# Run crosswalks for US police violence data
rm(list=ls())
library(data.table)
# Source code for crosswalk package: https://github.com/ihmeuw-msca/CrossWalk
library(crosswalk, lib.loc = "FILEPATH")
library(argparse)

one_hot_encode <- function(df, col) {
  stopifnot(is.data.table(df))
  stopifnot(class(df[, get(col)]) == 'factor')
  
  df_copy <- copy(df)
  df_copy[, uniq_row := seq(1, .N)]
  one_hot <- as.data.table(dcast(
    df_copy, formula(paste0("uniq_row ~ ", col)),
    length
  ))
  stopifnot(ncol(one_hot) == length(unique(df[, get(col)])) + 1)
  stopifnot(unique(
    one_hot[, rowSums(.SD),
              .SDcols = names(one_hot)[names(one_hot) != "uniq_row"]]
  ) == 1)
  
  reference_level <- names(one_hot)[names(one_hot) != "uniq_row"][1]
  one_hot[, c("uniq_row", reference_level) := NULL]
  names(one_hot) <- sapply(names(one_hot), function(x) {paste0(col, x)})
  df <- cbind(df, one_hot)
  return(list("df" = df, "cols" = names(one_hot)))
}

log_transform <- function(df, mean_col, se_col) {
  tf <- as.data.frame(
    delta_transform(
      df[, get(mean_col)], df[, get(se_col)], "linear_to_log")
  )
  names(tf) <- c(paste0("log_", mean_col), paste0("log_", se_col))
  return(cbind(df, tf))
}

convert_to_factor <- function(df) {
  factor_cols <- c(
    "age_group_id", "sex_id", "location_id", "state_id", "re", "population_group_id")
  factor_cols <- factor_cols[factor_cols %in% names(df)]
  df[, (factor_cols) := lapply(.SD, factor), .SDcols = factor_cols]
  return(df)
}

get_data <- function(working_dir, matches_file, match_cols, model_col) {
  df <- fread(paste0(working_dir, matches_file))
  stopifnot(!any(is.na(df)))
  df <- convert_to_factor(df)
  
  model_col_x <- paste0(model_col, "_x")
  model_col_y <- paste0(model_col, "_y")
  df <- log_transform(df, model_col_x, "se_x")
  df <- log_transform(df, model_col_y, "se_y")
  
  diff <- calculate_diff(
    df, alt_mean = paste0("log_", model_col_y), alt_sd = "log_se_y",
    ref_mean = paste0("log_", model_col_x), ref_sd = "log_se_x"
  )
  names(diff) <- c("log_diff_mean", "log_diff_se")
  df <- cbind(df, diff)
  
  df[, group_id := .GRP, by = match_cols]
  return(df)
}

check_collinearity <- function(df, covs) {
  # Pairwise correlations
  corr_mat <- abs(cor(df[, ..covs]))
  diag(corr_mat) <- 0
  print("Checking collinearity... correlation matrix")
  print(round(corr_mat, digits = 2))
  stopifnot(all(corr_mat < 0.80))
}

determine_prior <- function(cov, dorms, impose_priors = FALSE) {
  if (cov %in% c("LDI_pc", "ldi_pc_re", "ldi_pc_black", "ldi_pc_lowest", "pct_firearm") & impose_priors) {
    prior_beta_uniform <- lapply(dorms, function(x) {array(c(0, 0))})
    names(prior_beta_uniform) <- dorms
  } else {
    prior_beta_uniform <- NULL
  }
  return(prior_beta_uniform)
}

run_crosswalk <- function(df, dorm_col, covs, gold_dorm, order_prior, impose_priors) {
  alt_dorms <- paste0(dorm_col, "_y")
  ref_dorms <- paste0(dorm_col, "_x")
  df.cw <- CWData(
    df = df,
    obs = "log_diff_mean",
    obs_se = "log_diff_se",
    alt_dorms = alt_dorms,
    ref_dorms = ref_dorms,
    covs = covs,
    study_id = "group_id"
  )

  uniq_dorms <- unique(c(as.matrix(df[, get(alt_dorms), get(ref_dorms)])))
  uniq_dorms <- uniq_dorms[!grepl("NVSS", uniq_dorms)]
  uniq_dorms <- uniq_dorms[!grepl(gold_dorm, uniq_dorms)]
  cov_models <- lapply(
    covs, function(x) {
      CovModel(cov_name = x, prior_beta_uniform = determine_prior(
        x, uniq_dorms, impose_priors = impose_priors))})
  cov_models[[length(cov_models) + 1]] <- CovModel(cov_name = "intercept")
  fit.cw <- CWModel(
    cwdata = df.cw,
    obs_type = "diff_log",
    cov_models = cov_models,
    gold_dorm = gold_dorm,
    max_iter = 10000L,
    order_prior = order_prior
  )
  return(fit.cw)
}

