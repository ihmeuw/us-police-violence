import pandas as pd
import numpy as np
 
df = pd.read_csv("FILEPATH")
age_weights = df[['age_group_id','age_weight']].drop_duplicates()
draw_cols = list()
for integer in range(0,1000):
    draw_cols.append(f"draw_{integer}")
    
# calculate asmr for every state in a given year range
def create_asmr_dataframe(df, start_year, end_year, race='all races'):
    df_asmr_by_years = df.query(f"location_id != 102 & race == '{race}' & year_id >= {start_year} & year_id < {end_year}")
    df_asmr_by_years = df_asmr_by_years.groupby(['location_id','state','race','age_group_id'], as_index=False)[draw_cols+['population']].sum() 
    for col in draw_cols:
        df_asmr_by_years[col] = (df_asmr_by_years[col] / df_asmr_by_years['population']) * 100000
    df_asmr_by_years = df_asmr_by_years.merge(age_weights)
    for col in draw_cols:
        df_asmr_by_years[col] = (df_asmr_by_years[col] * df_asmr_by_years['age_weight'])
    df_asmr_by_years = df_asmr_by_years.groupby(['location_id','state','race'], as_index=False)[draw_cols].sum()   
    df_asmr_by_years['best'] = df_asmr_by_years[draw_cols].mean(axis=1)
    df_asmr_by_years['low'] = np.percentile(df_asmr_by_years[draw_cols], 2.5,axis=1)
    df_asmr_by_years['high'] = np.percentile(df_asmr_by_years[draw_cols], 97.5,axis=1)
    df_asmr_by_years.drop(draw_cols, axis=1, inplace=True)
    df_asmr_by_years = df_asmr_by_years.sort_values(['best'], ascending=False)
    return df_asmr_by_years

asmr_by_state_80s = pd.DataFrame()
for race in df.race.unique():
    asmr_by_state_all_years = create_asmr_dataframe(df, 1980, 1990, race)
    asmr_by_state_all_years['decade'] = "1980s"
    asmr_by_state_80s = asmr_by_state_80s.append(asmr_by_state_all_years)


asmr_by_state_90s = pd.DataFrame()
for race in df.race.unique():
    asmr_by_state_all_years = create_asmr_dataframe(df, 1990, 2000, race)
    asmr_by_state_all_years['decade'] = "1990s"
    asmr_by_state_90s = asmr_by_state_90s.append(asmr_by_state_all_years)

asmr_by_state_00s = pd.DataFrame()
for race in df.race.unique():
    asmr_by_state_all_years = create_asmr_dataframe(df, 2000, 2010, race)
    asmr_by_state_all_years['decade'] = "2000s"
    asmr_by_state_00s = asmr_by_state_00s.append(asmr_by_state_all_years)

asmr_by_state_10s = pd.DataFrame()
for race in df.race.unique():
    asmr_by_state_all_years = create_asmr_dataframe(df, 2010, 2020, race)
    asmr_by_state_all_years['decade'] = "2010s"
    asmr_by_state_10s = asmr_by_state_10s.append(asmr_by_state_all_years)

asmr_by_state_race_all_years = pd.DataFrame()
asmr_by_state_race_all_years = asmr_by_state_race_all_years.append(asmr_by_state_80s)
asmr_by_state_race_all_years = asmr_by_state_race_all_years.append(asmr_by_state_90s)
asmr_by_state_race_all_years = asmr_by_state_race_all_years.append(asmr_by_state_00s)
asmr_by_state_race_all_years = asmr_by_state_race_all_years.append(asmr_by_state_10s)

asmr_by_state_race_all_years.to_csv("FILEPATH", index=False)
