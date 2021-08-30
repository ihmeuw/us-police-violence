rm(list=ls())
library(data.table)
library(ggplot2)

working_dir <- paste0("FILEPATH")

# AGE
CW_VERSION <- "FILEPATH"
working_dir <- "FILEPATH"
data <- fread(paste0(working_dir, CW_VERSION, "FILEPATH"))

data <- data[age_group_id %in% 9:15]

data <- data[sub_source_x == 'NVSS' | sub_source_y == 'NVSS']
data[sub_source_y == 'NVSS', ln_rate_ratio := log(deaths_y / deaths_x)]
data[sub_source_x == 'NVSS', ln_rate_ratio := log(deaths_x / deaths_y)]
data[, sub_source_combo := paste0(sub_source_x, sub_source_y)]
factor_cols <- c("age_group_id", "sex_id", "sub_source_combo")
factor_cols <- factor_cols[factor_cols %in% names(data)]
data[, (factor_cols) := lapply(.SD, factor), .SDcols = factor_cols]
stopifnot(!any(is.na(data$ln_rate_ratio)))

age.aov <- aov(ln_rate_ratio ~ age_group_id + sub_source_combo, data)
summary(age.aov)

mod <- lm(ln_rate_ratio ~ age_group_id + sub_source_combo, data)
summary(mod)

# SEX
CW_VERSION <- "FILEPATH"
working_dir <- "FILEPATH"
data <- fread(paste0(working_dir, CW_VERSION, "FILEPATH"))

data <- data[sub_source_x == 'NVSS' | sub_source_y == 'NVSS']
data[sub_source_y == 'NVSS', ln_rate_ratio := log(deaths_y / deaths_x)]
data[sub_source_x == 'NVSS', ln_rate_ratio := log(deaths_x / deaths_y)]

data[, sub_source_combo := paste0(sub_source_x, sub_source_y)]
factor_cols <- c("age_group_id", "sex_id", "sub_source_combo")
factor_cols <- factor_cols[factor_cols %in% names(data)]
data[, (factor_cols) := lapply(.SD, factor), .SDcols = factor_cols]
stopifnot(!any(is.na(data$ln_rate_ratio)))

sex.aov <- aov(ln_rate_ratio ~ sex_id + sub_source_combo, data)
summary(sex.aov)

mod <- lm(ln_rate_ratio ~ sex_id + sub_source_combo, data)
summary(mod)