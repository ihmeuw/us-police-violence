import os
import pandas as pd
from pathlib import Path
import numpy as np
import dask.dataframe as dd

draw_cols = list()
for integer in range(0,1000):
    draw_cols.append(f"draw_{integer}")

model_id = 190430
SAVE_DIR = Path(f"FILEPATH")
population_filepath = SAVE_DIR / "FILEPATH"

pop = pd.read_csv(population_filepath)

# read in all year files
df = pd.DataFrame()
for year in list(range(1980,2020)):
    print(year)
    tmp = pd.read_csv(SAVE_DIR / f"FILEPATH")
    df = df.append(tmp)

# only keep wanted columns
df = df[['location_id','year_id','sex_id','age_group_id'] + draw_cols]

# merge on population
original_shape = df.copy().shape[0]
df = pd.merge(df,pop, on=['year_id','location_id','sex_id','age_group_id'],how='left')
assert df.shape[0] == original_shape

pop_for_weights = pop.query("location_id == 102 & sex_id == 3 & year_id >= 2000")
assert np.isclose(pop_for_weights.query("age_group_id == 22")['population'].sum(),
                  pop_for_weights.query("age_group_id != 22")['population'].sum())
total_pop = pop_for_weights.query("age_group_id == 22")['population'].sum()

pop_for_weights = pop_for_weights.query("age_group_id != 22")
# collapse out year
pop_for_weights = pop_for_weights.groupby(['age_group_id'], as_index=False)['population'].sum()
pop_for_weights['total_pop'] = total_pop
# make sure the sum of age_specific pop equals age group 22 pop
assert pop_for_weights.population.sum() == total_pop
# divide pop by total pop for each age group 
pop_for_weights['age_weight'] = pop_for_weights['population'] / pop_for_weights['total_pop']
assert np.isclose(pop_for_weights['age_weight'].sum(), 1)
age_weights = pop_for_weights[['age_group_id','age_weight']]


# merge on location name to the df
from db_queries import get_location_metadata
locs = get_location_metadata(location_set_id=105)[['location_id','location_name']]
df = pd.merge(df,locs)
assert df.shape[0] == original_shape

# split out race and state from the location name
df[['state', "race"]] = df['location_name'].str.split(";", expand=True)
# a blank is all race
df['race'] = df['race'].fillna("all races")

# drop the national all races, we will aggregate to this
races_to_national = df.query("location_id != 102")

# we want to sum population as well
agg_columns = draw_cols + ["population"]

# use dask to save on memory
races_to_national = dd.from_pandas(races_to_national, npartitions=5)
national = races_to_national.groupby(['year_id','sex_id','age_group_id','race']).sum().reset_index().compute()
national['location_id'] = 102
national['location_name'] = "United States"
national['state'] = "United States"

# races_to_national is a dask object and cant be used as needed
df = df.query("location_id != 102")
# combine the state level data with the national
df = df.append(national)

# merge on the age weights for later use
shape = df.shape[0]
df = pd.merge(df, age_weights)
assert shape == df.shape[0]

df.to_csv(SAVE_DIR / "FILEPATH")






