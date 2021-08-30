rm(list=ls())
library(data.table)
library(ggplot2)

ST_GPR_RUN_ID <- 190430
ST_GPR_BASE_DIR <- sprintf("FILEPATH", ST_GPR_RUN_ID)
CW_VERSION <- "FILEPATH"
working_dir <- "FILEPATH"

df <- fread(paste0(ST_GPR_BASE_DIR, "FILEPATH"))
df <- df[location_id == 102 & race != 'all races']
df$race = stringr::str_trim(df$race)
draws = paste0("draw_", 0:999)
df[, deaths := rowMeans(.SD), .SDcols = draws]
df[, (draws) := NULL]
df <- df[, lapply(.SD, sum), by = c("year_id", "race"), .SDcols = c("deaths", "population")]

cw <- fread(paste0(working_dir, CW_VERSION, "/crosswalk_out.csv"))
cw <- cw[, lapply(.SD, sum), by = c("year_id", "re", "sub_source"), .SDcols = c("deaths_adjusted", "population")]
cw$race <- cw$re

df <- merge(
  df, cw, all.x = TRUE, all.y = FALSE,
  by = c('year_id', 'race'),
  suffixes=c('_st_gpr', '_cw')
)

g1 <- ggplot(df, aes(deaths_adjusted, deaths, color = race)) + 
  geom_point() +
  coord_fixed() +
  scale_y_log10(limits = c(1, NA)) +
  scale_x_log10(limits = c(1, NA)) +
  geom_abline(slope = 1, intercept = 0) +
  xlab("deaths_cw") +
  ylab("deaths_st_gpr") +
  NULL

g2 <- ggplot(df, aes(deaths_adjusted, deaths, color = race)) + 
  geom_point() +
  coord_fixed() +
  geom_abline(slope = 1, intercept = 0) +
  xlab("deaths_cw") +
  ylab("deaths_st_gpr") +
  NULL

ggsave(
  "FILEPATH", g1, device = "pdf", path = "FILEPATH",
  width = 10, height = 10, units = c("in")
)

ggsave(
  "FILEPATH", g2, device = "pdf", path = "FILEPATH",
  width = 10, height = 10, units = c("in")
)
