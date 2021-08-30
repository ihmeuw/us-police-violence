"""
Format data on incarcerated populations from the Bureau of Justice Statistics.

Referenced this report heavily as well as the codebooks:
https://www.bjs.gov/index.cfm?ty=pbdetail&iid=7026
"""
import pandas as pd
import sys
import numpy as np
from pathlib import Path
from getpass import getuser
sys.path.append("FILEPATH")
from us_police_conflict_utils import (
    get_location_id_from_us_state_codes, get_location_id_from_state
)
from race_location_utils import redistribute_re, get_re_map, get_re_loc_id
from cod_prep.claude.configurator import Configurator
from cod_prep.utils.misc import report_if_merge_fail, report_duplicates
from cod_prep.downloaders import add_population
from mcod_prep.utils.covariates import merge_covariate

IN_DIR = Path("FILEPATH")
WORKING_DIR = Path("FILEPATH")
ID_COLS = ['location_id', 'age_group_id', 'sex_id', 'year_id', 'jurisdiction', 'race']
VALUE_COL = 'prisoners'
INT_COLS = [col for col in ID_COLS if 'id' in col]
FINAL_COLS = ID_COLS + [VALUE_COL]
CONF = Configurator()


def collapse(df):
    df = df[FINAL_COLS]
    df[INT_COLS] = df[INT_COLS].astype(int)
    df[VALUE_COL] = df[VALUE_COL].astype(float)
    df = df.groupby(ID_COLS, as_index=False)[VALUE_COL].sum()
    assert df.notnull().values.all()
    return df


def initial_NPS_clean(long_cols, pop_cols, melt_var_name):
    df = pd.read_stata("FILEPATH")
    df = df.rename(columns=lambda x: x.lower())

    # Year
    df['year_id'] = df['year']
    df = df.loc[df.year.between(1980, 2018)]

    # Location
    df = df.loc[~df.state.isin(['ST', 'US'])]
    df = get_location_id_from_us_state_codes(df, 'state', fill=True)
    assert (df.loc[df.location_id == 102, 'state'] == 'FE').all()

    # Map jurisdiction
    df.loc[df.state == 'FE', 'jurisdiction'] = 'federal'
    df.loc[df.state != 'FE', 'jurisdiction'] = 'state'

    pop_cols = [col + 'm' for col in pop_cols] + [col + 'f' for col in pop_cols]
    df = df.melt(
        id_vars=long_cols, value_vars=pop_cols, var_name=melt_var_name,
        value_name='prisoners'
    )
    df.loc[
        ~df.prisoners.astype(str).str.isnumeric(), 'prisoners'
    ] = 0
    df['prisoners'] = df['prisoners'].astype(int)

    # Sex
    df['sex_id'] = df[melt_var_name].str[-1:].map({'m': 1, 'f': 2})
    assert df.sex_id.isin([1, 2, 9]).all()
    df[melt_var_name] = df[melt_var_name].str[:-1]
    return df


def format_NPS():
    """
    Format data from the National Prisoner Statistics data collecion effort.
    """
    long_cols = ['location_id', 'year_id', 'jurisdiction']
    pop_cols = [
        'white', 'black', 'hisp', 'aian', 'asian', 'nhpi', 'api',
        'tworace', 'addrace', 'unkrace'
    ]
    df = initial_NPS_clean(long_cols, pop_cols, 'race')

    # Age
    df['age_group_id'] = 22

    # Race
    assert not df.groupby(['location_id', 'year_id', 'age_group_id', 'sex_id']).apply(
        lambda x:
            (x.loc[x.race == 'api', 'prisoners'].sum() != 0) and
            (x.loc[x.race.isin(['asian', 'nhpi']), 'prisoners'].sum() != 0)
    ).any()
    return collapse(df)


def format_NPS_local():
    """
    Format NPS including only prisoners held in local jails.
    """
    long_cols = ['location_id', 'year_id', 'jurisdiction']
    pop_cols = ['lf', 'lfcrowd']
    df = initial_NPS_clean(long_cols, pop_cols, 'facility')

    df['age_group_id'] = 22
    df = pd.pivot_table(
        df, index=long_cols + ['age_group_id', 'sex_id'], columns='facility',
        values='prisoners'
    ).reset_index()
    df.loc[df.lf == 0, 'lf'] = df['lfcrowd']
    df['prisoners'] = df['lf']
    df = df.drop(['lf', 'lfcrowd'], axis='columns')
    df['race'] = 'Unknown'
    return collapse(df)


