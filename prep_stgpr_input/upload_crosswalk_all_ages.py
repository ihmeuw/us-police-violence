import pandas as pd
import numpy as np
from pathlib import Path
from getpass import getuser
from elmo import (
    get_bundle_data, upload_bundle_data, save_bundle_version, get_bundle_version,
    save_crosswalk_version
)
from cod_prep.utils import report_duplicates, report_if_merge_fail
from cod_prep.downloaders import (
    add_age_metadata, add_location_metadata, add_population,
    get_datasets)
from cod_prep.claude.configurator import Configurator

BASE_DIR = Path("FILEPATH")
NEW_DIR = BASE_DIR / "FILEPATH"
BUNDLE_ID = 8345
DECOMP_STEP = 'usa_re'
GBD_ROUND_ID = 7
CONF = Configurator()
LSV_ID = 608
LS_ID = 105


def delete_old_rows():
    df = get_bundle_data(
        bundle_id=BUNDLE_ID, decomp_step=DECOMP_STEP, gbd_round_id=GBD_ROUND_ID)
    print(df.seq.min())
    print(df.seq.max())
    df = df[['seq']].drop_duplicates()
    delete_path = NEW_DIR / "FILEPATH"
    df.to_excel(delete_path, sheet_name='extraction', index=False)
    upload_bundle_data(
        bundle_id=BUNDLE_ID,
        decomp_step=DECOMP_STEP,
        gbd_round_id=GBD_ROUND_ID,
        filepath=str(delete_path))


def aggregate_location(df, id_cols, sum_cols):
    df = add_location_metadata(df, 'parent_id', location_set_version_id=LSV_ID, location_set_id=LS_ID)
    report_if_merge_fail(df, 'parent_id', 'location_id')
    df['location_id'] = df['parent_id']
    df = df.drop('parent_id', axis='columns')
    return df.groupby(id_cols, as_index=False)[sum_cols].sum()


def prep_new_bundle_data():
    print("Prepping the data")
    df = pd.read_csv(BASE_DIR / "FILEPATH")

    # First aggregate location
    # SE is in rate space - convert to deaths
    df['variance'] = (df['population'] * df['se_adjusted']) ** 2
    variance = df['variance'].mean()
    print(df['variance'].max(), variance, df['variance'].min())
    df['variance'] = df['variance'].replace(0, variance)
    assert (df['variance'] > 0).all()
    df['sample_size'] = df['population']
    df = df.assign(age_group_id=22, sex_id=3)
    id_cols = ['location_id', 'year_id', 'age_group_id', 'sex_id', 'sub_source']
    sum_cols = ['deaths_adjusted', 'variance', 'sample_size']
    df = df.groupby(id_cols, as_index=False)[sum_cols].sum()
    assert df.notnull().values.all()
    level_4_aggs = aggregate_location(df, id_cols, sum_cols)
    level_3_aggs = aggregate_location(level_4_aggs, id_cols, sum_cols)
    df = pd.concat([df, level_4_aggs, level_3_aggs])
    report_duplicates(df, id_cols)

    # Add important columns
    # Age group
    df = add_age_metadata(df, ['age_group_years_start', 'age_group_years_end'])
    df = df.rename(columns={
        'age_group_years_start': 'age_start',
        'age_group_years_end': 'age_end'})
    datasets = get_datasets(is_active=True, iso3='USA', data_type_id=9)[
        ['year_id', 'nid']
    ].drop_duplicates()
    report_duplicates(datasets, ['year_id'])
    datasets['sub_source'] = 'NVSS'
    df = df.merge(datasets, how='left', on=['year_id', 'sub_source'], validate='many_to_one')
    df['nid'] = df['nid'].fillna(df['sub_source'].map({
        'MPV': 448794, 'Fatal_Encounters': 448791, 'The_Counted': 453326
    }))
    df['nid'] = df['nid'].where(~
        ((df['sub_source'] == 'NVSS') & 
        (df['year_id'] == 2018)), 
        other=456291
    )   
    assert df['nid'].notnull().all()
    # Other columns
    df['val'] = df['deaths_adjusted']
    df = df.drop('deaths_adjusted', axis='columns')
    df = df.assign(**{
        'underlying_nid': np.NaN,
        'seq': np.NaN,
        'measure': 'continuous', 
        'is_outlier': 0,
        'year_start': df['year_id'],
        'year_end': df['year_id'],
        'sex': df['sex_id'].map({1: 'Male', 2: 'Female', 3: 'Both'})
    })
    save_path = NEW_DIR / "FILEPATH"
    print("Saving the excel sheet")
    df.to_excel(
        save_path,
        sheet_name='extraction',
        index=False)
    print("Uploading")
    upload_bundle_data(
        bundle_id=BUNDLE_ID,
        decomp_step=DECOMP_STEP,
        gbd_round_id=GBD_ROUND_ID,
        filepath=str(save_path))


def save_bv():
    result = save_bundle_version(
        bundle_id=BUNDLE_ID, decomp_step=DECOMP_STEP, gbd_round_id=GBD_ROUND_ID)
    print(result)
    result.to_csv(NEW_DIR / "FILEPATH", index=False)


def prep_cw_version():
    print("Pulling the data")
    bundle_version_id = pd.read_csv(
        NEW_DIR / "bundle_version.csv")['bundle_version_id'].item()
    df = get_bundle_version(bundle_version_id, export=False, fetch='all')
    print("Prepping the data")
    goal_cols = pd.read_csv("FILEPATH").need_cols.tolist()
    df = df.drop(list(set(df) - set(goal_cols)), axis='columns')

    df['urbanicity_type'] = 'mixed/both'
    df['recall_type'] = 'point'
    df['unit_value_as_published'] = 1
    df['unit_type'] = 'person'
    df['group_review'] = 1
    df['sex_id'] = df['sex'].map({'Male': 1, 'Female': 2, 'Both': 3})
    df.loc[df.sub_source.isin(['MPV', 'Fatal_Encounters', 'The_Counted']), 'source_type'] =\
        'News report'
    df['source_type'] = df['source_type'].fillna('Vital registration - national')
    df['representative_name'] = 'Representative for subnational location only'
    for col in [
        'crosswalk_parent_seq', 'design_effect', 'effective_sample_size',
        'sampling_type', 'input_type', 'recall_type_value', 'uncertainty_type'
    ]:
        df[col] = np.NaN
    assert set(df) == set(goal_cols)

    print("Saving the excel sheet")
    save_path = NEW_DIR / "FILEPATH"
    df.to_excel(
        save_path, index=False,
        sheet_name='extraction'
    )
    print("Running save_crosswalk_version")
    results = save_crosswalk_version(
        bundle_version_id=bundle_version_id,
        data_filepath=str(save_path)
    )
    print(results)
    results.to_csv(NEW_DIR / "FILEPATH", index=False)


if __name__ == '__main__':
    delete_old_rows()
    prep_new_bundle_data()
    save_bv()
    prep_cw_version()
