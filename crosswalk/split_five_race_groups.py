"""
Script that takes the four-race group ST-GPR model result and splits it into
the 5 race groups at the national level.
"""
import pandas as pd
from cod_prep.downloaders import add_pop_group_metadata
from cod_prep.utils.misc import report_if_merge_fail

ST_GPR_RUN_ID = "190430_fixed_clip"
ST_GPR_BASE_DIR = "FILEPATH"
CW_VERSION = "2021_04_09_no_pct_firearm"
CW_BASE_DIR = "FILEPATH"


def split_st_gpr_model():
    df = pd.read_csv("FILEPATH")
    df = df.loc[(df.location_id == 102) & (df.race != 'all races') & (df.year_id >= 1990)]
    df['race'] = df['race'].str.strip()

    wgt = pd.read_csv("FILEPATH")
    wgt = wgt.loc[wgt.population_group_id.isin([3, 6])]
    wgt = wgt.groupby(['year_id', 'population_group_id'], as_index=False)[
        ['deaths_adjusted', 'population']].sum()
    wgt['prop_deaths'] = wgt['deaths_adjusted'] / wgt.groupby(
        ['year_id'])['deaths_adjusted'].transform(sum)
    wgt['prop_pop'] = wgt['population'] / wgt.groupby(
        ['year_id'])['population'].transform(sum)
    wgt = add_pop_group_metadata(wgt, 'population_group_name')
    assert wgt['population_group_name'].notnull().all()
    wgt['new_race'] = wgt['population_group_name']
    wgt['race'] = 'Non-Hispanic, Other races'
    wgt = wgt[['year_id', 'race', 'new_race', 'prop_deaths', 'prop_pop']]

    draws = [c for c in df if 'draw' in c]
    no_split = df.query("race != 'Non-Hispanic, Other races'")
    split = df.query("race == 'Non-Hispanic, Other races'")
    split = split.merge(wgt, how='left', on=['year_id', 'race'])
    report_if_merge_fail(split, 'new_race', 'year_id')
    split = split.reset_index(drop=True)

    split[draws] = pd.DataFrame(
        split[draws].to_numpy() * split[['prop_deaths']].to_numpy(),
        index=split.index
    )
    split['population'] = split['population'] * split['prop_pop']
    split['race'] = split['new_race']
    df = pd.concat([split, no_split], sort=False)

    keep_cols = [
        'age_group_id',
        'sex_id',
        'location_id',
        'year_id',
        'race',
        'population',
        'age_weight'
    ]
    df = df[keep_cols + draws]
    df.to_csv("FILEPATH", index=False)
    return df


def aggregate_for_plot(df):
    draws = [c for c in df if 'draw' in c]

    age_weights = df[['age_group_id', 'age_weight']].drop_duplicates()

    df['year_bin'] = pd.cut(
        df['year_id'], bins=list(range(1980, 2021, 5)),
        right=False, include_lowest=True,
        labels=[f"{i}-{i+4}" for i in list(range(1980, 2020, 5))]
    )
    df = df.groupby(
        ['year_bin', 'race', 'age_group_id'], as_index=False)[draws + ['population']].sum()

    df = df.reset_index(drop=True)

    df = df.merge(age_weights, how='left')
    report_if_merge_fail(df, 'age_weight', 'age_group_id')
    df[draws] = pd.DataFrame(
        df[draws].to_numpy() / df[['population']].to_numpy() * df[['age_weight']].to_numpy(),
        index=df.index
    )
    df = df.groupby(['year_bin', 'race'], as_index=False)[draws + ['population']].sum()

    df['rate'] = df[draws].mean(axis=1)
    df['rate_upper'] = df[draws].quantile(0.975, axis=1)
    df['rate_lower'] = df[draws].quantile(0.025, axis=1)
    df = df.drop(draws, axis='columns')

    for col in ['rate', 'rate_lower', 'rate_upper']:
        df[col + '_per_100k'] = df[col] * 100_000

    df.loc[df.race == 'Non-Hispanic, American Indian, Alaskan Native', 'race'] =\
        'Non-Hispanic, Indigenous'
    df['rate'] = (
        df['rate_per_100k'].round(decimals=2).astype(str).str.ljust(4, fillchar='0') + ' (' +
        df['rate_lower_per_100k'].round(decimals=2).astype(str).str.ljust(4, fillchar='0') + ' - ' +
        df['rate_upper_per_100k'].round(decimals=2).astype(str).str.ljust(4, fillchar='0') + ')'
    )
    df[['year_bin', 'race', 'rate', 'rate_per_100k']].to_csv(
        "FILEPATH",
        index=False
    )
    df = pd.pivot_table(
        df, columns='race', index='year_bin',
        values=['rate', 'rate_per_100k'], aggfunc=lambda x: x)
    df.to_excel("FILEPATH")


if __name__ == '__main__':
    df = split_st_gpr_model()
    aggregate_for_plot(df)
