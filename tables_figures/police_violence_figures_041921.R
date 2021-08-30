### SET UP
options(OutDec= ".")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
require(tidyr)
library(openxlsx)
require(grid)
require(ggrepel)
library(maptools)
require(sp)
require(RColorBrewer)
options(scipen=999)
require(dplyr)
library(ggplot2)
library(sf)
library(data.table)
library(rgdal)
library(parallel)
library(stringr)
library(gridExtra)
library(viridis)
library(cowplot)
library(ggplotify)
library(ggpubr)

data_dir <- "FILEPATH"
outdir <- "FILEPATH"

source_dat_long <- data.table(read.csv(paste0(data_dir, "FILEPATH")))

mort_dat <- data.table(read.csv(paste0(data_dir, "FILEPATH")))
mort_dat_decade <- data.table(read.csv(paste0(data_dir, "FILEPATH")))

source_dat_wide <- data.table(read.csv(paste0(data_dir, "FILEPATH")))
source_dat_wide$percent_missed[source_dat_wide$percent_missed %like% 100] <- 0
source_dat_wide$percent_missed[source_dat_wide$percent_missed < 0] <- 0

source_dat <- data.table(read.csv(paste0(data_dir, "FILEPATH")))
source_dat <- source_dat[!(re %like% 'all races'),]
source_dat <- source_dat[!(location %like% 'United States'),]

library(extrafont)
font_import("FILEPATH", prompt=FALSE)
loadfonts()
f2 <- "Times"

#### FIG 2  ####

k = "FILEPATH"
source(paste0(k,"FILEPATH"))

if (Sys.info()["sysname"] == "Linux") j <- "FILEPATH" else j <- "FILEPATH"

map_theme_main <- theme(text=element_text(family = f2), panel.background = element_rect(fill="white"),
                        panel.border = element_rect(color="white", fill=NA, size=rel(1)),
                        axis.text.x = element_blank(),
                        axis.title.x = element_blank(),
                        axis.ticks.x = element_blank(),
                        axis.text.y = element_blank(),
                        axis.title.y = element_blank(),
                        plot.title = element_text(size = 20, hjust = 0.5),
                        plot.subtitle = element_text(size = 14, hjust = 0.5),
                        legend.position = "bottom",
                        legend.direction = "vertical",
                        legend.text = element_text(size = 12),
                        legend.title = element_text(size = 14),
                        axis.ticks.y = element_blank(),
                        panel.grid = element_blank(),
                        legend.key.size = unit(.8, 'cm'),
                        panel.grid.major = element_line(color = 'white'))
map_theme_insets <- theme(panel.background = element_rect(fill="white"),
                          panel.border = element_rect(color="black", fill=NA, size=rel(1)),
                          axis.text.x = element_blank(),
                          axis.title.x = element_blank(),
                          axis.ticks.x = element_blank(),
                          axis.text.y = element_blank(),
                          axis.title.y = element_blank(),
                          legend.position = "none",
                          legend.justification = c(0,0),
                          plot.margin=grid::unit(c(0,0,0,0), "mm"),
                          axis.ticks.y = element_blank(),
                          panel.grid = element_blank(),
                          legend.key.size = unit(.5, 'cm'),
                          panel.grid.major = element_line(color = 'white'))


centers = data.frame()

for (i in 1:length(shp_plt@polygons)) {
  centers[i, 1] = shp_plt@polygons[[i]]@labpt[1]
  centers[i, 2] = shp_plt@polygons[[i]]@labpt[2]
  centers[i, 3] = shp_plt_DF[which(as.numeric(shp_plt_DF$id)==as.numeric(shp_plt@polygons[[i]]@ID))[1],]$state_name
}
colnames(centers) = c("long", "lat", "state_name")
centers[which(centers$state_name == "FL"),]$long = (centers[which(centers$state_name == "FL"),]$long) + 1
centers[which(centers$state_name == "MI"),]$long = (centers[which(centers$state_name == "MI"),]$long)
centers[which(centers$state_name == "HI"),]$lat = (centers[which(centers$state_name == "HI"),]$lat) + 2
centers[which(centers$state_name == "AK"),]$long = (centers[which(centers$state_name == "AK"),]$long) + 18


