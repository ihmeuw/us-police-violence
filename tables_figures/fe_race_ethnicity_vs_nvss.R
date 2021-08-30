rm(list=ls())
library(data.table)
library(ggplot2)

working_dir <- "FILEPATH"

df1 <- fread(paste0(working_dir, "FILEPATH"))
df1[, pct_cutoff := "Imputed race/ethnicity included, 80% cutoff"]
df2 <- fread(paste0(working_dir, "FILEPATH"))
df2[, pct_cutoff := "Raw data"]

data <- rbindlist(list(df1, df2), fill=TRUE)
data$pct_cutoff <- factor(data$pct_cutoff, levels = c("Raw data", "Imputed race/ethnicity included, 80% cutoff"))
data <- data[sub_source %in% c("Fatal_Encounters", "NVSS")]
data <- data[year_id %in% 2005:2017]
data <- data[re != "Unknown race or ethnicity"]
data$year_id <- as.integer(data$year_id)
# get pct for each re by sub_source, cutoff and year
data[, pct_deaths := deaths / sum(deaths), by = c("year_id", "sub_source", "pct_cutoff")]

g <- ggplot(data, aes(x = year_id, y = pct_deaths, color = sub_source)) +
  geom_point() +
  geom_line() +
  facet_grid(vars(pct_cutoff), vars(re), scales = "free") +
  theme(aspect.ratio=1) +
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
  scale_x_continuous(breaks=seq(2000, 2020, 2)) +
  ylab("Proportion of deaths") +
  xlab("Year") +
  ggtitle("Proportion of deaths by race/ethnicity in Fatal Encounters vs NVSS") +
  theme(plot.title = element_text(hjust = 0.5)) +
  NULL

ggsave(
  "FILEPATH",
  g, device = "pdf", path = working_dir,
  width = 14, height = 6, units = "in"
)
