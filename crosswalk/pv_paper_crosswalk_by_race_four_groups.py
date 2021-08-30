"""
Purpose: Crosswalk US police violence data with race/state detail.
"""
import sys
import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from getpass import getuser
from cod_prep.claude.configurator import Configurator
from cod_prep.claude.claude_io import get_claude_data
from cod_prep.utils import report_if_merge_fail
from cod_prep.downloaders import add_code_metadata, add_nid_metadata
from race_location_utils import (
    get_re_args, get_re_loc_id, get_state_re, get_re_map, redistribute_re,
    calculate_pct_firearm
)
from cod_prep.downloaders import get_current_location_hierarchy
sys.path.append("FILEPATH")
from format_sub_sources import format_sub_sources
from crosswalk import run_crosswalk, age_sex_split_data
from cod_prep.utils import create_square_df

CONF = Configurator()
WORKING_DIR = Path("FILEPATH")
MATCHES_FILE = "crosswalk_in.csv"
DATA_FILE = "data_orig.csv"
ADJUSTED_FILE = "crosswalk_out.csv"
LOCATION_SET_ID = 105
LOCATION_SET_VERSION_ID = 608
POP_RUN_ID = 233
DECOMP_STEP = 'usa_re'
GBD_ROUND_ID = 7


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

    re_map = get_re_map('four_groups')
    df['re'] = df['race'].map(re_map)
    report_if_merge_fail(df, 're', 'race')

    df = df.groupby(
        ['sub_source', 'year_id', 'location_id', 're', 'age_group_id', 'sex_id'],
        as_index=False)['deaths'].sum()

    start_deaths = df.deaths.sum()
    df = redistribute_re(
        df, by=['sub_source', 'location_id', 'year_id'],
        re_col='re', unknown_re='Unknown race or ethnicity',
        allow_fail=True)
    df = redistribute_re(
        df, by=['sub_source', 'location_id'],
        re_col='re', unknown_re='Unknown race or ethnicity',
        allow_fail=False)
    assert df.notnull().values.all()
    assert np.isclose(df.deaths.sum(), start_deaths)

    df['state_id'] = df['location_id']
    df['location_id'] = get_re_loc_id(df['state_id'], df['re'])
    report_if_merge_fail(df, 'location_id', ['state_id', 're'])

    nvss = get_claude_data(
        'disaggregation', extract_type_id=1889,
        year_id=list(range(1980, 2020)), data_type_id=9,
        force_rerun=True, block_rerun=False,
        launch_set_id=10541
    )
    nvss = nvss.loc[nvss.cause_id == 854]
    nvss = pd.concat([
        add_code_metadata(group, 'value', code_system_id=csid)
        for csid, group in add_nid_metadata(nvss, 'code_system_id').groupby('code_system_id')
    ])
    nvss = nvss.loc[~(
        ((nvss.year_id <= 1998) & nvss.value.str.startswith("E978")) |
        ((nvss.year_id > 1998) & nvss.value.str.startswith("Y35.5"))
    )]
    pct = calculate_pct_firearm(nvss, by=['year_id', 'location_id'])
    nvss = nvss.groupby(
        ['location_id', 'year_id', 'age_group_id', 'sex_id'], as_index=False
    )['deaths'].sum()
    state_id, re = get_state_re(nvss['location_id'])
    assert state_id.notnull().all()
    assert re.notnull().all()
    nvss['state_id'] = state_id
    nvss['re'] = re
    df = df.append(nvss.assign(sub_source='NVSS'))
    assert df.notnull().values.all()
    df = df.groupby(
        ['sub_source', 'location_id', 'year_id', 're', 'state_id', 'age_group_id', 'sex_id'],
        as_index=False
    )['deaths'].sum()
    return df, pct