small = c("CT", "RI", "DC", "DE", "NJ", "MD")
centers_1 = centers %>% filter(!state_name %in% small)
centers_2 = centers %>% filter(state_name %in% small)



fname <- "FILEPATH"


# read in shapefile
us_shp <- readShapePoly(paste0(j,'FILEPATH'))

#get US locs metadata
us_locs = get_location_metadata(location_set_id = 35, gbd_round_id = 6)[parent_id == 102][, c("location_id", "location_name", "local_id")]
us_locs$state_name = sub('.*-', '', us_locs$local_id)
loc_match <- us_locs[, c("location_id", "location_name", "state_name")]

source_dat_wide$race_ethnicity[source_dat_wide$race_ethnicity == "Non-Hispanic, Other race"] <- "Non-Hispanic, Other races"

list <- unique(source_dat_wide$race_ethnicity)

centers = data.frame()

for (i in 1:length(shp_plt@polygons)) {
  centers[i, 1] = shp_plt@polygons[[i]]@labpt[1]
  centers[i, 2] = shp_plt@polygons[[i]]@labpt[2]
  centers[i, 3] = shp_plt_DF[which(as.numeric(shp_plt_DF$id)==as.numeric(shp_plt@polygons[[i]]@ID))[1],]$state_name
}
colnames(centers) = c("long", "lat", "state_name")
centers[which(centers$state_name == "FL"),]$long = (centers[which(centers$state_name == "FL"),]$long) + 1
centers[which(centers$state_name == "MI"),]$long = (centers[which(centers$state_name == "MI"),]$long)
centers[which(centers$state_name == "HI"),]$lat = (centers[which(centers$state_name == "HI"),]$lat) + 2
centers[which(centers$state_name == "AK"),]$long = (centers[which(centers$state_name == "AK"),]$long) + 18


small = c("CT", "RI", "DC", "DE", "NJ", "MD")
centers_1 = centers %>% filter(!state_name %in% small)
centers_2 = centers %>% filter(state_name %in% small)

