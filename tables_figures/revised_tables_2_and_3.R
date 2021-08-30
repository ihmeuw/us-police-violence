rm(list=ls())
library(ggplot2)
library(data.table)
library(extrafont)
library(stringr)
library(RColorBrewer)
library(ggpubr)

# LOAD DATA
data_dir <- "FILEPATH"
mort_dat_decade <- data.table(read.csv("FILEPATH"))
national_mort_dat_decade <- data.table(read.csv("FILEPATH"))
five_race_dir <- "FILEPATH"
fr <- fread("FILEPATH")

# SET FONTS
font_import("FILEPATH", prompt=FALSE)
loadfonts()
f2 <- "Times"

# SUBPLOT 1

df <- rbind(mort_dat_decade, national_mort_dat_decade)
df$race <- gsub("all races", "All Races and Ethnicities", df$race)
df$race <- gsub(" Non-Hispanic, Other races", "Non-Hispanic, Other race (including Indigenous)", df$race)
df$newx <- interaction(df$race, df$decade, lex.order = TRUE, sep = ", ")
df$newx <- str_wrap(df$newx, width = 10)

level_list <- unique(df$newx)

df$newx_order <- factor(df$newx, levels= c(level_list[1], level_list[6], level_list[11], level_list[16], level_list[5], level_list[10], level_list[15],
                                           level_list[20], level_list[2], level_list[7], level_list[12], level_list[17],
                                           level_list[4], level_list[9], level_list[14], level_list[19],
                                           level_list[3], level_list[8], level_list[13], level_list[18]), ordered = TRUE)

bins <- seq(0, 1.2, 0.2)
bins <- c(bins, round(max(df$best) + 1))
y <- '%.2f'

bin_labels <- c()
for (i in 1:length(bins)) {
  if (i == 1 | i == length(bins)) {
    # Do nothing
  } else if (i == 2) {
    bin_labels <- c(bin_labels, paste0('<', sprintf(y, bins[i])))
  } else {
    bin_labels <- c(bin_labels, paste0(sprintf(y, bins[i - 1]), '-', '<', sprintf(y, bins[i])))
    if (i == length(bins) - 1) {
      bin_labels <- c(bin_labels, paste0(sprintf(y, bins[i]), '+'))
    }
  }
}

df$Bin <- cut(df$best, bins, bin_labels)
level_list <- unique(df$Bin)
stopifnot(!any(is.na(df$Bin)))

df_named <- df[, named := paste0(sprintf('%0.2f', best)," (",sprintf('%0.2f', low)," - ",sprintf('%0.2f', high),")")]
colors <- brewer.pal(length(unique(df_named$Bin)), "YlOrRd")

# Reorder levels of the state variable
sub_df <- df_named[newx_order == 'All\nRaces and\nEthnicities,\n2010s']
sub_df <- setorder(sub_df, best)
state_levels <- as.character(sub_df$state)
# Move USA to the front
state_levels <- state_levels[state_levels != "United States"]
state_levels <- c("USA", state_levels)  # Using USA to copy Lancet
df_named[state == 'United States', state := "USA"]
df_named$state <- factor(df_named$state, levels = state_levels, ordered = TRUE)

gg <- ggplot(df_named, aes(x = newx_order,  y = state,
                           label = named, fill = Bin))  +
  geom_tile(color = "white") + geom_text(size =1.5) +
  coord_fixed(ratio = .2)+
  scale_fill_manual(drop=FALSE, values=colors, name="Age-Standardised Mortality Rate per 100,000 ") +
  scale_x_discrete(position = "top", expand = c(0,0)) +
  scale_y_discrete(position = "left", expand = c(0,0))+
  theme_bw() + xlab("") + ylab("") +
  ggtitle("Table 2A: Police Violence Age-Standardised Mortality Rate per 100,000 in the USA\nby Four Race/Ethnicity Groups, State, and Decade, 1980-2019") +
  theme(text=element_text(family = f2),
        axis.text.x = element_text(color="black", size=6, angle = 0),
        axis.ticks.x = element_blank(),
        axis.text.y = element_text(color="black", size=6),
        plot.title = element_text(color = "black", face ='bold', size=10, hjust = 0.5, vjust = -4),
        legend.position="none",
        strip.text = element_text(size = 6),
        panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        axis.line=element_blank(),
        panel.background = element_blank()) +
  NULL

# SUBPLOT 2
fr <- fr[!(year_bin %in% c("1980-1984", "1985-1989"))]
fr$Bin <- cut(fr$rate_per_100k, bins, bin_labels)
fr[race == "Non-Hispanic, Other races", race := "Non-Hispanic, Other race (not including Indigenous)"]
fr$race <- str_wrap(fr$race, width = 10)
levels <- sort(unique(fr$race))
fr$race <- factor(fr$race, levels = c(levels[2], levels[1], levels[3], levels[4], levels[5]))
fr$year_bin <- factor(fr$year_bin, levels = sort(unique(fr$year_bin), decreasing = TRUE))

gg2 <- ggplot(fr, aes(x = race,  y = year_bin, label = rate, fill = Bin)) +
  geom_tile(color = "white") + geom_text(size =1.5) +
  coord_fixed(ratio = .2) +
  scale_fill_manual(drop=FALSE, values=colors, name="Age-Standardised Mortality Rate per 100,000 ") +
  scale_x_discrete(position = "top", expand = c(0,0)) +
  scale_y_discrete(position = "left", expand = c(0,0)) +
  theme_bw() + xlab("") + ylab("") +
  ggtitle("Table 2B: Police Violence Age-Standardised Mortality Rate per 100,000 in the USA\nby Five Race/Ethnicity Groups and Five-Year Period, 1990-2019") +
  theme(text=element_text(family = f2),
        axis.text.x = element_text(color="black", size=6, angle = 0),
        axis.ticks.x = element_blank(),
        axis.text.y = element_text(color="black", size=6),
        plot.title = element_text(color = "black", face ='bold', size=10, hjust = 0.5, vjust = -4),
        legend.position = "left",
        legend.direction = "vertical",
        strip.text = element_text(size = 6),
        legend.background = element_blank(),
        legend.key = element_blank(),
        legend.text=element_text(size = 10),
        legend.title=element_text(size = 8),
        legend.key.size = unit(0.5, "cm"),
        panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        axis.line=element_blank(),
        panel.background = element_blank()) +
  NULL

legend <- ggpubr::get_legend(gg2)
legend <- as_ggplot(legend)
gg2 <- gg2 + theme(legend.position = "none")

figure <- ggarrange(
  gg,
  ggarrange(
    gg2,
    legend,
    ncol = 2,
    nrow = 1,
    widths = c(2, 1)
  ),
  ncol = 1,
  nrow = 2,
  heights = c(2, 0.6)
)

figure
file.remove("FILEPATH")
ggsave(filename = "FILEPATH", figure,
       width = 300, height = 240, units = "mm", limitsize = FALSE)