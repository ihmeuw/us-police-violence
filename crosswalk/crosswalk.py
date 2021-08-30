"""
Prep US police violence data for crosswalks.
"""
import subprocess
import pandas as pd
import numpy as np
import itertools
import sys
from getpass import getuser
from cod_prep.claude.configurator import Configurator
from cod_prep.claude.age_sex_split import AgeSexSplitter
from cod_prep.downloaders import (
    get_current_location_hierarchy, add_population, pretty_print,
    add_location_metadata
)
from cod_prep.utils import (
    print_log_message, create_square_df, report_if_merge_fail,
    wrap, report_duplicates
)
from mcod_prep.utils.covariates import merge_covariate, get_cov
from race_location_utils import get_re_loc_id, get_state_re
CONF = Configurator()


def age_sex_split_data(df, pop_run_id=None, location_set_id=None,
                       location_set_version_id=None):
    """
    Apply age/sex splitting.

    Within-study age/sex splitting is recommended before crosswalking.
    Apply CoD age/sex splitting algorithm, which relies on the
    age/sex pattern of mortality rate by cause.
    """
    start_deaths = df.deaths.sum()
    no_cause = 'cause_id' not in df.columns
    if no_cause:
        df = df.assign(cause_id=854)
    if location_set_version_id is None:
        location_set_version_id = CONF.get_id('location_set_version')
    if location_set_id is None:
        location_set_id = CONF.get_id("location_set")
    location_meta_df = get_current_location_hierarchy(
        location_set_id=location_set_id,
        location_set_version_id=location_set_version_id
    )
    if pop_run_id is None:
        pop_run_id = CONF.get_id("pop_run")
    column_metadata = {
        col: {'col_type': 'demographic'} for col in
        df if col not in ['deaths', 'cause_id']
    }
    MySplitter = AgeSexSplitter(
        CONF.get_id('cause_set_version'),
        pop_run_id,
        CONF.get_id('distribution_set_version'),
        location_set_id=location_set_id
    )
    df = MySplitter.get_computed_dataframe(
        df, location_meta_df, column_metadata=column_metadata)
    assert np.isclose(start_deaths, df.deaths.sum())
    if no_cause:
        df = df.drop('cause_id', axis='columns')
    return df


def square_and_offset_data(df, square_cols, within_cols, offset=0):
    """
    Square the data and apply an offset to make everything nonzero.

    Arguments:
      df (pd.DataFrame): dataframe to square
      square_cols (list of strings): column names to square
      within_cols (list of strings): column whose unique
        combinations to preserve
    """
    start_deaths = df.deaths.sum()
    sq_df = create_square_df(
        df, square_cols
    )
    if 're' in square_cols and 'state_id' in square_cols:
        assert 'location_id' not in square_cols, "Can't square race/state/location_id"
        assert 'location_id' not in within_cols
        sq_df['location_id'] = get_re_loc_id(sq_df['state_id'], sq_df['re'])
    sq_df = pd.merge(
        sq_df.assign(merge=1),
        df[within_cols].drop_duplicates().assign(merge=1),
        on='merge')\
        .drop('merge', axis='columns')

    df = df.merge(sq_df, how='right', validate='one_to_one')\
        .fillna({'deaths': 0})
    if isinstance(offset, str) and offset == 'one_tenth_min':
        df['deaths'] = df['deaths'] + df.loc[df.deaths != 0, 'deaths'].min() / 10
    elif isinstance(offset, pd.DataFrame):
        merge_cols = list(set(offset) - {'offset'})
        df = df.merge(offset, how='left', on=merge_cols, validate='many_to_one')
        report_if_merge_fail(df, 'offset', merge_cols)
        df['deaths'] = df['deaths'] + df['offset']
    else:
        df['deaths'] = df['deaths'] + offset
    print_log_message(f"START DEATHS {start_deaths}")
    print_log_message(f"END DEATHS {df.deaths.sum()}")
    return df


