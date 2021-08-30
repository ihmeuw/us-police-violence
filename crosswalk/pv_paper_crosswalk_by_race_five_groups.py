"""
Purpose: Crosswalk US police violence data with race/ethnicity
    detail at the national level.
"""
import sys
import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from getpass import getuser
from cod_prep.claude.configurator import Configurator
from cod_prep.claude.claude_io import get_claude_data
from cod_prep.utils import report_if_merge_fail, create_square_df, cod_timestamp
from race_location_utils import (
    get_re_args, get_re_loc_id, get_state_re, get_re_map,
    redistribute_re, calculate_pct_firearm
)
from cod_prep.downloaders import (
    get_current_location_hierarchy, add_pop_group_metadata,
    add_location_metadata, get_cod_ages, add_code_metadata,
    add_nid_metadata
)
sys.path.append("FILEPATH")
from format_sub_sources import format_sub_sources
from crosswalk import run_crosswalk, age_sex_split_data

CONF = Configurator()
WORKING_DIR = Path("FILEPATH")
MATCHES_FILE = "crosswalk_in.csv"
DATA_FILE = "data_orig.csv"
ADJUSTED_FILE = "crosswalk_out.csv"
WRITE = True


def get_data():
    """
    Data prep function for this crosswalk.
    """
    df = format_sub_sources(['MPV', 'Fatal_Encounters', 'The_Counted'])

    df = df.query("sub_source != 'Fatal_Encounters' | year_id >= 2005")
    drop_fe_causes = [
        'Vehicle',
        'Drug overdose',
        'Undetermined',
        'Medical emergency',
        'Other',
        'Unknown'
    ]
    df = df.loc[(df.sub_source != 'Fatal_Encounters') | ~df.int_cause.isin(drop_fe_causes)]

    re_map = get_re_map('pv_five_groups')
    df['population_group_name'] = df['race'].map(re_map)
    report_if_merge_fail(df, 'population_group_name', 'race')
    df = add_pop_group_metadata(df, 'population_group_id', merge_col='population_group_name')
    df['population_group_id'] = df['population_group_id'].fillna(999)

    df['location_id'] = 102
    df = df.groupby(
        ['sub_source', 'year_id', 'location_id', 'population_group_id', 'age_group_id', 'sex_id'],
        as_index=False)['deaths'].sum()

    df = redistribute_re(
        df, by=['sub_source', 'location_id', 'year_id'], allow_fail=True)
    df = redistribute_re(
        df, by=['sub_source', 'location_id'], allow_fail=False)
    assert df.notnull().values.all()

    nvss = get_claude_data('disaggregation', data_type_id=9, extract_type_id=1892)
    nvss = nvss.loc[nvss.cause_id == 854]
    nvss = pd.concat([
        add_code_metadata(group, 'value', code_system_id=csid)
        for csid, group in add_nid_metadata(nvss, 'code_system_id').groupby('code_system_id')
    ])
    nvss = nvss.loc[~(
        ((nvss.year_id <= 1998) & nvss.value.str.startswith("E978")) |
        ((nvss.year_id > 1998) & nvss.value.str.startswith("Y35.5"))
    )]
    nvss.loc[nvss.population_group_id == 7, 'population_group_id'] = 3

    nvss['location_id'] = 102
    pct = calculate_pct_firearm(nvss, by=['year_id', 'location_id', 'population_group_id'])

    nvss = nvss.groupby(
        ['location_id', 'population_group_id', 'year_id', 'age_group_id', 'sex_id'], as_index=False
    )['deaths'].sum()

    df = df.append(nvss.assign(sub_source='NVSS'))
    assert df.notnull().values.all()
    df = df.groupby(
        ['sub_source', 'location_id', 'population_group_id', 'year_id', 'age_group_id', 'sex_id'],
        as_index=False
    )['deaths'].sum()

    df = df.loc[df.year_id >= 1990]
    return df, pct


def main(model_version, impose_priors, add_covariates=None, read_cache=False):
    add_covariates = add_covariates or []
    working_dir = WORKING_DIR / model_version
    working_dir.mkdir(exist_ok=True)
    print("Getting data")
    if not read_cache:
        df, pct = get_data()
        df.to_csv("FILEPATH", index=False)
        pct.to_csv("FILEPATH", index=False)
    else:
        print("Reading cache")
        df = pd.read_csv("FILEPATH")

    df = run_crosswalk(
        working_dir=working_dir,
        matches_file=MATCHES_FILE,
        data_file=DATA_FILE,
        adjusted_file=ADJUSTED_FILE,
        df=df,
        matches_data_options={
            'age_sex_split': False,
            'aggregate': {'age_group_id': 22, 'sex_id': 3},
            'square_and_offset': False,
            'calculate_rates': True
        },
        ref='The_Counted',
        alts=['MPV', 'NVSS', 'Fatal_Encounters'],
        case_def='sub_source',
        match_cols=[
            'location_id', 'year_id',
            'age_group_id', 'sex_id',
            'population_group_id'
        ],
        adjustment_data_options={
            'age_sex_split': False,
            'aggregate': {'age_group_id': 22, 'sex_id': 3},
            'square_and_offset': False,
            'calculate_rates': True
        },
        encode_cols=['population_group_id'],
        cov_cols=['population_group_id'] + add_covariates,
        order_prior=[],
        adjust_col='rate',
        model_col='rate',
        impose_priors=impose_priors
    )

    df.to_csv(WORKING_DIR / ADJUSTED_FILE, index=False)
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch crosswalk for 5 race groups')
    parser.add_argument('model_version', type=str)
    parser.add_argument('impose_priors', type=bool)
    parser.add_argument('--add_covariates', nargs="*", type=str)
    parser.add_argument('--read_cache', action='store_true')
    args = parser.parse_args()
    main(**vars(args))
