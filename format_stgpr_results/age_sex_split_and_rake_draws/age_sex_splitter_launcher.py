import pandas as pd
import getpass
from db_queries import get_location_metadata
from db_queries import get_population
from db_tools import ezfuncs
from pathlib import Path
import os
import subprocess


user = getpass.getuser()
MODEL_ID = 190430
SAVE_DIR = Path(f"FILEPATH")
DEM_COLS = ['location_id', 'year_id', 'age_group_id', 'sex_id']

if not os.path.exists(SAVE_DIR):
    os.mkdir(SAVE_DIR)

location_filepath = SAVE_DIR / "loc_meta.csv"
population_filepath = SAVE_DIR / "pop_data.csv"


# pull location metadata
locs = get_location_metadata(location_set_id=105)[['location_id','parent_id','level']]
locs.to_csv(location_filepath, index=False)

# pull population
get_pop = """
        SELECT * FROM ADDRESS
        WHERE run_id = 233
        """
pop = ezfuncs.query(get_pop, conn_def="view_mort")
pop = pop[['year_id','location_id','sex_id','age_group_id','population']]
pop = pop.drop_duplicates()
pop_id_cols = DEM_COLS
pop_df = pop

pop.to_csv(population_filepath, index=False)


for year_id in list(range(1980,2020)):

    errout_path = "FILEPATH"
    python_shell = "FILEPATH".format(user)
    code_path = "FILEPATH".format(user)
    qsub_string = (
                "qsub -N {name} -l m_mem_free=4G -l fthread=1 -l archive=True -l h_rt=10:00:00 -P proj_shocks"
                " -e {error_path} -q all.q {shell} {code_path}"
                " --year_id {year_id} --save_dir {save_dir}"
                " --population_filepath {population_filepath}"
                " --location_filepath {location_filepath}"
                " --model_id {model_id}".format(
                    name="police_stgpr_rake_{}_{}".format(MODEL_ID, year_id), error_path=errout_path,
                    shell=python_shell, code_path=code_path, year_id=int(year_id), save_dir=SAVE_DIR,
                    location_filepath=location_filepath, population_filepath=population_filepath,
                    model_id=int(MODEL_ID)))

    qsub = subprocess.Popen(qsub_string,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)

    (stdout, stderr) = qsub.communicate()