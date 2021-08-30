import numpy as np
from cod_prep.downloaders import get_current_location_hierarchy, get_pop_groups
from cod_prep.utils import report_if_merge_fail, warn_if_merge_fail


def get_re_args(args):
    return {arg: val for arg, val in {
        'pop_run_id': 233,
        'location_set_id': 105,
        'gbd_round_id': 6,
        'decomp_step': 'usa_re'
    }.items() if arg in args}


def get_re_loc_id(state_id, re):
    lh = get_current_location_hierarchy(
        **get_re_args(['location_set_id', 'gbd_round_id'])
    )
    assert state_id.isin(lh.query("level == 4")['location_id'].unique()).all()
    state_map = lh.query("level == 4").set_index('location_id')['location_name'].to_dict()
    re_loc_map = lh.query("level == 5").set_index('location_name')['location_id'].to_dict()
    return (state_id.map(state_map) + '; ' + re).map(re_loc_map)


def get_state_re(re_loc_id):
    lh = get_current_location_hierarchy(
        **get_re_args(['location_set_id', 'gbd_round_id'])
    )
    assert re_loc_id.isin(lh.query("level == 5")['location_id'].unique()).all()
    state_map = lh.query("level == 4").set_index('location_name')['location_id'].to_dict()
    re_loc_map = lh.query("level == 5").set_index('location_id')['location_name'].to_dict()
    df = re_loc_id.map(re_loc_map).str.split('; ', expand=True)
    df[0] = df[0].map(state_map)
    return df[0], df[1]


def get_re_map(map_version):
    """
    Get a map that standardizes race/ethnicity categories.

    Arguments:
        map_version (str): options are "four_groups" and "pv_five_groups"
    """
    standard_re = get_pop_groups().set_index('population_group_id')[
        'population_group_name'].to_dict()
    assert 999 not in standard_re.keys()
    standard_re.update({999: 'Unknown race or ethnicity'})
    if map_version == 'four_groups':
        pop_group_ids = list(range(2, 6)) + [999]
        map_position = 0
    elif map_version == 'pv_five_groups':
        pop_group_ids = list(range(2, 7)) + [999]
        map_position = 1
    else:
        raise AssertionError("Invalid R/E map version")
    re_map = {
        'White': [5, 5],
        'Black': [4, 4],
        'Unknown race': [999, 999],
        'Hispanic': [2, 2],
        'Pacific Islander': [3, 3],
        'Native American': [3, 6],
        'Asian': [3, 3],
        'Race unspecified': [999, 999],
        'African-American/Black': [4, 4],
        'European-American/White': [5, 5],
        'Hispanic/Latino': [2, 2],
        'Asian/Pacific Islander': [3, 3],
        'Native American/Alaskan': [3, 6],
        'Middle Eastern': [3, 3],
        'Unknown': [999, 999],
        'Arab-American': [3, 3],
        'Other': [3, 3],
        'Latino': [2, 2],
        'Other Race': [3, 3],
        'addrace': [3, 3],
        'aian': [3, 6],
        'api': [3, 3],
        'asian': [3, 3],
        'black': [4, 4],
        'hisp': [2, 2],
        'nhpi': [3, 3],
        'tworace': [3, 3],
        'unkrace': [999, 999],
        'white': [5, 5],
        'nhopi': [3, 3],
        'otherrace': [3, 3],
        'racedk': [999, 999]
    }
    assert set(x[map_position] for x in re_map.values()).issubset(pop_group_ids)
    re_map = {
        **{re: standard_re[re_map[re][map_position]] for re in re_map},
        **{
            standard_re[pop_group_id]: standard_re[pop_group_id]
            for pop_group_id in standard_re if pop_group_id in pop_group_ids
        }
    }
    return re_map


def redistribute_re(df, by=['sub_source', 'year_id', 'location_id'],
                    re_col='population_group_id', unknown_re=999,
                    allow_fail=True, value_col='deaths'):
    """
    Redistribute race/ethnicity unknown.
    """
    start_val = df[value_col].sum()
    known_re = df.loc[df[re_col] != unknown_re]
    known_re = known_re.groupby(
        by + [re_col], as_index=False)[value_col].sum()
    known_re['total'] = known_re.groupby(by)[value_col].transform(sum)
    known_re = known_re.loc[known_re['total'] != 0]
    known_re['prop'] = known_re[value_col] / known_re['total']
    known_re = known_re.drop([value_col, 'total'], axis='columns')
    known_re = known_re.rename(columns={re_col: re_col + '_new'})
    known_re[re_col] = unknown_re
    df = df.merge(
        known_re, how='left',
        on=by + [re_col])
    update_row = (df[re_col] == unknown_re)
    if allow_fail:
        warn_if_merge_fail(df.loc[update_row], 'prop', by + [re_col])
    else:
        report_if_merge_fail(df.loc[update_row], 'prop', by + [re_col])
    df.loc[update_row & df.prop.notnull(), value_col] = df[value_col] * df['prop']
    df.loc[update_row & df.prop.notnull(), re_col] = df[re_col + '_new']
    df = df.drop(['prop', re_col + '_new'], axis='columns')
    assert np.isclose(start_val, df[value_col].sum())
    if not allow_fail:
        assert (df[re_col] != unknown_re).all()
    return df


def calculate_pct_firearm(df, by):
    df = df.copy()
    firearm_causes = [
        'Gunshot',
        'Y35.0',
        'Y35.00',
        'Y35.001',
        'Y35.002',
        'Y35.003',
        'Y35.09',
        'Y35.091',
        'Y35.092',
        'Y35.093',
        'E970'
    ]
    assert ("int_cause" in df) ^ ("value" in df)
    for col in set({'int_cause', 'value'}).intersection(list(df)):
        df['firearm'] = df[col].isin(firearm_causes)
    assert 'firearm' in df
    pct = df.groupby(by + ['firearm'])['deaths'].sum().div(df.groupby(by)['deaths'].sum())
    assert pct.notnull().values.all()
    pct = pct.reset_index(drop=False).query("firearm == True").drop('firearm', axis='columns')
    pct = pct.rename(columns={'deaths': 'pct_firearm'})
    return pct
