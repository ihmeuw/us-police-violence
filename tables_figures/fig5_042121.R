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
require(xlsx)
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
library(ggplotify, lib.loc = 'FILEPATH')

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

#### FIG 5  ####
library(extrafont)
font_import(
  "FILEPATH"
  , prompt=FALSE)
loadfonts()
f3 <- "Shaker 2 Lancet Regular"
f2 <- "Times"

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
                          panel.border = element_rect(color="white", fill=NA, size=rel(1)),
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

# read in shapefile
us_shp <- readShapePoly(paste0(j,'FILEPATH'))

#get US locs metadata
us_locs = get_location_metadata(location_set_id = 35, gbd_round_id = 6)[parent_id == 102][, c("location_id", "location_name", "local_id")]
us_locs$state_name = sub('.*-', '', us_locs$local_id)
loc_match <- us_locs[, c("location_id", "location_name", "state_name")]

mort_dat_decade <- mort_dat_decade[!(race %like% 'all races'),]
mort_dat_decade <- mort_dat_decade[decade %like% '2010s',]
list <- unique(mort_dat_decade$race)


for (race_eth in list) {

  df <- mort_dat_decade[race %like% race_eth,]
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


  main = ggplot() +
    geom_polygon(data = shp_plt_DF, aes(x=long, y=lat, group = group,
                                        fill = best)) +
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
    scale_fill_gradientn(colors = mapcolors, name = "", limits = c(0, 2.5)) +
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
                                        fill = best)) +
    geom_path(data = shp_plt_DF, aes(x=long, y=lat, group = group), size = 0.2) +
    geom_text(data = centers, aes(x = long, y = lat, label = state_name),
              size = 4,
              fontface = "bold",
              color = "black") +
    scale_fill_gradientn(colors = mapcolors, name = "", limits = c(0, 2.5)) +
    coord_cartesian(xlim = c(-161.5, -154.4), ylim = c(18.5, 22.4)) +
    map_theme_insets + theme(legend.position = 'none')


  ak <- ggplot() +
    geom_polygon(data = shp_plt_DF, aes(x=long, y=lat, group = group,
                                        fill = best)) +
    geom_path(data = shp_plt_DF, aes(x=long, y=lat, group = group), size = 0.2) +
    geom_text(data = centers, aes(x = long, y = lat, label = state_name),
              size = 4,
              fontface = "bold",
              color = "black") +
    scale_fill_gradientn(colors = mapcolors, name = "", limits = c(0, 2.5)) +
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

us_map_nhb <- map_nhw + theme(legend.position="none")
us_map_nhw <- map_nhb + theme(legend.position="none")
map_nho <- map_nho + theme(legend.position="none")
map_har <- map_har + theme(legend.position="none")




us_map_nhb <- arrangeGrob(us_map_nhb)
us_map_nhw <- arrangeGrob(us_map_nhw)
us_map_har <- arrangeGrob(map_nho)
us_map_other <- arrangeGrob(map_har)

us_multi<- plot_grid(us_map_nhb, us_map_nhw, us_map_har, us_map_other, ncol = 2, nrow = 2,axis = 'l', align = 'v')
text <- "Age-Standardised Mortality Rate per 100,000, 2010-2019"
tgrob <- text_grob(text, family = f2, size = 15)
as_ggplot(tgrob)

us_multi <- plot_grid(tgrob, us_multi, nrow =2,  rel_widths = c(.3,2), rel_heights = c(.3,2))

us_ASMR_multi<- plot_grid(us_multi, legend, ncol =1, align = 'v', axis = 'm', rel_widths = c(3, .2),  rel_heights= c(2.5, .2))



mort_dat_all <- data.table(read.csv(paste0(data_dir, "FILEPATH")))
dt <- mort_dat_all[location %like% "United States",]

dt$race[dt$race == " Non-Hispanic, Black"] <- "1Non-Hispanic, Black"
dt$race[dt$race == " Hispanic, Any race"] <- "2Hispanic, Any Race"
dt$race[dt$race == "all races"] <- "3All Races"
dt$race[dt$race == " Non-Hispanic, White"] <- "4Non-Hispanic, White"
dt$race[dt$race == " Non-Hispanic, Other races"] <- "5Non-Hispanic, Other race"

