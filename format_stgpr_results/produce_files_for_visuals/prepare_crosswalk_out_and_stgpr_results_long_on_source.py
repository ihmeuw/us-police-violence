# combine STGPR results with the crosswalk output 
# this is to create a visual that overlays st-gpr over the model's input data
 
import pandas as pd
import numpy as np
model_id = 190430

draw_cols = list()
for integer in range(0,1000):
    draw_cols.append(f"draw_{integer}")
    
df = pd.read_csv(f"FILEPATH")
save_dir = "FILEPATH"

crosswalk_out = pd.read_csv("FILEPATH")

# groupby before collapsing draws
df = df.groupby(['location_id','race','state','year_id'], as_index=False)[draw_cols].sum()

# only the stpgr results will have high/low estimates
df['deaths'] = df[draw_cols].mean(axis=1)
df['deaths_upper'] = np.percentile(df[draw_cols], 97.5,axis=1)
df['deaths_lower'] = np.percentile(df[draw_cols], 2.5, axis=1)

# drop draw columns
df = df[['deaths','deaths_lower','deaths_upper','year_id','state','location_id','race']]

crosswalk_out['race'] = crosswalk_out['re']
# keep only the columns in df
crosswalk_out = crosswalk_out[['age_group_id','sex_id','sub_source','deaths','location_id','year_id','race','state']]

# collapse out age-sex of crosswalk data 
crosswalk_out = crosswalk_out.groupby(['location_id','race','state','sub_source','year_id'], as_index=False)[['deaths']].sum()

# append the crosswalk data to the stgpr results
df = df.append(crosswalk_out)

# data with missing sub_souce is STGPR
df['sub_source'] = df.sub_source.fillna("STGPR_result")
df = df.rename(columns = {"race":"race_ethnicity"})

df.to_csv(save_dir + "FILEPATH", index=False)
