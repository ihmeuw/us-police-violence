rm(list = ls())
library(data.table)
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
source("FILEPATH")
require(ggplot2) 
require(plyr)
require(RColorBrewer)
require(reshape2)
require(stringr)
require(tidyverse)
library(Cairo, lib = "FILEPATH")
library(cowplot, lib = "FILEPATH")
library(scales)

data = read.csv("FILEPATH")
head(data)

#################### DATA COLLECTION ###########################
if (Sys.info()[1]=="Windows") {
  root <- "FILEPATH"
  user <- Sys.getenv("USERNAME")
} else {
  root <- "FILEPATH"
  user <- Sys.getenv("USER")
  print(commandArgs())
  topic_id <- commandArgs()[8]
  imp <- commandArgs()[9]
  loc_id <- commandArgs()[10]
  step <- commandArgs()[11]
  cvid <- commandArgs()[12]
  cond <- commandArgs()[13]
  outfile <- commandArgs()[14]
}

f3 <- "Shaker 2 Lancet Regular"

library(extrafont)

font_import()
options(OutDec="\u0B7")


#------------ Standard Method for Data Collection ---------------
shp_num <- c("\u25A0", "\u25CF", "\u25C6", "\u2B23", "\u25CF", "\u25B2", "\u25BC", "\u25C0")

shp_col <- c("#9f7aac", "#aeb5d9","#0099b499","#e3afad")

shp_size <- c(3, 3, 2, 2, 3, 3, 3,3)

data_breaks <- seq(0, 4000, 500)
data_labels <- as.character(data_breaks)
data_labels[!(data_breaks%%50==0)] <- ''
data_labels[1] <- "0"
max_y <- max(data$rate_police_violence, na.rm = T)
if (max_y < 50){
  y_up <- ceiling(max_y/5)*5
} else if (max_y < 200) {
  y_up <- ceiling(max_y/10)*10 
} else if (max_y < 1000){
  y_up <- ceiling(max_y/50)*50
} else {
  y_up <- ceiling(max_y/100)*100
}
y_breaks <- pretty(c(0,data$rate_police_violence, max_y), n = 5)
y_labs <- lapply(y_breaks, as.character)
y_labs <- as.data.table(unlist(y_labs))
y_labs[nchar(V1) > 4, V1 := paste0(substr(V1,1,(nchar(V1)-3)), as.character("\u202F"),
                                   substr(V1, (nchar(V1) -2), nchar(V1)))]

cond = "T"
if (cond == "T"){
  h <- 58
  w <- 90
  l_pos <- 1.32
} else {
  h <- 105
  w <- 91.5
  l_pos <- 1.12
}

data$re <- factor(data$re, levels = c("Non-Hispanic, White","Non-Hispanic, Black" , "Non-Hispanic, Other races", "Hispanic, Any race"))
data <- data[order(data$re),]

gg <- ggplot(data,aes(x = rate_incarceration, y = rate_police_violence)) +
  theme_bw() +
  geom_point(aes(colour = re), alpha=0.6) +
  geom_smooth(method = "lm") +
  labs(x = paste0("Incarceration", " rate (per 100\u202F000)"),
       y = paste0("Police Violence", " rate (per 100\u202F000)"),
       title = "State Police Violence and Incarceration Rate, by Race",
       caption = "*Only including state-years with a population of 700,000 or greater") +
  
  scale_y_continuous(limits = c(0,max(y_breaks)), breaks = y_breaks, labels = y_labs$V1, expand = c(0,0)) +
  scale_x_continuous(breaks = data_breaks, labels = data_labels, limit = c(0,4000), expand = c(0,0)) +
  
  scale_shape_manual(values = shp_num, name = "year range") +
  scale_size_manual(values = shp_size, name = "race") +
  scale_color_manual(values = shp_col, name = "race") +
  scale_fill_manual(values = shp_col, name = "race") +
  theme(plot.margin=unit(c(10,5,2,2),"mm"),
        text=element_text(size=6.5, family = f3),  
        panel.grid = element_blank(),
        panel.border = element_blank(), 
        plot.title = element_text(color="black", size=10),
        
        axis.line = element_line(size = 0.2334312),
        axis.ticks = element_line(size = 0.2334312),
        axis.ticks.length=unit(1.118, "mm"),
        axis.title = element_text(size = 6.5, face = "bold"),
        axis.text.y = element_text(size = 6.5),
        axis.text.x = element_text(size = 6.5, vjust = 0.5),
        
        legend.margin=margin(t=2, r=3, b=0, l=14, unit="mm"),
        legend.spacing.x = unit(0.01, 'mm'),
        legend.spacing.y = unit(0.01, 'mm'),
        legend.position = c(0.8, l_pos - 0.2), 
        legend.title = element_text(size = 6.5, face = "bold"), 
        legend.box = "vertical",
        legend.key.size = unit(0.1,"cm"),
        legend.text = element_text(size = 6.5)) +
  
  guides(shape=guide_legend(nrow=4,byrow=TRUE, title.position = "top"),
         size = guide_legend(title.position = "top"),
         color = guide_legend(title.position = "top"),
         fill = guide_legend(title.position = "top"))

 g_legend<-function(a.gplot){
   tmp <- ggplot_gtable(ggplot_build(a.gplot))
   leg <- which(sapply(tmp$grobs, function(x) x$name) == "guide-box")
   legend <- tmp$grobs[[leg]]
   return(legend)}

 legend <- g_legend(gg)

 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[22, 1:4] <-
   legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[23, 1:4]

 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[13, 1:4] <-
   legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[15, 1:4]

 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[14, 1:4] <-
   legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[16, 1:4]

 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[23, 2] <- 8
 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[23, 4] <- 8

 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[15, 2] <- 6
 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[15, 4] <- 6

 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[16, 2] <- 6
 legend$grobs$`99_091d49b3b563502eae74591599b0f7eb`$layout[16, 4] <- 6

 plt_gtable <- ggplot_gtable(ggplot_build(gg))
 leg <- which(sapply(plt_gtable$grobs, function(x) x$name) == "guide-box")

 plt_gtable$grobs[[leg]] <- legend

# Save file
ggsave(file = "FILEPATH", gg, device = cairo_pdf,
       width = w, height = h, units = "mm", limitsize = F,
       dpi = 320)