def format_NJC():
    """
    Format data from the National Jail Censuses.
    """
    file_path = "FILEPATH"
    df = pd.read_stata(file_path)
    df = df.rename(columns=lambda x: x.lower())
    long_cols = ['facid', 'year']
    pop_cols = [
        'white', 'black', 'hisp', 'aian', 'asian', 'nhopi',
        'tworace', 'otherrace', 'racedk'
    ]
    df = df.melt(
        id_vars=long_cols, value_vars=pop_cols, var_name='race',
        value_name='prisoners'
    )

    # Year
    df['year_id'] = df['year']

    # Location
    facid_map = pd.read_csv("FILEPATH")
    facid_map = facid_map.facid.str.split(" ", n=1, expand=True).set_index(0)[1].to_dict()
    df['state'] = df['facid'].str[0:2].map(facid_map)
    report_if_merge_fail(df, 'state', 'facid')
    df = get_location_id_from_state(df, 'state')

    # Remaining columns
    df['age_group_id'] = 22
    df['sex_id'] = 3
    df['jurisdiction'] = 'local'
    return collapse(df)


def format_incarcerated():
    """
    Get data on the total incarcerated population.

    BJS definition of incarcerated populations: "estimated number of prisoners
    under the jurisdiction of state or federal prisons and inmates in the custody
    of local jails." Effectively NPS + NJC minus any double-counting for
    prisoners in local jails.
    """
    prison = format_NPS()
    prison_local = format_NPS_local()
    start_val = prison.prisoners.sum()
    merge_cols = ['location_id', 'age_group_id', 'sex_id', 'year_id', 'jurisdiction']
    prison = prison.merge(
        prison_local[merge_cols + ['prisoners']], how='left',
        on=merge_cols, suffixes=('', '_local'), validate='many_to_one')
    prison['prisoners_local'] = prison['prisoners_local'].fillna(0)
    prison['fraction'] = (prison['prisoners'] / prison.groupby(
        merge_cols)['prisoners'].transform(sum)).fillna(0)
    prison['prisoners'] = prison['prisoners'] - prison['prisoners_local'] * prison['fraction']
    assert np.isclose(
        start_val - prison_local['prisoners'].sum(),
        prison['prisoners'].sum()
    )
    assert (prison['prisoners'] >= 0).all()

    jail = format_NJC()
    df = pd.concat([prison, jail], sort=False)
    df = df.loc[df.year_id.isin(set(jail.year_id).intersection(set(prison.year_id)))]
    return collapse(df)


def scatter_incarceration_police_violence(scatter_type):
    if scatter_type == 'state_and_local':
        incar = format_incarcerated()
    elif scatter_type == 'state':
        incar = format_NPS()
    incar = incar[incar.jurisdiction != 'federal']
    re_map = get_re_map('four_groups')
    incar['re'] = incar['race'].map(re_map)
    report_if_merge_fail(incar, 're', 'race')
    incar = redistribute_re(
        incar, by=['location_id', 'year_id'], re_col='re',
        unknown_re='Unknown race or ethnicity', value_col='prisoners',
        allow_fail=True
    )
    incar = redistribute_re(
        incar, by=['location_id'], re_col='re',
        unknown_re='Unknown race or ethnicity', value_col='prisoners',
        allow_fail=False
    )
    incar['state_id'] = incar['location_id']
    incar['location_id'] = get_re_loc_id(incar['state_id'], incar['re'])
    incar = incar.groupby(
        ['location_id', 'year_id', 're', 'state_id'], as_index=False)['prisoners'].sum()\
        .assign(age_group_id=22, sex_id=3)
    incar = add_population(
        incar, force_rerun=False, block_rerun=True, pop_run_id=CONF.get_id("pop_run"))
    report_if_merge_fail(incar, 'population', 'location_id')
    incar['rate'] = incar['prisoners'] / incar['population'] * 100_000

    pv = pd.read_csv("FILEPATH")
    pv = pv.loc[pv.gpr_mean.notnull()]
    pv['location_id'] = pv['location_id_x']
    pv = add_population(
        pv, force_rerun=False, block_rerun=True, pop_run_id=CONF.get_id("pop_run"))
    report_if_merge_fail(pv, 'population', 'location_id')
    pv['rate'] = pv['gpr_mean'] / pv['population'] * 100_000

    df = pd.merge(
        incar, pv, how='inner',
        on=['location_id', 'year_id', 'age_group_id', 'sex_id'],
        suffixes=('_incarceration', '_police_violence'),
        validate='one_to_one'
    )
    df = merge_covariate(df, 'ldi_pc_re', decomp_step='usa_re')
    return df


if __name__ == '__main__':
    assert CONF.config_type == 'race_ethnicity'
    df = scatter_incarceration_police_violence('state_and_local')
    df.to_csv("FILEPATH", index=False)
    df = scatter_incarceration_police_violence('state')
    df.to_csv("FILEPATH", index=False)