def aggregate_data(df, aggregate):
    """
    Aggregate certain demographic columns.

    Arguments:
       df (pd.DataFrame, required): dataframe of deaths to aggregate
       aggregate(dict, required): dictionary of <column to aggregate: value to assign>
    """
    dem_cols = list(set(df.columns) - {'deaths'})
    keep_cols = list(set(dem_cols) - set(aggregate.keys()))
    df = df.groupby(keep_cols, as_index=False)['deaths'].sum()
    df = df.assign(**aggregate)
    return df


def get_rates(df, pop_run_id=None, location_set_id=None):
    """
    Convert deaths to rates.
    """
    if pop_run_id is None:
        pop_run_id = CONF.get_id('pop_run')
    if location_set_id is None:
        location_set_id = CONF.get_id('location_set')
    if 'population_group_id' not in df:
        df = add_population(
            df, pop_run_id=pop_run_id, location_set_id=location_set_id,
            force_rerun=False, block_rerun=True, cache_results=False)
    else:
        pop_df = pd.read_csv("FILEPATH")
        df = add_population(
            df, merge_cols=[
                'location_id', 'year_id', 'age_group_id',
                'sex_id', 'population_group_id'
            ], pop_df=pop_df
        )
    report_if_merge_fail(
        df, 'population', ['location_id', 'year_id', 'age_group_id', 'sex_id'])
    df['rate'] = df['deaths'] / df['population']
    return df


def get_se(df):
    """
    Calculate standard errors of the observations.

    Here we use the standard error of the mean of a Bernoulli distribution
    """
    df['se'] = np.sqrt(df['rate'] * (1 - df['rate']) / df['population'])
    return df


def get_matches(df, ref, alts, case_def,
                match_cols=['location_id', 'year_id', 'age_group_id', 'sex_id']):
    """
    Match observations for the crosswalk
    """
    df = df.query("deaths > 0")
    matches = []
    for alt in alts:
        match = df.query(f"{case_def} == '{ref}'").merge(
            df.query(f"{case_def} == '{alt}'"),
            on=match_cols, validate='one_to_one'
        )
        matches.append(match)

    for combo in list(itertools.combinations(alts, 2)):
        match = df.query(f"{case_def} == '{combo[0]}'").merge(
            df.query(f"{case_def} == '{combo[1]}'"),
            on=match_cols, validate='one_to_one'
        )
        matches.append(match)
    return pd.concat(matches, sort=True)


def prep_data(df, pop_run_id=None, location_set_id=None, location_set_version_id=None,
              age_sex_split=True, square_and_offset=False, square_cols=None,
              within_cols=None, offset=None, aggregate=None, calculate_rates=True):
    """Function that preps data with options"""
    assert (df.deaths > 0).all(),\
        "The code makes the assumption that all records "\
        "going into the algorithm have non-zero deaths"
    if age_sex_split:
        print_log_message("Age/sex splitting")
        df = age_sex_split_data(
            df, pop_run_id=pop_run_id, location_set_id=location_set_id,
            location_set_version_id=location_set_version_id
        )
    if aggregate is not None:
        print_log_message("Aggregating...")
        df = aggregate_data(df, aggregate)
    if square_and_offset:
        print_log_message("Squaring & offsetting")
        assert square_cols is not None
        assert within_cols is not None
        assert offset is not None
        df = square_and_offset_data(df, square_cols, within_cols, offset=offset)
    if calculate_rates:
        print_log_message("Getting rates & SE")
        df = get_rates(
            df, pop_run_id=pop_run_id,
            location_set_id=location_set_id)
        df = get_se(df)
    if 'se' not in df.columns:
        print_log_message("You said not to calculate rates, filling in SE...")
        df['se'] = 1
    return df


