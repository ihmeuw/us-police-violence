import pandas as pd
import numpy as np
 
def create_asmr_dataframe_by_year_location(df):
    df_asmr_by_years = df.copy()
    df_asmr_by_years = df_asmr_by_years.groupby(['location_id','state','race','age_group_id',"year_id"], as_index=False)[draw_cols+['population']].sum() 
    for col in draw_cols:
        df_asmr_by_years[col] = (df_asmr_by_years[col] / df_asmr_by_years['population']) * 100000
    df_asmr_by_years = df_asmr_by_years.merge(age_weights)
    for col in draw_cols:
        df_asmr_by_years[col] = (df_asmr_by_years[col] * df_asmr_by_years['age_weight'])
    df_asmr_by_years = df_asmr_by_years.groupby(['location_id','state','race','year_id'], as_index=False)[draw_cols].sum()   
    df_asmr_by_years['best'] = df_asmr_by_years[draw_cols].mean(axis=1)
    df_asmr_by_years['low'] = np.percentile(df_asmr_by_years[draw_cols], 2.5,axis=1)
    df_asmr_by_years['high'] = np.percentile(df_asmr_by_years[draw_cols], 97.5,axis=1)
    df_asmr_by_years.drop(draw_cols, axis=1, inplace=True)
    df_asmr_by_years = df_asmr_by_years.sort_values(['best'], ascending=False)
    return df_asmr_by_years


df = pd.read_csv("FILEPATH")
age_weights = df[['age_group_id','age_weight']].drop_duplicates()
draw_cols = list()
for integer in range(0,1000):
    draw_cols.append(f"draw_{integer}")

df = create_asmr_dataframe_by_year_location(df)

df = df.rename(columns={"state":"location",
                    "best":"Age Standardized Mortality Rate Per 100k",
                    "low":"Age Standardized Mortality Rate Per 100k Lower",
                    "high":"Age Standardized Mortality Rate Per 100k Upper"})

df.to_csv("FILEPATH", index=False)
