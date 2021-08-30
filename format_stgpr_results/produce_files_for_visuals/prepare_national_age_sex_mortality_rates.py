# calculate age sex mortality rates for visuals

import pandas as pd
from db_queries import get_age_metadata
 
draw_cols = list()
for integer in range(0,1000):
    draw_cols.append(f"draw_{integer}")
    
needed_columns = ["sex_id","age_group_id","gpr_mean","population","mortality_rate_per_100k","age_group_name","sex"]

df = pd.read_csv("FILEPATH")
save_dir = "FILEPATH"

# filter to U.S. every race
df = df.query("location_id == 102 & race == 'all races'")

# under 5 age group
df['age_group_id'] = df['age_group_id'].replace(2,1)
df['age_group_id'] = df['age_group_id'].replace(3,1)
df['age_group_id'] = df['age_group_id'].replace(34,1)
df['age_group_id'] = df['age_group_id'].replace(238,1)
df['age_group_id'] = df['age_group_id'].replace(388,1)
df['age_group_id'] = df['age_group_id'].replace(389,1)
# 85+ age group
df['age_group_id'] = df['age_group_id'].replace(31,160)
df['age_group_id'] = df['age_group_id'].replace(32,160)
df['age_group_id'] = df['age_group_id'].replace(235,160)

# collapse out year and aggregate to age groups
df = df.groupby(['location_id','age_group_id','sex_id','race','state'], as_index=False)[draw_cols+['population']].sum()

# for reference calculate avg deaths
df['gpr_mean'] = df[draw_cols].mean(axis=1)

# convert deaths to mortality rate per 100k
for column in draw_cols:
    df[column] = (df[column] / df['population']) * 100000
    
# calcualte avg mortality rate per 100k by age group
df['mortality_rate_per_100k'] = df[draw_cols].mean(axis=1)

# drop draw columns
df = df.drop(draw_cols, axis=1)

# for visual add sex names
df['sex'] = df['sex_id']
df['sex'] = df['sex'].replace(1,"Male")
df['sex'] = df['sex'].replace(2,"Female")

# for visual add age names
ages = get_age_metadata(age_group_set_id=2)
ages = ages[['age_group_id','age_group_name']]
ages['age_group_id'] =ages['age_group_id'].replace(27, 160) 
ages['age_group_name'] =ages['age_group_name'].replace("Age-standardized", "85+ Years") 
ages['age_group_id'] =ages['age_group_id'].replace(21, 30) 
ages['age_group_name'] =ages['age_group_name'].replace("80 plus", "80-84") 

original_shape = df.shape[0]
df = df.merge(ages)
assert df.shape[0] == original_shape

df = df[needed_columns]

df.to_csv(save_dir+"FILEPATH")
