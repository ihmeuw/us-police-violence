import pandas as pd
import numpy as np
import os
import pandas as pd
from pathlib import Path
import getpass
import sys
COD_DIR = 'FILEPATH'.format(getpass.getuser())
sys.path.append(COD_DIR)
from cod_prep.utils.misc import report_if_merge_fail, create_square_df
from cod_prep.downloaders import (
    add_location_metadata, getcache_age_aggregate_to_detail_map, get_pop,
    add_population, get_cod_ages, pretty_print)
from cod_prep.claude.configurator import Configurator
from cod_prep.claude.relative_rate_split import relative_rate_split
CONF = Configurator()
from db_queries import get_location_metadata
from db_queries import get_population
from db_tools import ezfuncs
import argparse

DEM_COLS = ['location_id', 'year_id', 'age_group_id', 'sex_id']
BASE_DIR = Path("FILEPATH")
WORKING_DIR = BASE_DIR / "FILEPATH"

# define the raking function
def rake(df, column_to_rake, value_col, level_from, level_to, id_cols):
    assert set(
        [column_to_rake, 'parent_id', 'level', value_col] + id_cols
    ) <= set(df)
    start_cols = set(df)
    assert level_from - level_to == 1
    df['detail_total'] = df.groupby(
        id_cols + ['parent_id'])[value_col].transform(sum)
    agg_df = df.copy().assign(**{
        'level': df['level'] + 1})\
        .drop('parent_id', axis='columns')\
        .rename(columns={column_to_rake: 'parent_id'})\
        .loc[:, id_cols + ['parent_id', 'level', value_col]]
    df = df.merge(
        agg_df, how='left', on=id_cols + ['parent_id', 'level'],
        validate='many_to_one', suffixes=('', '_agg')
    )
    report_if_merge_fail(
        df.query(f"level == {level_from}"), value_col + '_agg',
        id_cols + [column_to_rake]
    )
    df.loc[df.level == level_from, value_col] = df[value_col] * df[value_col + '_agg'] \
        / df['detail_total']
    assert df[value_col].notnull().all()
    return df[list(start_cols)]

# run everything
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--year_id", type=int,
                        help="The year ID of that these draws will save")
    parser.add_argument("-m", "--model_id", type=int,
                        help="the model the draws will be saved for")
    parser.add_argument("-s", "--save_dir", type=str,
                        help="the path the draws will be saved for")
    parser.add_argument("-p", "--population_filepath", type=str,
                        help="the population the draws will be saved for")
    parser.add_argument("-l", "--location_filepath", type=str,
                        help="the location the draws will be saved for")

    cmd_args = parser.parse_args()
    year = cmd_args.year_id
    model_id = cmd_args.model_id
    save_dir = cmd_args.save_dir
    location_filepath = cmd_args.location_filepath
    population_filepath = cmd_args.population_filepath

    draw_cols = list()
    for integer in range(0,1000):
        draw_cols.append(f"draw_{integer}")

    # read in location here
    locs = pd.read_csv(location_filepath)

    # read in population here
    pop_df = pd.read_csv(population_filepath)

    pop_id_cols = DEM_COLS

    cw = pd.read_csv(WORKING_DIR / "FILEPATH")
    cw = cw.groupby(DEM_COLS + ['sub_source'], as_index=False)['deaths_adjusted'].sum()

    # read in model and subest to only the current year
    df = pd.DataFrame()
    all_location_files = os.listdir(f"FILEPATH")
    for location_file in all_location_files:
        tmp = pd.read_csv(f"FILEPATH")
        tmp = tmp.query(f"year_id == {year}")
        df = df.append(tmp.copy())

    original_shape = df.copy().shape[0]
    df = df.merge(locs)
    assert df.shape[0] == original_shape 

    for draw_col in draw_cols:
        df[draw_col] = np.clip(df[draw_col] - .001, 0, a_max=np.nan)

    # age sex split model
    start_cols = set(df)
    print("prepping weights")
    ages = get_cod_ages(gbd_round_id=CONF.get_id("gbd_round"))
    cw = cw.loc[
        cw.age_group_id.isin(ages.age_group_id.unique().tolist()) &
        cw.sex_id.isin([1, 2])
    ]
    value_col_ref = "deaths_adjusted"

    original_shape = cw.copy().shape[0]
    cw = cw.merge(pop_df, how='left')
    assert cw.shape[0] == original_shape 

    weight_cols = ['age_group_id', 'sex_id']
    cw = cw.groupby(weight_cols, as_index=False)[
        [value_col_ref, 'population']].sum()
    cw['weight'] = cw[value_col_ref] / cw['population']
    cw_sq = create_square_df(cw, weight_cols)
    cw = cw_sq.merge(
        cw, how='left', on=weight_cols, validate='one_to_one').fillna(0)
    cw = cw[weight_cols + ['weight']]
    cw['cause'] = 'pv'

    print("prep age map")
    age_detail_map = getcache_age_aggregate_to_detail_map(
        gbd_round_id=CONF.get_id("gbd_round"),
        force_rerun=False, block_rerun=True
    )
    sex_detail_map = pd.DataFrame(
        columns=['agg_sex_id', 'sex_id'],
        data=[
            [3, 1],
            [3, 2],
            [9, 1],
            [9, 2],
            [1, 1],
            [2, 2]
        ]
    )
    detail_maps = {
        'age_group_id': age_detail_map,
        'sex_id': sex_detail_map
    }

    print("prep which distributions should be used")
    cause_to_weight_cause_map = pd.DataFrame([['pv', 'pv']],
        columns=['cause', 'dist_cause'])
    val_to_dist_maps = {
        'cause': cause_to_weight_cause_map
    }
    # which columns are to be split
    split_cols = ['age_group_id', 'sex_id']
    split_inform_cols = ['cause']
    value_cols = [draw_cols]
    start_val = df[draw_cols].sum()
    df['orig_location_id'] = df['location_id']
    df['cause'] = 'pv'
    df = relative_rate_split(
        df,
        pop_df,
        cw,
        detail_maps,
        split_cols,
        split_inform_cols,
        pop_id_cols,
        draw_cols,
        pop_val_name='population',
        val_to_dist_map_dict=val_to_dist_maps,
        verbose=True
    )
    
    # rake model, rake one draw column at a time
    # rake from most detailed to national
    print("raking draws")
    for draw_col in draw_cols:
        # 4 to 3
        df = rake(df, 'location_id', draw_col, 4, 3, ['year_id', 'age_group_id', 'sex_id'])
        # 5 to 4
        df = rake(df, 'location_id', draw_col, 5, 4, ['year_id', 'age_group_id', 'sex_id'])


    
    print(f"Change of {df[draw_cols].sum() - start_val}")
    df = df[start_cols]
    df.to_csv(save_dir + f"FILEPATH")