colsname <- c("Non-Hispanic, Black", "Hispanic, Any Race", "All Races and Ethnicities", 
              "Non-Hispanic, White",  "Non-Hispanic, Other race")

# top half
# write graph to grob
us_death =
  ggplot(dt, aes(x = year_id, y = dt$Age.Standardized.Mortality.Rate.Per.100k, group = dt$race)) +
  geom_line(aes(colour = race)) +
  geom_ribbon(aes(ymin=dt$Age.Standardized.Mortality.Rate.Per.100k.Lower, ymax=dt$Age.Standardized.Mortality.Rate.Per.100k.Upper, fill = dt$race), linetype=2, alpha=0.2) +
  labs(x ='Year', y = 'Age-Standardised Mortality Rate per 100,000',
       title = paste0("United States Police Violence Age-Standardised Mortality Rate\nper 100,000 with 95% Uncertainty Intervals")) +
  theme_bw() +
  scale_fill_manual(values = c("#b31f38", "#0d4e93", "#ffdc00", "#8b2269", "#006a37"), labels = colsname) +
  scale_color_manual(values=c("#b31f38", "#0d4e93", "#ffdc00", "#8b2269", "#006a37"), labels = colsname) +
  scale_x_continuous(breaks =seq(1980, 2019, by =5), expand = c(0, 0)) +
  scale_y_continuous(expand = c(0, 0)) +
  guides(fill=FALSE) +
  theme(text=element_text(family =f2), panel.grid.major = element_blank(),
        panel.grid.minor  = element_blank(),
        axis.line = element_line(colour = "black"),
        plot.title = element_text(hjust = 0.5, size = 15), legend.key.width = unit(1.2, "cm"),
        legend.background = element_rect(fill="#FDF9D8", size = 0.5,
                                         linetype = "solid"),
        axis.text.y = element_text(size = 15, face="bold"),
        axis.title.y = element_text(size = 15, face="bold"),
        axis.title.x = element_text(size = 15),
        axis.text.x = element_text(size = 15, face="bold"),
        legend.position = c(0.70, 0.85),
        legend.text = element_text(size = 16),
        legend.title = element_blank(), plot.margin = margin(0.2, 0.4, 0, 0.3, "cm"))

fig_1_top<- plot_grid(us_death, us_ASMR_multi, ncol =2,  rel_widths = c(1,2), rel_heights = c(1,1))

text <- "Figure 5. Police Violence Age-Standardised Mortality Rate per 100,00 in the USA, 1980-2019"
tgrob <- text_grob(text, family = f2, size = 20, face = "bold")
as_ggplot(tgrob)

fig_1_top_test <- plot_grid(tgrob, fig_1_top, nrow =2,  rel_widths = c(.1,2), rel_heights = c(.1,2))

us_locs$state_name = sub('.*-', '', us_locs$local_id)

library(grid)

df_all_mort <- merge(mort_dat_all, loc_match, by.x ="location", by.y= "location_name", all.x = TRUE)

