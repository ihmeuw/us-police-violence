"""
Format sub-sources on US police conflict.
"""
import pandas as pd
from pathlib import Path
import numpy as np
from cod_prep.utils import report_if_merge_fail, wrap
from cod_prep.utils.formatting.ages import AgeRangeFormatter, PointAgeFormatter
from us_police_conflict_utils import (
    get_location_id_from_state, get_location_id_from_us_state_codes)

IN_DIR = Path("FILEPATH")
ID_COLS = [
    'location_id', 'year_id', 'age_group_id', 'sex_id', 'race',
    'officer_on_duty', 'int_cause'
]
VALUE_COL = ['deaths']


def collapse(df):
    """subset to final columns, check for missing values, and collapse"""
    id_cols = list(set(ID_COLS).intersection(set(df.columns)))
    final_formatted_cols = id_cols + VALUE_COL
    int_cols = [col for col in id_cols if 'id' in col]
    df = df[final_formatted_cols]
    # convert all integer data types
    df[int_cols] = df[int_cols].astype(int)
    df[VALUE_COL] = df[VALUE_COL].astype(float)
    assert df.notnull().values.all()
    df = df.groupby(id_cols, as_index=False)[VALUE_COL].sum()
    return df


def format_MPV():
    """Format Mapping Police Violence data."""
    df = pd.read_excel(
        "FILEPATH",
        sheet_name="2013-2019 Police Killings")

    # Year
    df['year_id'] = df['Date of Incident (month/day/year)'].dt.year
    assert df.year_id.between(2013, 2019).all()

    # Location
    df = get_location_id_from_us_state_codes(df, 'State')

    # Age
    df['age_unit'] = 'year'
    df['age'] = df["Victim's age"].replace({'Unknown': np.NaN, '40s': np.NaN})
    df = PointAgeFormatter().run(df).astype({'age_group_id': int})
    df.loc[df["Victim's age"] == '40s', 'age_group_id'] = 217
    report_if_merge_fail(df, 'age_group_id', "Victim's age")

    # Sex
    df['sex_id'] = df["Victim's gender"].map(
        {'Male': 1, 'Female': 2}
    ).fillna(9)

    # Race
    df['race'] = df["Victim's race"].replace({"Unknown Race": "Unknown race"})
    report_if_merge_fail(df, 'race', "Victim's race")

    # On/off duty
    df['officer_on_duty'] = df['Off-Duty Killing?'] != 'Off-Duty'

    # Intermediate cause of death
    df['int_cause'] = df['Cause of death'].str.split(', ').apply(
        lambda x: x[0]
    )
    report_if_merge_fail(df, 'int_cause', 'Cause of death')

    df['deaths'] = 1
    return collapse(df)


def format_Fatal_Encounters():
    """Format Fatal Encounters data."""
    df = pd.read_excel(
        "FILEPATH",
        sheet_name="Form Responses"
    )

    # Year
    df['year_id'] = df['Date of injury resulting in death (month/day/year)'].dt.year
    df = df.loc[df.year_id != 2100]
    df = df.loc[df.year_id != 2020]
    assert df.year_id.between(2000, 2019).all()

    # Location
    df = get_location_id_from_us_state_codes(df, 'Location of death (state)')

    # Age
    df['age'] = df["Subject's age"]
    df['age_unit'] = 'year'
    df.loc[df.age.str.contains("mon", na=False), 'age_unit'] = 'month'
    df.loc[df.age.str.contains("day", na=False), 'age_unit'] = 'day'
    df['age'] = df.age.astype(str)\
        .str.rstrip(" `monthsdays")\
        .str.replace("s", "")\
        .str.replace(" or ", "-")
    rngs = df['age'].astype(str).str.split("[-/]", expand=True)
    df['age_start'] = rngs[0].replace({"": np.NaN}).astype(float)
    df['age_end'] = rngs[1].astype(float)
    df['age_end'] = df['age_end'].fillna(df['age_start'])
    df['age_end'].update(
        df["Subject's age"].str.extract(".*(\d{2}s)$")[0]
        .str.replace("s", "").astype(float) + 9
    )
    df = pd.concat(
        [
            AgeRangeFormatter().run(df.query("age_start != age_end")),
            PointAgeFormatter(age_col='age_start').run(df.query("age_start == age_end"))
        ]
    )
    df['age_group_id'] = df['age_group_id'].astype(int)

    # Sex
    df['sex_id'] = df["Subject's gender"].map(
        {'Male': 1, 'Female': 2}
    ).fillna(9)

    # Race
    df = df.reset_index(drop=True)
    df['race'] = df["Subject's race"]
    # Accept any imputed race with imputation probability >= 80%
    # We found that this was the highest threshold that gave a reasonable
    # race/ethnicity distribution in terms of consistency across the time series
    # and feasibility for redistribution of unknown race/ethnicity
    df['impute_prob'] = pd.to_numeric(df['Imputation probability'], errors='coerce')
    df.loc[
        (df['race'] == 'Race unspecified') & (df['impute_prob'] >= 0.8), 'race'
    ] = df["Subject's race with imputations"]

    # On/off duty
    df['officer_on_duty'] = "Unknown"

    # Intermediate cause of death
    df['int_cause'] = df['Cause of death']

    df['deaths'] = 1

    return collapse(df)


def format_The_Counted():
    """Format The Counted (Guardian)"""
    df = pd.concat([
        pd.read_csv("FILEPATH")
        for year in [2015, 2016]
    ], sort=True)

    # Year
    df['year_id'] = df['year']

    # Location
    df = get_location_id_from_us_state_codes(df, 'state')

    # Age
    df['age_original'] = df['age']
    df['age_unit'] = 'year'
    df['age'] = df["age"].replace({'Unknown': np.NaN, '40s': np.NaN}).astype(float)
    df = PointAgeFormatter().run(df).astype({'age_group_id': int})
    df.loc[df["age_original"] == '40s', 'age_group_id'] = 217
    report_if_merge_fail(df, 'age_group_id', "age_original")

    # Sex
    df['sex_id'] = df['gender'].map({'Male': 1, 'Female': 2, 'Non-conforming': 9})

    # Race
    df['race'] = df['raceethnicity']

    # Intermediate cause
    df['int_cause'] = df['classification']

    df['deaths'] = 1
    return collapse(df)


def get_sub_sources():
    return {
        'MPV': {
            'formatter': format_MPV,
            'ucod': 'police conflict (civilian deaths)'},
        'Fatal_Encounters': {
            'formatter': format_Fatal_Encounters,
            'ucod': 'police conflict (civilian deaths)'},
        'The_Counted': {
            'formatter': format_The_Counted,
            'ucod': 'police conflict (civilian deaths)'}
    }


def format_sub_sources(sub_sources):
    sub_sources = wrap(sub_sources)
    available_sub_sources = get_sub_sources()
    assert set(sub_sources).issubset(set(available_sub_sources))
    return pd.concat([
        available_sub_sources[sub_source]['formatter']().assign(
            sub_source=sub_source,
            underlying_cause=available_sub_sources[sub_source]['ucod']
        ) for sub_source in sub_sources
    ], sort=True)
