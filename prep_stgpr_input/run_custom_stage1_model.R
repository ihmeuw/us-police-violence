# Purpose: Custom stage 1 model
rm(list=ls())
library(tidyverse)

base_dir <- "FILEPATH"
working_dir <- paste0(base_dir, "FILEPATH")


run_one_model <- function(data) {
	data <- data %>% mutate(year_id = as.numeric(year_id))
	formula <- deaths ~ year_id + offset(log(sample_size))
  glm.control(maxit = 1000)
  pois_model <- glm(
  	formula = formula,
    family = poisson(),
    data = data)
  preds <- data %>% distinct(location_id, year_id, age_group_id, sex_id, .keep_all = TRUE) %>%
    modelr::add_predictions(
  	  pois_model, var = "cv_custom_stage_1", type = "response")
  data_and_preds <- bind_rows(data, preds) %>%
    mutate(converged = pois_model$converged)
  return(data_and_preds)
}

print("Reading in the data")
data <- readxl::read_excel(paste0(working_dir, "FILEPATH")) %>%
  mutate(deaths = val)

print("Running models")
data <- data %>%
  group_by(location_id, age_group_id, sex_id) %>%
  group_modify(~ run_one_model(.x)) %>%
  ungroup()

check_conv <- distinct(data, location_id, age_group_id, sex_id, converged)
print(sprintf("%d out of %d models converged", sum(check_conv$converged), nrow(check_conv)))

print("Saving the data")
data <- data %>% select(
	location_id, year_id, age_group_id, sex_id, sub_source,
	val, cv_custom_stage_1, sample_size, converged)
write_csv(data, paste0(working_dir, "FILEPATH"))

data <- data %>% filter(!is.na(cv_custom_stage_1)) %>%
  select(location_id, year_id, age_group_id, sex_id, cv_custom_stage_1)
stopifnot(nrow(data) == (51 * 4 + 51 + 1) * (2019 - 1980 + 1))
stopifnot(!any(is.na(data)))
stopifnot(!any(duplicated(select(data, location_id, year_id, age_group_id, sex_id))))
stopifnot(all(data$cv_custom_stage_1 > 0))

write_csv(data, paste0(working_dir, "FILEPATH"))