apply_crosswalk <- function(df_orig, fit.cw, dorm_col, adjust_col, study_id = NULL) {
  orig_zero <- df_orig[get(adjust_col) == 0,]
  orig_nonzero <- df_orig[get(adjust_col) != 0,]
  preds <- adjust_orig_vals(
    fit_object = fit.cw,
    df = orig_nonzero,
    orig_dorms = dorm_col,
    orig_vals_mean = adjust_col,
    orig_vals_se = "se",
    study_id = study_id
  )
  orig_nonzero[, c(paste0(adjust_col, "_adjusted"), "se_adjusted",
              "log_adjustment", "log_adjustment_se")] <- preds[, 1:4]
  orig_zero[, paste0(adjust_col, "_adjusted") := 0]
  orig_zero[, paste0("se_adjusted") := 0]
  return(rbindlist(list(orig_nonzero, orig_zero), fill = TRUE))
}

main <- function(working_dir, matches_file, data_file, adjusted_file,
                 match_cols, encode_cols, cov_cols, dorm_col, gold_dorm,
                 order_prior, adjust_col, model_col, impose_priors) {
  # working_dir: working directory
  # matches_file: file name for matches
  # data_file: file name for data to adjust
  # adjusted_file: file name for adjusted data
  # match_cols: vector of columns that that were matched on
  # encode_cols: vector of factor variables to one-hot encode
  # cov_cols: vector of columns to use as covariates
  # dorm_col: name of column that contains the dorm
  # gold_dorm: value of dorm_col to use as the gold standard
  # order_prior: list of two-element vectors that represent
  #   inequalities to enforce on the model coefficients
  # adjust_col: name of column that should be adjusted
  #   using crosswalk betas
  # model_col: name of column that should be modelled
  # impose_priors: impose special priors for certain covs

  df_matched <- get_data(
    working_dir, matches_file, match_cols, model_col
  )
  df_orig <- fread(paste0(working_dir, data_file))
  df_orig <- convert_to_factor(df_orig)

  added_cols <- c()
  for (encode_col in encode_cols) {
    matched_encode <- one_hot_encode(df_matched, encode_col)
    orig_encode <- one_hot_encode(df_orig, encode_col)
    df_matched <- matched_encode$df
    df_orig <- orig_encode$df
    if (encode_col %in% cov_cols) {
      cov_cols <- cov_cols[cov_cols != encode_col]
      cov_cols <- c(cov_cols, matched_encode$cols)
    }
    added_cols <- c(added_cols, orig_encode$cols)
  }
  continuous_covs <- cov_cols[!(cov_cols %in% added_cols)]
  check_collinearity(df_matched, continuous_covs)

  fit.cw <- run_crosswalk(
    df_matched, dorm_col, as.list(cov_cols), gold_dorm, order_prior,
    impose_priors = impose_priors
  )
  df_adjusted <- apply_crosswalk(df_orig, fit.cw, dorm_col, adjust_col)

  for (added_col in added_cols) {
    df_adjusted[[added_col]] <- NULL
  }
  write.csv(
    df_adjusted, file = paste0(working_dir, adjusted_file),
    row.names = FALSE
  )

  betas <- as.data.table(fit.cw$create_result_df()[, 1:4])
  degf = fit.cw$cwdata$num_obs - nrow(betas[dorms != betas$dorms[1]])
  betas[, p := 2 * pt(-1 * abs(beta / beta_sd), df = degf)]
  betas[, signf := p <= 0.05]
  write.csv(betas, "FILEPATH")
}


parser <- ArgumentParser(description = "Arguments for crosswalking")
parser$add_argument('working_dir', type = "character")
parser$add_argument('matches_file', type = "character")
parser$add_argument('data_file', type = "character")
parser$add_argument('adjusted_file', type = "character")
parser$add_argument('--match_cols', type = "character", nargs="+")
parser$add_argument('--encode_cols', type = "character", nargs="*", default=c())
parser$add_argument('--cov_cols', type = "character", nargs="*", default=c())
parser$add_argument('--dorm_col', type = "character", nargs = 1, required = TRUE)
parser$add_argument('--gold_dorm', type = "character", nargs = 1, required = TRUE)
parser$add_argument(
  '--order_prior', type = "character", nargs = "*",
  help = "ordered pairs of dorms separated by commas"
)
parser$add_argument('--adjust_col', type = "character", nargs = 1, required = TRUE)
parser$add_argument('--model_col', type = "character", nargs = 1, required = TRUE)
parser$add_argument('--impose_priors', action='store_true')

args <- parser$parse_args()

if (!grepl("/$", args$working_dir)) {
  args$working_dir <- paste0(args$working_dir, "/")
}

if (length(args$order_prior) < 1) {
  order_prior <- NULL
} else {
  order_prior <- strsplit(args$order_prior, ",")
}

main(
  args$working_dir,
  args$matches_file,
  args$data_file,
  args$adjusted_file,
  args$match_cols,
  args$encode_cols,
  args$cov_cols,
  args$dorm_col,
  args$gold_dorm,
  order_prior,
  args$adjust_col,
  args$model_col,
  args$impose_priors
)