draw_line = function(loc = NULL, data = df_all_mort, us_locs = us_locs) {

  dt <- df_all_mort[location_id.y ==loc]
  max <- round(max(dt$Age.Standardized.Mortality.Rate.Per.100k.Upper),1)

  grob <- grobTree(textGrob(us_locs[which(us_locs$location_id == loc),]$state_name, x=0.05,  y=0.90, hjust=0,
                          gp=gpar(col="black", fontsize=10)))
  plot_death =
    ggplot(dt, aes(x = year_id, y = dt$Age.Standardized.Mortality.Rate.Per.100k, group = dt$race)) +
    geom_line(aes(colour = race)) +
    geom_ribbon(aes(ymin=dt$Age.Standardized.Mortality.Rate.Per.100k.Lower, ymax=dt$Age.Standardized.Mortality.Rate.Per.100k.Upper, fill = dt$race), linetype=2, alpha=0.2) +
    labs(x ='', y = '',
         title = paste0("")) +
    theme_bw() +
    scale_fill_manual(values = c("#0d4e93", "#b31f38", "#006a37", "#8b2269", "#ffdc00")) +
    scale_color_manual(values=c("#0d4e93", "#b31f38", "#006a37", "#8b2269", "#ffdc00")) +
    scale_x_continuous(expand = c(0, 0)) +
    scale_y_continuous(breaks=c(0, round((max/2),1), max-0.1), expand = c(0, 0), limits = c(0.0, NA)) +
   annotation_custom(grob) +
    theme_bw() +
    theme( panel.grid.minor = element_blank(),
           panel.grid.major = element_blank(),
           axis.text.y = element_text(face = "bold", size = 9),
           axis.ticks.y = element_blank(),
           axis.text.x = element_blank(),
           axis.ticks.x = element_blank(),
           legend.title = element_blank(),
           legend.position = "none",
           plot.title = element_blank(),
           plot.margin = margin(0, 0.4, 0, 0.2, "cm"))


  comprss = function(tx) {
    div = findInterval(as.numeric(gsub("\\,", "", tx)), c(0, 1e3, 1e6, 1e9, 1e12))
    paste0(round( as.numeric(gsub("\\,", "", tx)) / 10 ^ (3 * (div - 1)), 1),
           c("","K","M","B","T")[div])}



  return(plot_death)
}

map_locs = c(524, 568, 552, 542, 555, 529, 544, 570, 549, 557, 564, 546, 572, 545, 561, 553, 562,
             560, 535, 573, 550, 538, 536, 537, 558, 569, 531, 530, 551, 567, 528, 539, 548, 565,
             540, 571, 556, 543, 527, 525, 554, 559, 526, 547, 523, 533, 563, 566, 541, 532, 534)
map_locs = c(523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539,
             540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 
             557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573)

empty = ggplot() + theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
                         panel.background = element_blank())

line_list = list()
for (i in 1:length(map_locs)) {
  line_list[[i]] = draw_line(loc = map_locs[i], data = df_all_mort, us_locs = us_locs)
}

# line_list = sort(line_list)

############################

fig_1_bottom <- arrangeGrob(line_list[[1]], line_list[[2]], line_list[[3]], line_list[[4]], 
line_list[[5]], line_list[[6]], line_list[[7]],line_list[[8]], line_list[[9]], line_list[[10]], 
line_list[[11]], line_list[[12]], line_list[[13]], line_list[[14]], line_list[[15]], line_list[[16]], 
line_list[[17]], line_list[[18]], line_list[[19]], line_list[[20]], line_list[[21]], line_list[[22]], 
line_list[[23]], line_list[[24]], line_list[[25]], line_list[[26]], line_list[[27]], line_list[[28]],
line_list[[29]], line_list[[30]], line_list[[31]], line_list[[32]], line_list[[33]], line_list[[34]], 
line_list[[35]], line_list[[36]], line_list[[37]], line_list[[38]], line_list[[39]], line_list[[40]], 
line_list[[41]], line_list[[42]], line_list[[43]], line_list[[44]], line_list[[45]], line_list[[46]], 
line_list[[47]], line_list[[48]], line_list[[49]], line_list[[50]], line_list[[51]],
                            ncol = 13, nrow = 4)

text <- "Age-Standardised Mortality Rate per 100,000"
tgrob <- text_grob(text, family = f2, size = 15, rot = 90, face = "bold")
as_ggplot(tgrob)

fig_1_bottom_1 <- as_grob(fig_1_bottom)
tgrob_1 <- as_grob(tgrob)
fig_1_botttom_test <- plot_grid(tgrob_1, fig_1_bottom_1, ncol =2,  rel_widths = c(.1, 3),  rel_heights= c(.5, 2))

lay1 <- rbind(c(1),
              c(1),
              c(1),
              c(1),
              c(2),
              c(2)
              )

cairo_pdf("FILEPATH", width = 20, height = 15)
grid.arrange(arrangeGrob(fig_1_top_test, fig_1_botttom_test, layout_matrix = lay1))
dev.off()




