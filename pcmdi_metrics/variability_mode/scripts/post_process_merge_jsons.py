#!/usr/bin/env python

from __future__ import print_function
from genutil import StringConstructor
from pcmdi_metrics.variability_mode.lib import dict_merge

import copy
import glob
import json
import os


def main():
    # mips = ['cmip5', 'cmip6']
    mips = ['cmip6']
    # mips = ['cmip3']

    exps = ['historical', 'amip']
    # exps = ['historical']
    # exps = ['20c3m', 'amip']

    # case_id = 'v20200221'
    case_id = 'v20200803'

    syear = 1900
    eyear = 2005

    # pmprdir = '/work/lee1043/imsi/result_test'
    pmprdir = '/p/user_pub/pmp/pmp_results/pmp_v1.1.2'

    for mip in mips:
        for exp in exps:

            if exp == 'amip':
                modes = ['NAM', 'NAO', 'PNA', 'SAM', 'NPO']
            else:
                modes = ['NAM', 'NAO', 'PNA', 'SAM', 'NPO', 'PDO', 'NPGO']

            for mode in modes:
                # eof
                if mode in ['NPO', 'NPGO']:
                    eof = 'EOF2'
                else:
                    eof = 'EOF1'
                # obs name
                if mode in ['PDO', 'NPGO']:
                    obs = 'HadISSTv1.1'
                else:
                    obs = 'NOAA-CIRES_20CR'
                # json merge
                merge_json(mode, eof, mip, exp, case_id, obs, syear, eyear, pmprdir)


def merge_json(mode, eof, mip, exp, case_id, obs, syear, eyear, pmprdir):
    json_file_dir_template = 'metrics_results/variability_modes/%(mip)/%(exp)/%(case_id)/%(mode)/%(obs)'
    json_file_dir_template = StringConstructor(json_file_dir_template)
    json_file_dir = os.path.join(
        pmprdir,
        json_file_dir_template(mip=mip, exp=exp, case_id=case_id, mode=mode, obs=obs))

    json_file_template = 'var_mode_%(mode)_%(eof)_stat_%(mip)_%(exp)_mo_atm_%(model)_%(run)_%(syear)-%(eyear).json'
    json_file_template = StringConstructor(json_file_template)

    # Search for individual JSONs
    json_files = sorted(glob.glob(
        os.path.join(
            json_file_dir,
            json_file_template(mode=mode, eof=eof, mip=mip, exp=exp, model='*', run='*', syear='*', eyear='*'))))

    # Remove diveDown JSONs and previously generated merged JSONs if included
    json_files_revised = copy.copy(json_files)
    for j, json_file in enumerate(json_files):
        filename_component = json_file.split('/')[-1].split('.')[0].split('_')
        if 'allModels' in filename_component:
            json_files_revised.remove(json_file)
        elif 'allRuns' in filename_component:
            json_files_revised.remove(json_file)

    # Load individual JSON and merge to one big dictionary
    for j, json_file in enumerate(json_files_revised):
        print(j, json_file)
        f = open(json_file)
        dict_tmp = json.loads(f.read())
        if j == 0:
            dict_final = dict_tmp.copy()
        else:
            dict_merge(dict_final, dict_tmp)
        f.close()

    # Dump final dictionary to JSON
    final_json_filename = json_file_template(
        mode=mode, eof=eof, mip=mip, exp=exp, model='allModels', run='allRuns', syear=str(syear), eyear=str(eyear))
    final_json_file = os.path.join(json_file_dir, final_json_filename)

    with open(final_json_file, 'w') as fp:
        json.dump(dict_final, fp, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()