def merge_covariates(df, cov_cols, working_dir, location_set_id=None,
                     gbd_round_id=None, decomp_step=None):
    for cov in [c for c in cov_cols if c not in df]:
        if cov == 'pct_firearm':
            pct = pd.read_csv(working_dir / "pct_firearm.csv")
            df = df.merge(
                pct, how='left', on=[c for c in pct if c != 'pct_firearm'],
                validate='many_to_one'
            )
            df['pct_firearm'] = df['pct_firearm'].fillna(0)
        elif cov in ['ldi_pc_black', 'ldi_pc_lowest']:
            ldi = get_cov(
                covariate_id=2007, location_set_id=location_set_id,
                gbd_round_id=gbd_round_id, decomp_step=decomp_step,
                force_rerun=False, block_rerun=True
            )
            ldi = add_location_metadata(
                ldi, 'most_detailed',
                location_set_version_id=CONF.get_id("location_set_version")
            )
            ldi = ldi.loc[ldi.most_detailed == 1]
            state_id, re = get_state_re(ldi['location_id'])
            ldi['state_id'] = state_id
            ldi['re'] = re
            if cov == 'ldi_pc_black':
                ldi = ldi.loc[ldi.re.str.contains("Black")]
            elif cov == 'ldi_pc_lowest':
                ldi = ldi.groupby(['year_id', 'state_id'], as_index=False)['mean_value'].min()
            ldi = ldi[
                ['year_id', 'state_id', 'mean_value']
            ].drop_duplicates()
            ldi[cov] = np.log(ldi['mean_value'])
            df = df.merge(
                ldi[['year_id', 'state_id', cov]], how='left', on=['year_id', 'state_id'],
                validate='many_to_one'
            )
        elif cov == 'LDI_pc':
            ldi = get_cov(
                covariate_id=57, location_set_id=35,
                gbd_round_id=gbd_round_id, decomp_step='iterative',
                force_rerun=False, block_rerun=True
            )
            if 'state_id' in df:
                ldi['state_id'] = ldi['location_id']
                merge_cols = ['year_id', 'state_id']
            else:
                merge_cols = ['year_id', 'location_id']
            ldi[cov] = np.log(ldi['mean_value'])
            df = df.merge(
                ldi[merge_cols + [cov]], how='left', on=merge_cols,
                validate='many_to_one'
            )
        else:
            df = merge_covariate(
                df, cov, location_set_id=location_set_id,
                gbd_round_id=gbd_round_id, decomp_step=decomp_step,
                force_rerun=False, block_rerun=True
            )
        assert df[cov].notnull().values.all()
    return df


def reset_offset(df, adjustment_data_options, adjust_col):
    """
    Reset the specified offset for the adjustment data.
    """
    adjustment_square_and_offset = adjustment_data_options.get('square_and_offset', False)
    adjustment_offset = adjustment_data_options.get('offset', 0)
    if adjust_col == 'rate':
        df['deaths_adjusted'] = df['rate_adjusted'] * df['population']
    if adjustment_square_and_offset:
        if 'offset' in df:
            df = df.drop('offset', axis='columns')
        if isinstance(adjustment_offset, pd.DataFrame):
            df = df.merge(adjustment_offset, how='left')
            report_if_merge_fail(
                df, 'offset',
                adjustment_offset.columns.drop('offset').tolist())
        else:
            df['offset'] = adjustment_offset
        df = df.assign(**{
            col: np.clip(df[col] - df['offset'], 0, None) for col in [
                'deaths', 'deaths_adjusted'
            ]
        })
    if adjust_col == 'rate':
        df['rate'] = df['deaths'] / df['population']
        df['rate_adjusted'] = df['deaths_adjusted'] / df['population']
    return df


