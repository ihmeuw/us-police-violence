"""
Launch script for ST-GPR.
"""
import pandas as pd
from pathlib import Path
from stgpr import register_stgpr_model, stgpr_sendoff

BASE_DIR = Path("FILEPATH")
V = BASE_DIR / "FILEPATH"

BUNDLE_ID = 8345
DECOMP_STEP = 'usa_re'
GBD_ROUND_ID = 7


def create_config_file():
    config_file = pd.DataFrame()
    my_row = {
        'bundle_id': BUNDLE_ID,
        'crosswalk_version_id': pd.read_csv(V / "FILEPATH")[
            'crosswalk_version_id'
        ].item(),
        'modelable_entity_id': 26151,
        'prediction_units': 'deaths',
        'description': 'run using crosswalk covariate deaths by gun',
        'gbd_round_id': GBD_ROUND_ID,
        'decomp_step': DECOMP_STEP,
        'location_set_id': 105,
        'data_transform': 'log',
        'path_to_custom_stage_1': str(V / "FILEPATH"),
        'year_start': 1980,
        'year_end': 2019,
        'gpr_draws': 1000,
        'gpr_amp_factor':1.3,
        "add_nsv":1,
        'st_lambda': .4,
        'st_zeta': 0.001,
        'st_omega': 1,
        'gpr_scale': 5,
        'transform_offset':.001
    }
    config_file = config_file.append(my_row, ignore_index=True)
    config_file.to_csv(V / "config_file.csv", index=False)


if __name__ == '__main__':
    create_config_file()
    run_id = register_stgpr_model(str(V / "FILEPATH"))

    print(run_id)

    stgpr_sendoff(
        run_id,
        project="proj_codprep",
        nparallel=50,
        log_path="FILEPATH")
