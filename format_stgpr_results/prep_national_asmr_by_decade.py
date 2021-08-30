import pandas as pd
import numpy as np

def bin_decade(row):
    year = row['year_id']
    if ((year >= 1980) & (year < 1990)):
        return "1980s"
    if ((year >= 1990) & (year < 2000)):
        return "1990s"
    if ((year >= 2000) & (year < 2010)):
        return "2000s"
    if ((year >= 2010) & (year < 2020)):
        return "2010s"

draw_cols = list()
for integer in range(0,1000):
    draw_cols.append(f"draw_{integer}")

    model_id = 190430


dir_path = "FILEPATH"
current = pd.read_csv("FILEPATH")


df = pd.read_csv("FILEPATH")
age_weights = df[['age_group_id','age_weight']].drop_duplicates()

df['decade'] = df.apply(lambda x: bin_decade(x), axis=1)


df = df.groupby(['location_id','race','age_group_id','decade'], as_index=False)[draw_cols+['population']].sum()
df = df.merge(age_weights)

for col in draw_cols:
    df[col] = (df[col] / df['population']) * 100000


for col in draw_cols:
        df[col] = (df[col] * df['age_weight'])

df = df.groupby(['location_id','race','decade'], as_index=False)[draw_cols].sum()

df['best'] = df[draw_cols].mean(axis=1)
df['low'] = np.percentile(df[draw_cols], 2.5,axis=1)
df['high'] = np.percentile(df[draw_cols], 97.5,axis=1)

df = df.drop(draw_cols, axis=1)

united_states = df.query("location_id == 102")
united_states['state'] = "United States"
united_states = united_states[current.columns]

for location_id in current.location_id.unique():
    for decade in ['1980s', '1990s', '2000s', '2010s']:
        old_value = current[((current['location_id'] == location_id) & (current['decade'] == decade))]['best'].iloc[0]
        new_value = df[((df['location_id'] == location_id) & (df['decade'] == decade))]['best'].iloc[0]
        assert np.isclose(old_value, new_value)
        old_value = current[((current['location_id'] == location_id) & (current['decade'] == decade))]['high'].iloc[0]
        new_value = df[((df['location_id'] == location_id) & (df['decade'] == decade))]['high'].iloc[0]
        assert np.isclose(old_value, new_value)
        old_value = current[((current['location_id'] == location_id) & (current['decade'] == decade))]['low'].iloc[0]
        new_value = df[((df['location_id'] == location_id) & (df['decade'] == decade))]['low'].iloc[0]
        assert np.isclose(old_value, new_value)




united_states.to_csv("FILEPATH", index=False)
