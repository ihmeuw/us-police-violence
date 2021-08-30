# Purpose: Prep NCHS bridged race population estimates from 1990-2019.
rm(list=ls())
library(data.table)
pop <- readRDS("FILEPATH")

# location, year, age, and sex
pop[, year_id := year]
pop[, location_id := 102]
pop[, sex_id := 3]
pop[, age_group_id := 22]

# 1 = non-Hispanic White
# 2 = non-Hispanic Black
# 3 = non-Hispanic AIAN
# 4 = non-Hispanic API
# 7 = Hispanic of any race
race_map = c(
  "1" = 5,
  "2" = 4,
  "3" = 6,
  "4" = 3,
  "7" = 2
)
pop$population_group_id <- race_map[as.character(pop$race)]

pop <- pop[, sum(pop), by = c("year_id", "location_id", "age_group_id", "sex_id", "population_group_id")]
setnames(pop, "V1", "population")

stopifnot((2019 - 1990 + 1) * 5 == dim(pop)[1])

write.csv(
  pop, file = "FILEPATH", row.names = FALSE
)
