import pandas as pd

df = pd.read_csv("FILEPATH")
 
# remove the national estimate
df['race_ethnicity'] = df['race_ethnicity'].replace(' Hispanic, Any race', 'Hispanic, Any race')
df['race_ethnicity'] = df['race_ethnicity'].replace(' Non-Hispanic, Other races', 'Non-Hispanic, Other races')
df['race_ethnicity'] = df['race_ethnicity'].replace(' Non-Hispanic, Black', 'Non-Hispanic, Black')
df['race_ethnicity'] = df['race_ethnicity'].replace(' Non-Hispanic, White', 'Non-Hispanic, White')
df = df.query("location_id != 102")

# create a df for each source
t1 = df.copy().query("sub_source == 'STGPR_result'")
t1.drop("sub_source",axis=1, inplace=True)

t2 = df.copy().query("sub_source == 'Fatal_Encounters'")
t2 = t2.rename(columns={"deaths":"Fatal_Encounters"})
t2.drop("deaths_lower",axis=1, inplace=True)
t2.drop("deaths_upper",axis=1, inplace=True)
t2.drop("sub_source",axis=1, inplace=True)


t3 = df.copy().query("sub_source == 'MPV'")
t3 = t3.rename(columns={"deaths":"MPV"})
t3.drop("deaths_lower",axis=1, inplace=True)
t3.drop("deaths_upper",axis=1, inplace=True)
t3.drop("sub_source",axis=1, inplace=True)


t4 = df.copy().query("sub_source == 'NVSS'")
t4 = t4.rename(columns={"deaths":"NVSS"})
t4.drop("deaths_lower",axis=1, inplace=True)
t4.drop("deaths_upper",axis=1, inplace=True)
t4.drop("sub_source",axis=1, inplace=True)


t5 = df.copy().query("sub_source == 'The_Counted'")
t5 = t5.rename(columns={"deaths":"The_Counted"})
t5.drop("deaths_lower",axis=1, inplace=True)
t5.drop("deaths_upper",axis=1, inplace=True)
t5.drop("sub_source",axis=1, inplace=True)

# combine all of the dataframes
original_shape = t1.shape[0]
fin = t1.merge(t2, on=['location_id','race_ethnicity','state','year_id'], how='left')
fin = fin.merge(t3, on=['location_id','race_ethnicity','state','year_id'], how='left')
fin = fin.merge(t4, on=['location_id','race_ethnicity','state','year_id'], how='left')
fin = fin.merge(t5, on=['location_id','race_ethnicity','state','year_id'], how='left')
assert original_shape == fin.shape[0]

fin = fin.query("race_ethnicity != 'all races'")
fin = fin.query("year_id <= 2018")
fin = fin.groupby(['location_id','race_ethnicity','state'], as_index=False)['deaths','NVSS'].sum()
fin['missed_deaths'] = fin['deaths'] - fin['NVSS']
fin['percent_missed'] = (fin['missed_deaths'] / fin['deaths']) * 100

fin.to_csv("FILEPATH")




