rm(list=ls())
library(data.table)
library(ggplot2)

working_dir <- paste0("FILEPATH")

df1 <- fread(paste0(working_dir, "FILEPATH"))
df2 <- fread(paste0(working_dir, "FILEPATH"))

df1[, status := "Raw data"]
df2[, status := "Including imputed race/ethnicity with 80% imputation probability cutoff"]
df <- rbindlist(list(df1, df2))
df$status <- factor(df$status, levels = c("Raw data", "Including imputed race/ethnicity with 80% imputation probability cutoff"))

df <- df[Year >= 2005 & Year <= 2019]
df[, Race := ifelse(Race == 'Race unspecified', "Race unspecified", "Race specified")]
df <- df[, lapply(.SD, sum), by = c("Year", "Race", "status"), .SDcols = c("Deaths")]
df[, prop_deaths := Deaths / sum(Deaths), by = c("Year", "status")]

g <- ggplot(df, aes(fill = Race, Year, prop_deaths, label = sprintf("%0.2f", round(prop_deaths, digits = 2)))) +
  geom_bar(position="stack", stat="identity") +
  geom_text(size = 3, position = position_stack(vjust = 0.5)) +
  facet_wrap(~ status) +
  ylab("Proportion of deaths") +
  ggtitle("Proportion of deaths by race/ethnicity in Fatal Encounters") +
  theme(plot.title = element_text(hjust = 0.5)) +
  NULL

ggsave(
  "FILEPATH",
  g, device = "pdf", path = working_dir,
  width = 14, height = 6, units = "in"
)