def run_crosswalk(working_dir, matches_file, data_file, adjusted_file,
                  gbd_round_id, decomp_step, df, matches_data_options, ref, alts,
                  case_def, match_cols, adjustment_data_options,
                  encode_cols, cov_cols, order_prior, adjust_col,
                  model_col, impose_priors=False):
    """
    Run the crosswalk.

    Arguments:
        working_dir (PosixPath): directory to save intermediate files
        matches_file (str): file name for matches (ends with .csv)
        data_file (str): file name for data to be adjusted (ends with .csv)
        adjusted_file (str): file name for adjusted data (ends with .csv)
        df (pd.DataFrame): prepped data prior to any age/sex splitting,
            squaring, aggregation or rates/se calculation
        matches_data_options (dict): dictionary with options age_sex_split,
            square_and_offset, aggregate, and calculate_rates for matches
        ref (str): reference dorm
        alts (list of str): alternatives dorms
        case_def (str): column name with dorms listed
        match_cols (list of str): columns to match on
        adjustment_data_options (dict): dictionary with options age_sex_split,
            square_and_offset, aggregate, and calculate_rates for data
            for adjustment
        encode_cols (list of str): factor columns that need to be one-hot encoded
            for modelling
        cov_cols (list of str): columns to use as covariates
        order_prior (list of str): list of pairs of ordered dorms, where
            each pair is separated by a comma
        adjust_col (str): column to adjust at the end of the crosswalk
        model_col (str): column to use as the outcome variable in the CW model
        impose_priors (bool): impose special priors, default False
    """
    alts = wrap(alts)
    match_cols = wrap(match_cols)
    encode_cols = wrap(encode_cols)
    cov_cols = wrap(cov_cols)
    order_prior = wrap(order_prior)

    matches_path = working_dir / matches_file
    data_path = working_dir / data_file
    adjusted_path = working_dir / adjusted_file
    for path in [matches_path, data_path, adjusted_path]:
        if path.exists():
            path.unlink()

    if ('pct_firearm' in cov_cols) and not impose_priors:
        df = df.loc[~df.year_id.isin([2018, 2019])]

    print_log_message("Prepping data for matching")
    data_for_matches = prep_data(
        df, **matches_data_options
    )
    print_log_message("Matching data")
    matches = get_matches(
        data_for_matches, ref, alts, case_def, match_cols=match_cols)
    print_log_message("Merging covariates")
    matches = merge_covariates(
        matches, cov_cols, working_dir,
        location_set_id=matches_data_options['location_set_id'],
        gbd_round_id=gbd_round_id,
        decomp_step=decomp_step
    )
    print_log_message("Saving matches...")
    matches.to_csv(matches_path, index=False)

    print_log_message("Prepping data for adjustment")
    data_for_adjustment = prep_data(
        df, **adjustment_data_options
    )
    print_log_message("Merging covariates")
    data_for_adjustment = merge_covariates(
        data_for_adjustment, cov_cols, working_dir,
        location_set_id=adjustment_data_options['location_set_id'],
        gbd_round_id=gbd_round_id,
        decomp_step=decomp_step
    )
    data_for_adjustment = pretty_print(data_for_adjustment)
    print_log_message("Saving data for adjustment...")
    data_for_adjustment.to_csv(data_path, index=False)

    print_log_message("Running crosswalk!")
    cmd = [
        "FILEPATH",
        "-i FILEPATH",
        "-s", "FILEPATH",
        str(working_dir),
        matches_file,
        data_file,
        adjusted_file,
        "--match_cols"] + match_cols + [
        '--encode_cols'] + encode_cols + [
        '--cov_cols'] + cov_cols + [
        '--dorm_col',
        case_def,
        '--gold_dorm',
        ref,
        '--order_prior'] + order_prior + [
        '--adjust_col', adjust_col,
        '--model_col', model_col
    ]
    if impose_priors:
        cmd += ['--impose_priors']
    subprocess.call(cmd)

    print_log_message("Getting back the adjusted data")
    df = pd.read_csv(adjusted_path)

    print_log_message("Resetting the offset...")
    df = reset_offset(df, adjustment_data_options, adjust_col)
    df.to_csv(adjusted_path, index=False)
    return df