def split_offset(df, offset_value, split_across, split_within):
    """
    Split an offset of a given value across the split_across columns
    with the split_within columns using the distribution of
    the data in df.
    """
    df = age_sex_split_data(
        df, pop_run_id=POP_RUN_ID, location_set_id=LOCATION_SET_ID,
        location_set_version_id=LOCATION_SET_VERSION_ID
    )
    sq_df = create_square_df(df, split_across + split_within)
    df = df.groupby(split_across + split_within, as_index=False)['deaths'].sum().merge(
        sq_df, how='right', on=split_across + split_within, validate='one_to_one'
    ).fillna({'deaths': 0})
    if split_within == []:
        df['offset'] = df['deaths'] / df.deaths.sum() * offset_value
    else:
        df['offset'] = df['deaths'] / df.groupby(split_within).deaths.transform(sum) * offset_value
    df = df.drop('deaths', axis='columns')
    return df


def get_offsets(df):
    """
    Determine how to offset data points.
    """
    matches_offset = split_offset(df, 1, ['re'], ['state_id'])

    adjustment_offset = split_offset(df, 1, ['age_group_id', 'sex_id'], [])
    adjustment_offset = adjustment_offset.assign(merge=1).merge(
        matches_offset.assign(merge=1), on='merge'
    ).assign(
        offset=lambda d: d['offset_x'] * d['offset_y']
    ).drop(['merge', 'offset_x', 'offset_y'], axis='columns')
    return matches_offset, adjustment_offset


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
    matches_offset, adjustment_offset = get_offsets(df)
    df = run_crosswalk(
        working_dir=working_dir,
        matches_file=MATCHES_FILE,
        data_file=DATA_FILE,
        adjusted_file=ADJUSTED_FILE,
        gbd_round_id=GBD_ROUND_ID,
        decomp_step=DECOMP_STEP,
        df=df,
        matches_data_options={
            'age_sex_split': False,
            'aggregate': {'age_group_id': 22, 'sex_id': 3},
            'square_and_offset': True,
            'square_cols': ['age_group_id', 'sex_id', 're', 'state_id'],
            'within_cols': ['sub_source', 'year_id'],
            'offset': matches_offset,
            'calculate_rates': True,
            'pop_run_id': POP_RUN_ID,
            'location_set_id': LOCATION_SET_ID,
            'location_set_version_id': LOCATION_SET_VERSION_ID,
        },
        ref='The_Counted',
        alts=['MPV', 'NVSS', 'Fatal_Encounters'],
        case_def='sub_source',
        match_cols=[
            'location_id', 'year_id',
            'age_group_id', 'sex_id',
            'state_id', 're'
        ],
        adjustment_data_options={
            'age_sex_split': True,
            'aggregate': None,
            'square_and_offset': True,
            'square_cols': ['age_group_id', 'sex_id', 're', 'state_id'],
            'within_cols': ['sub_source', 'year_id'],
            'offset': adjustment_offset,
            'calculate_rates': True,
            'pop_run_id': POP_RUN_ID,
            'location_set_id': LOCATION_SET_ID,
            'location_set_version_id': LOCATION_SET_VERSION_ID,
        },
        encode_cols=['state_id', 're'],
        cov_cols=['state_id', 're'] + add_covariates,
        order_prior=[],
        adjust_col='rate',
        model_col='rate',
        impose_priors=impose_priors
    )

    lh = get_current_location_hierarchy(
        location_set_id=LOCATION_SET_ID,
        location_set_version_id=LOCATION_SET_VERSION_ID
    ).set_index('location_id')['location_name'].to_dict()
    df['state'] = df['state_id'].map(lh)

    df = df.to_csv(working_dir / ADJUSTED_FILE, index=False)
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch crosswalk for 4 race groups')
    parser.add_argument('model_version', type=str)
    parser.add_argument('impose_priors', type=bool)
    parser.add_argument('--add_covariates', nargs="*", type=str)
    parser.add_argument('--read_cache', action='store_true')
    args = parser.parse_args()
    main(**vars(args))
