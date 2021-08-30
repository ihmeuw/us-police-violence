rm(list=ls())
library(data.table)
library(ggplot2)
library(epiR)

working_dir <- "FILEPATH"

df <- fread("FILEPATH")

for (suffix in c('_x', '_y')) {
  df[, paste0('deaths_orig', suffix) := get(paste0('deaths', suffix)) - get(paste0('offset', suffix))]
  df[, paste0('rate_orig', suffix) := get(paste0('deaths_orig', suffix)) / get(paste0('population', suffix))]
}

for (suffix in c('', '_orig')) {
  df[, paste0('ratio', suffix) := get(paste0('rate', suffix, '_x')) / get(paste0('rate', suffix, '_y'))]
}

stopifnot(!any(is.na(df$ratio)))

df[, both := !(is.na(df$ratio_orig) | (df$ratio_orig == Inf) | (df$ratio_orig == 0))]
df_plot <- df[(both),]
stopifnot(!any(is.na(df_plot$ratio_orig)))
stopifnot(!any(is.infinite(df_plot$ratio_orig)))
stopifnot(!any(df_plot$ratio_orig == 0))

g1 <- ggplot(df_plot, aes(ratio_orig, ratio)) +
  geom_point(shape = 1, size = 2.5) +
  scale_x_log10() +
  scale_y_log10() +
  geom_abline(slope = 1, intercept = 0, color = "lightblue", size = 1) +
  coord_fixed(ratio=1) +
  xlab("Pre-offset ratio of mortality rates between data sources") +
  ylab("Post-offset ratio of mortality rates between data sources") +
  ggtitle("Ratios of mortality rates for all non-zero data points, pre- and post-offset") +
  theme(aspect.ratio=1) +
  theme_bw() +
  theme(plot.title = element_text(hjust = 0.5))

# Percent change
df_plot[, pct_change := (ratio - ratio_orig) / ratio_orig]
mean(df_plot$pct_change)
sd(df_plot$pct_change)

# Histograms
g2 <- ggplot(df, aes(ratio)) +
  geom_histogram(aes(fill = "Post-offset"), alpha = 0.5) +
  geom_histogram(data = df_plot, mapping = aes(ratio_orig, fill = "Pre-offset"), alpha = 0.5) +
  scale_x_log10(labels = scales::comma) +
  scale_color_manual(values = c("Post-offset" = "red", "Pre-offset" = "blue")) +
  xlab("Ratio of mortality rates between data sources") +
  ylab("Number of data points") +
  ggtitle("Distributions of ratios of mortality rates, pre- and post-offset") +
  labs(fill = "") +
  theme_bw() + 
  theme(plot.title = element_text(hjust = 0.5))

# Save
ggsave(
  "FILEPATH",
  plot = g1,
  device = "pdf",
  path = working_dir,
  width = 11,
  height = 8,
  units=c("in")
)
ggsave(
  "FILEPATH",
  plot = g2,
  device = "pdf",
  path = working_dir,
  width = 11,
  height = 8,
  units=c("in")
)

linccc <- epi.ccc(log(df_plot$ratio), log(df_plot$ratio_orig))
linccc$rho.c