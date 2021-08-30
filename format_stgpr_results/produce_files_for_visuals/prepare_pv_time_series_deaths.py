import pandas as pd 

df = pd.read_csv("FILEPATH")
df = df.groupby(['year_id','re','state','sub_source'], as_index=False)['deaths','deaths_adjusted'].sum()
 
raw_data = df[['year_id','re','state','deaths','sub_source']]
raw_data['model_type'] = 'raw_data'

crosswalk_results = df[['year_id','re','state','deaths_adjusted','sub_source']]
crosswalk_results['model_type'] = 'crosswalk results'

stgpr_out = pd.read_csv("FILEPATH")
stgpr_out = stgpr_out.query("sub_source == 'STGPR_result'")
stgpr_out = stgpr_out[['year_id','race_ethnicity','state','deaths','sub_source']]
stgpr_out['model_type'] = "STGPR Result"
stgpr_out["sub_source"] = "IHME Model"

raw_data = raw_data.rename(columns={"state":"location"})
crosswalk_results = crosswalk_results.rename(columns={"state":"location",
                                                      "deaths_adjusted":"deaths"})
stgpr_out = stgpr_out.rename(columns={"state":"location",
                                      "race_ethnicity":"re"})

final = raw_data.append(crosswalk_results)
final = final.append(stgpr_out)

final.to_csv("FILEPATH")
