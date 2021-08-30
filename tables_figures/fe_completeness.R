rm(list=ls())
library(data.table)
library(ggplot2)

working_dir <- paste0("FILEPATH")
df <- fread(paste0(working_dir, "FILEPATH"))

df <- df[compare_year %in% c(2000, 2005)]

map = c(
  "2000" = "Normalized to 2000",
  "2005" = "Normalized to 2005",
  "2008" = "Normalized to 2008"
)
df$compare_year <- map[as.character(df$compare_year)]
df <- df[sub_source != "Fatal_Encounters"]
df[sub_source == 'Fatal_Encounters_causes_dropped', sub_source := "Fatal Encounters"]

g <- ggplot(df, aes(x = year_id, y = deaths, color = sub_source, fill = sub_source)) +
  geom_point() +
  geom_line() +
  facet_wrap(~ compare_year) +
  theme(aspect.ratio=1) +
  theme(text = element_text(size=10)) +
  xlab("Year") +
  ylab("Deaths") +
  ggtitle("Normalized deaths in Fatal Encounters and NVSS") +
  theme(plot.title = element_text(hjust = 0.5)) +
  NULL

ggsave(
  "FILEPATH",
  g, device = "pdf", path = working_dir,
  width = 11.5, height = 8, units = "in"
)