for (race_eth in list) {

  df <- source_dat_wide[race_ethnicity %like% race_eth,]
  df_plot <- merge(df, loc_match, by.x = 'state', by.y = "location_name", all.y =FALSE)

  mapcolors <-  c("#0d4e93", "#0095c0", "#add9eb",
                  "#feeb98",  "#fdcd7b",
                  "#ec6445", "#e22527", "#b31f39")

  #merge onto shapefile
  shp_plt = us_shp
  shp_plt = subset(shp_plt, (shp_plt@data$loc_id != 102 & shp_plt@data$loc_id %in% us_locs$location_id))
  shp_plt@data = data.frame(shp_plt@data, df_plot[match(shp_plt@data$loc_id, df_plot$location_id.y),])

  shp_plt@data$id <- rownames(shp_plt@data)
  shp_plt_points <- fortify(shp_plt, region = "id")
  # create data frame
  shp_plt_DF <- merge(shp_plt_points, shp_plt@data, by = "id")
  setorder(shp_plt_DF, 'group')



  main = ggplot() +
    geom_polygon(data = shp_plt_DF, aes(x=long, y=lat, group = group,
                                        fill = percent_missed)) +
    geom_path(data = shp_plt_DF, aes(x=long, y=lat, group = group), size = 0.2) +
    geom_text(data = centers_1, aes(x = long, y = lat, label = state_name, family = f2),
              size = 4,
              fontface = "bold",
              color = "black") +
    geom_text_repel(data = centers_2, aes(x = long, y = lat, label = state_name, family = f2),
                    size = 4,
                    segment.size = 0.4,
                    nudge_y = -1.3,
                    nudge_x = 2.6,
                    fontface = "bold",
                    color = "black") +
    scale_fill_gradientn(colors = mapcolors, name = "", limits = c(0, 100)) +
    labs(title = "", subtitle = (race_eth)) +
    coord_cartesian(xlim = c(-127, -60), ylim = c(22, 50)) +
    map_theme_main +
    theme(legend.position = 'bottom',
          plot.subtitle = element_text(hjust=0.3, size = 15, face='bold'),
          legend.title = element_blank(),
          legend.direction = 'horizontal',
          legend.key.size = unit(0.95, "cm"),
          legend.text = element_text(size = 11.5, face="bold"),
          plot.margin = margin(0, 0, 0, 0, "cm"))


  hi <- ggplot() +
    geom_polygon(data = shp_plt_DF, aes(x=long, y=lat, group = group,
                                        fill = percent_missed)) +
    geom_path(data = shp_plt_DF, aes(x=long, y=lat, group = group), size = 0.2) +
    geom_text(data = centers, aes(x = long, y = lat, label = state_name),
              size = 4,
              fontface = "bold",
              color = "black") +
    scale_fill_gradientn(colors = mapcolors, name = "", limits = c(0, 100)) +
    coord_cartesian(xlim = c(-161.5, -154.4), ylim = c(18.5, 22.4)) +
    map_theme_insets + theme(legend.position = 'none')


  ak <- ggplot() +
    geom_polygon(data = shp_plt_DF, aes(x=long, y=lat, group = group,
                                        fill = percent_missed)) +
    geom_path(data = shp_plt_DF, aes(x=long, y=lat, group = group), size = 0.2) +
    geom_text(data = centers, aes(x = long, y = lat, label = state_name),
              size = 4,
              fontface = "bold",
              color = "black") +
    scale_fill_gradientn(colors = mapcolors, name = "", limits = c(0, 100)) +
    coord_cartesian(xlim = c(-184, -129), ylim = c(54, 71.7)) +
    map_theme_insets + theme(legend.position = 'none')

  ak_grb <- as.grob(ak)
  hi_grb <- as.grob(hi)

  x <- paste0('map_', race_eth)

  if (race_eth %like% list[1]) {
    map_har <- main +
      annotation_custom(grob = ak_grb,
                        xmin = -130,
                        xmax = -118,
                        ymin = 22,
                        ymax = 30) +
      annotation_custom(grob = hi_grb,
                        xmin = -117,
                        xmax = -104,
                        ymin = 22,
                        ymax = 27)
  }

  if (race_eth %like% list[2]) {
    map_nhb <- main +
      annotation_custom(grob = ak_grb,
                        xmin = -130,
                        xmax = -118,
                        ymin = 22,
                        ymax = 30) +
      annotation_custom(grob = hi_grb,
                        xmin = -117,
                        xmax = -104,
                        ymin = 22,
                        ymax = 27)
  }

  if (race_eth %like% list[3]) {
    map_nho <- main +
      annotation_custom(grob = ak_grb,
                        xmin = -130,
                        xmax = -118,
                        ymin = 22,
                        ymax = 30) +
      annotation_custom(grob = hi_grb,
                        xmin = -117,
                        xmax = -104,
                        ymin = 22,
                        ymax = 27)

  } else

    map_nhw <- main +
    annotation_custom(grob = ak_grb,
                      xmin = -130,
                      xmax = -118,
                      ymin = 22,
                      ymax = 30) +
    annotation_custom(grob = hi_grb,
                      xmin = -117,
                      xmax = -104,
                      ymin = 22,
                      ymax = 27)

}

legend <- get_legend(map_nhw)

map_nhw <- map_nhw + theme(legend.position="none")
map_nhb <- map_nhb + theme(legend.position="none")
map_nho <- map_nho + theme(legend.position="none")
map_har <- map_har + theme(legend.position="none")

fig1_maps <- plot_grid(map_nhw, map_nhb, map_nho, map_har, nrow=2, rel_heights = c(1, 1))

text <- "Figure 2. Percent of Police Violence Deaths Misclassified in NVSS by Race, Ethnicity, and State in the USA, 1980-2018"
tgrob <- text_grob(text, family = f2, size = 25, rot = 0, face = "bold")
as_ggplot(tgrob)

gg_legend <- plot_grid(NULL, legend, ncol=2, rel_heights = c(1, 1), rel_widths = c(1,1))

