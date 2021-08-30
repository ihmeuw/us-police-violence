from cod_prep.downloaders import (
    add_location_metadata,
    get_current_location_hierarchy
)
from cod_prep.claude.configurator import Configurator
from cod_prep.utils import report_if_merge_fail
CONF = Configurator()


def get_location_id_from_us_state_codes(df, state_code_col, fill=False):
    # Location
    df['local_id'] = 'US-' + df[state_code_col]
    lh = get_current_location_hierarchy(
        location_set_version_id=CONF.get_id('location_set_version'),
        location_set_id=CONF.get_id("location_set")
    ).query("parent_id == 102")
    df = add_location_metadata(
        df, 'location_id', merge_col='local_id',
        location_meta_df=lh
    )
    if fill:
        df['location_id'] = df['location_id'].fillna(102)
    report_if_merge_fail(df, 'location_id', state_code_col)
    return df


def get_location_id_from_state(df, state_col, fill=False):
    df['location_name'] = df[state_col]
    lh = get_current_location_hierarchy(
        location_set_version_id=CONF.get_id('location_set_version'),
        location_set_id=CONF.get_id("location_set")
    ).query("parent_id == 102")
    df = add_location_metadata(
        df, 'location_id', merge_col='location_name',
        location_meta_df=lh
    )
    if fill:
        df['location_id'] = df['location_id'].fillna(102)
    report_if_merge_fail(df, 'location_id', state_col)
    return df
