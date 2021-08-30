import pandas as pd
import sys
from getpass import getuser
sys.path.append("FILEPATH")
from format_sub_sources import format_sub_sources


input_dir = "FILEPATH"

df = pd.read_csv("FILEPATH")
fe = format_sub_sources(['Fatal_Encounters'])
drop_fe_causes = [
    'Vehicle',
    'Drug overdose',
    'Undetermined',
    'Medical emergency',
    'Other',
    'Unknown'
]
fe_dropped = fe.loc[~fe.int_cause.isin(drop_fe_causes)].assign(
    sub_source='Fatal_Encounters_causes_dropped')
df = df.query("sub_source == 'NVSS'")
df = df.append(fe).append(fe_dropped).groupby(
    ['sub_source', 'year_id'], as_index=False)['deaths'].sum()
df = df.set_index(['sub_source', 'year_id'])


def make_denom(compare_year, df):
    return pd.DataFrame(
        df.groupby(level=['sub_source']).apply(lambda d: int(
            d.query(f"year_id == {compare_year}")['deaths'].unique())),
        columns=['deaths']
    )


plot_df = pd.concat(
    [df.div(make_denom(x, df)).reset_index().assign(compare_year=x) for x in [2000, 2005, 2008]],
)
plot_df2 = plot_df.query(f"year_id >= 2000 & year_id <= 2017")
plot_df2.to_csv("FILEPATH", index=False)