fig1_title <- plot_grid(tgrob, fig1_maps, nrow=2, rel_heights = c(1, 5), rel_widths = c(1,5))
fig1_fin <- plot_grid(fig1_title, gg_legend, nrow=2, rel_heights = c(1, .1), rel_widths = c(1,.5))


pdf(paste0(outdir,fname), width = 27, height =20)
plot(fig1_fin)
dev.off()


##### FIGURE 3 #######
source_dat_raw <- source_dat[!(model_type %like% 'crosswalk results'),]
source_dat_cw <- source_dat[!(model_type %like% 'raw_data'),]

dt_raw<- data.table(source_dat_raw)
dt_raw<- dt_raw[,list(deaths = sum(deaths)), by = 'year_id,sub_source']

dt_cw<- data.table(source_dat_cw)
dt_cw<- dt_cw[,list(deaths = sum(deaths)), by = 'year_id,sub_source']

dt_raw$sub_source <- gsub("Fatal_Encounters", "Fatal Encounters", dt_raw$sub_source)


dt_raw$sub_source <- gsub("The_Counted", "The Counted", dt_raw$sub_source)


dt_raw$sub_source <-  gsub("IHME Model", "Model Estimate", dt_raw$sub_source)

dt_cw$sub_source <- gsub("Fatal_Encounters", "Fatal Encounters", dt_cw$sub_source)


dt_cw$sub_source <- gsub("The_Counted", "The Counted", dt_cw$sub_source)


dt_cw$sub_source <- gsub("IHME Model", "Model Estimate", dt_cw$sub_source)


dt <- source_dat_long[(race_ethnicity %like% 'all races'),]
dt <- dt[(state %like% 'United States'),]
dt$sub_source <- gsub("STGPR_result", "Model Estimate", dt$sub_source)


gg_raw <- ggplot() +
  geom_point(dt_raw, mapping= aes(x = year_id, y = deaths, group = sub_source, color = sub_source), size = 0) +
  geom_point(dt_raw[!(dt_raw$sub_source=='Model Estimate'),], mapping= aes(x = year_id, y = deaths, group = sub_source, color = sub_source), size = 4) +
  geom_line(dt[dt$sub_source=='Model Estimate',], mapping = aes(x = year_id, y = deaths), color =  "#006A37", size = 2) +
  geom_ribbon(dt[dt$sub_source=='Model Estimate',], mapping =  aes(x = year_id, y = deaths, ymin=deaths_lower, ymax=deaths_upper),  fill =  "#006A37", linetype=2, alpha=0.1) +
  labs(x ='Year', y = 'Deaths',
       title = paste0("Before Network Meta-Regression")) +
  theme_bw() +
  scale_fill_manual(values = c("#ffdc00", "#006a37",  "#0d4e93", "#b31f38", "#8b2269")) +
  scale_color_manual(values = c("#ffdc00", "#006a37",  "#0d4e93", "#b31f38", "#8b2269")) +
  scale_x_continuous(expand = c(0.01, 0.01), breaks = c(1980,  1985, 1990, 1995, 2000, 2005, 2010, 2015)) +
  scale_y_continuous(expand = c(0, 0), limits = c(0, 1550)) +
  guides(fill=FALSE) +
  theme(text=element_text(family = f2), panel.grid.major = element_blank(), panel.grid.minor  = element_blank(),
        axis.line = element_line(colour = "black"),
        axis.text.x = element_text(size = 10),
        axis.text.y = element_text(size = 10),
        plot.title = element_text(hjust = 0.5, size = 14),
        legend.position = "none", legend.direction = "horizontal", legend.title = element_blank())

gg_legend <- get_legend(gg_raw)


