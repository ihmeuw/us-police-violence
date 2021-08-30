import pandas as pd
import numpy as np
from cod_prep.utils import report_duplicates
from pathlib import Path

WORKING_DIR = Path(
    "FILEPATH"
)
OUT_DIR = Path(
    "FILEPATH"
)

model_versions = [
    '2021_04_19_pct_firearm_only',
    '2021_04_20_pct_firearm_only_drop_re',
    '2021_04_22_no_cov',
    '2021_04_22_drop_fe_2005_2012'
]


def get_results():
    # Get results
    results = pd.concat([
        pd.read_csv(
            WORKING_DIR / mv / "FILEPATH",
            usecols=['state', 're', 'year_id', 'sub_source', 'deaths_adjusted', 'deaths']
        ).assign(model_version=mv) for mv in model_versions
    ])

    cols = ['state', 're', 'age_group_id', 'sex_id', 'year_id', 'sub_source']
    scatter = pd.DataFrame(columns=cols)
    for mv in model_versions:
        df = pd.read_csv(
            WORKING_DIR / mv / "crosswalk_out.csv",
            usecols=cols + ['deaths_adjusted', 'deaths']
        )
        df = df.groupby(cols, as_index=False)[['deaths', 'deaths_adjusted']].sum()
        df = df.rename(columns={
            'deaths_adjusted': 'deaths_adjusted_' + mv, 'deaths': 'deaths_' + mv
        })
        scatter = scatter.merge(df, how='outer', validate='one_to_one')
    report_duplicates(scatter, cols)
    scatter.to_csv(OUT_DIR / "sens_analysis_scatter_models.csv", index=False)
    return results, scatter


def lin_ccc(x, y):
    variance = np.diagonal(np.cov(x, y))
    covariance = np.diagonal(np.cov(x, y), offset=1)
    ccc = 2 * covariance / ((np.mean(x) - np.mean(y))**2 + variance[0] + variance[1])
    return ccc


if __name__ == '__main__':
    results, scatter = get_results()
    for mv in [
        '2021_04_20_pct_firearm_only_drop_re',
        '2021_04_22_no_cov',
        '2021_04_22_drop_fe_2005_2012'
    ]:
        base_col = 'deaths_adjusted_2021_04_19_pct_firearm_only'
        compare_col = 'deaths_adjusted_' + mv
        temp_df = scatter.loc[
            scatter[base_col].notnull() & scatter[compare_col].notnull()
        ]
        print(mv)
        cc = lin_ccc(temp_df[base_col], temp_df[compare_col])
        print('{0:.16f}'.format(cc[0]))
    df = scatter.loc[scatter.sub_source == 'NVSS']
    df = df.groupby(['year_id'])[
        ['deaths_adjusted_2021_04_22_drop_fe_2005_2012',
         'deaths_adjusted_2021_04_19_pct_firearm_only']
    ].sum()
    df.columns = ['drop', 'keep']
    print((df['drop'] - df['keep']).mean())