gg_cw <- ggplot() +
  geom_point(dt_cw, mapping= aes(x = year_id, y = deaths, group = sub_source, color = sub_source), size = 0) +
  geom_point(dt_cw[!(dt_cw$sub_source=='Model Estimate'),], mapping= aes(x = year_id, y = deaths, group = sub_source, color = sub_source), size = 3) +
  geom_line(dt_cw[dt_cw$sub_source=='Model Estimate',], mapping = aes(x = year_id, y = deaths), color =  "#006A37", size = 2) +
  geom_ribbon(dt[dt$sub_source=='Model Estimate',], mapping =  aes(x = year_id, y = deaths, ymin=deaths_lower, ymax=deaths_upper),  fill =  "#006A37", linetype=2, alpha=0.1) +
  labs(x ='Year', y = 'Deaths',
       title = ("After Network Meta-Regression")) +
  theme_bw() +
  scale_fill_manual(values = c("#ffdc00", "#006a37",  "#0d4e93", "#b31f38", "#8b2269")) +
  scale_color_manual(values = c("#ffdc00", "#006a37",  "#0d4e93", "#b31f38", "#8b2269")) +
  scale_x_continuous(expand = c(0.01, 0.01), breaks = c(1980,  1985, 1990, 1995, 2000, 2005, 2010, 2015)) +
  scale_y_continuous(expand = c(0, 0), limits = c(0, 1550)) +
  guides(fill=FALSE) +
  theme(text=element_text(family = f2), panel.grid.major = element_blank(), panel.grid.minor  = element_blank(),
        axis.line = element_line(colour = "black"),
        axis.text.x = element_text(size = 10),
        axis.text.y = element_text(size = 10),
        plot.title = element_text(hjust = 0.5, size = 14),
        legend.position = "none", legend.title = element_blank())

gg  <- plot_grid(gg_raw, gg_cw, ncol=2, rel_heights = c(1, 1), rel_widths = c(1,1))
text <- "Figure 3. Input Data and Model Estimate with 95% Uncertainty Interval\nfor Police Violence Deaths in the USA, 1980-2019"
tgrob <- text_grob(text, family = f2, size = 15, rot = 0, face = "bold")
as_ggplot(tgrob)

fig2  <- plot_grid(tgrob, gg, gg_legend, nrow=3, rel_heights = c(1, 5, .5), rel_widths = c(1,5,.5))


pdf(paste0(outdir, 'fig3_043021', '.pdf'), height = 11, width = 15)
print (fig2)
dev.off()
###### FIGURE 4 ######
age_sex_dat_groups <- mort_dat

level_list <- as.character(unique(age_sex_dat_groups$age_group_name))
age_sex_dat_groups$newx_order <- factor(age_sex_dat_groups$age_group_name, levels= c(level_list[1], level_list[2], level_list[3], level_list[4], level_list[5], level_list[6], level_list[7], level_list[8],
                                                                                     level_list[9], level_list[10], level_list[11], level_list[12], level_list[13], level_list[14], level_list[15], level_list[16],
                                                                                     level_list[17], level_list[18]), ordered = TRUE)

age_sex_dat_groups$sex_order = factor(age_sex_dat_groups$sex, levels = c("Male", "Female"))


gg <- ggplot(age_sex_dat_groups, aes(x=rev(newx_order), y=mortality_rate_per_100k)) +
  geom_bar(aes(x=newx_order,
               y=mortality_rate_per_100k, fill = sex), stat="identity") +
  facet_wrap(.~ sex_order) +
  theme_bw() + xlab("Age") + ylab("Mortality Rate per 100,000") +
  ggtitle("Figure 4. Police Violence Mortality Rate per 100,000 by Age and Sex in the USA, 1980-2019") +
  theme(text=element_text(family = f2), panel.grid.major = element_line(colour = "grey80"), panel.grid.minor  = element_blank(),
        axis.text.x = element_text(angle = 45, hjust = 1, size = 8), axis.line = element_line(colour = "black"),
        axis.text.y = element_text(size = 8),
        plot.title = element_text(hjust = 0.5, size = 20, face = 'bold'),
        strip.background = element_rect(color="white", fill="white", size=1.5, linetype="solid"),
        strip.text = element_text(size = 15),  panel.border = element_blank(), panel.grid.minor.x=element_blank(),
        panel.grid.major.x=element_blank(),
        legend.position = "none", legend.title = element_blank()) +
  scale_y_continuous(limits = c(0,1.25), expand = c(0, 0)) +
  scale_fill_manual(values = c("#ffdc00", "#b31f38"))
pdf(paste0(outdir, 'fig4_043021', '.pdf'), height = 11, width = 15)

print (gg)
dev.off()


######## TABLE 2 #######
df <- mort_dat_decade
df$race <- gsub("all races", "All Races and Ethnicities", df$race)
df$race <- gsub(" Non-Hispanic, Other races", "Non-Hispanic, Other race\n", df$race)
df$newx <- interaction(df$race, df$decade, lex.order = TRUE)
df$newx <- str_wrap(df$newx, width = 10)

level_list <- unique(df$newx)

df$newx_order <- factor(df$newx, levels= c(level_list[1], level_list[6], level_list[11], level_list[16], level_list[5], level_list[10], level_list[15],
                                           level_list[20], level_list[2], level_list[7], level_list[12], level_list[17],
                                            level_list[4], level_list[9], level_list[14], level_list[19],
                                            level_list[3], level_list[8], level_list[13], level_list[18]), ordered = TRUE)

bins <- quantile(unique(df$best), probs = seq(0,.95,0.19), na.rm = TRUE)
bins <- c(bins, 9.5)
y <- '%.2f'
val <- as.numeric(gsub("\\$|,", "", df$best))
labels <- gsub("(?<!^)(\\d{3})$", ",\\1", bins, perl=T)
bkpt <- as.numeric(bins)
bkpt <- round(bkpt, 2)

lab_break1 = c(paste0(paste0('<',sprintf(y,bkpt[2]))),
               paste0(sprintf(y,bkpt[2]),'-', '<', sprintf(y,bkpt[3])),
               paste0(sprintf(y,bkpt[3]),'-', '<', sprintf(y,bkpt[4])),
               paste0(sprintf(y,bkpt[4]),'-', '<', sprintf(y,bkpt[5])),
               paste0(sprintf(y,bkpt[5]),'-', '<', sprintf(y,bkpt[6])),
               paste0(sprintf(y,bkpt[6]), '+'))

df$Bin <- cut(val, bins, lab_break1)
level_list <- unique(df$Bin)

df[is.na(Bin)]$Bin <- level_list[6]

df_named <- df[, named := paste0(sprintf('%0.2f', best)," (",sprintf('%0.2f', low)," - ",sprintf('%0.2f', high),")")]

gg <- ggplot(df_named, aes(x =newx_order,  y =reorder(state, best),
                     label = named, fill = Bin))  +
  geom_tile(color = "white") + geom_text(size =1.2) +
  coord_fixed(ratio = .2)+
  scale_fill_manual(drop=FALSE, values=brewer.pal(6, "YlOrRd"), name="Age-Standardised Mortality Rate per 100,000 ") +
  scale_x_discrete(position = "top", expand = c(0,0)) +
  scale_y_discrete(position = "left", expand = c(0,0))+
  theme_bw() + xlab("") + ylab("") +
  ggtitle("Table 2: Police Violence Age-Standardised Mortality Rate per 100,000 in the USA\nby Race, Ethnicity, and Decade, 1980-2019") +
  theme(text=element_text(family = f2),
        axis.text.x = element_text(color="black", size=6, angle = 0),
        axis.ticks.x = element_blank(),
        axis.text.y = element_text(color="black", size=6),
        plot.title = element_text(color = "black", face ='bold', size=10, hjust = 0.5, vjust = -4),
        legend.position="bottom",
        legend.direction = "horizontal",
        strip.text = element_text(size = 6),
        legend.background = element_blank(),
        legend.key = element_blank(),
        legend.text=element_text(size=10),
        legend.title=element_text(size = 8),
        legend.key.size = unit(0.5, "cm"),
        panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        axis.line=element_blank(),
        panel.background = element_blank()) +
  guides(fill = guide_legend(title.position = "top"))

ggsave(filename = paste0(outdir, 'FILEPATH'), gg,
       width = 250, height = 200.599, units = "mm", limitsize = FALSE)
