#!/usr/bin/env python

import json
import os
from re import split

import cdms2
import cdutil
import xcdat

from pcmdi_metrics import resources
from pcmdi_metrics.io import xcdat_open
from pcmdi_metrics.mean_climate.lib import create_mean_climate_parser

parser = create_mean_climate_parser()
parameter = parser.get_parameter(cmd_default_vars=False, argparse_vals_only=False)

"""
dir(parameter): ['__add__', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'case_id', 'check_case_id', 'check_custom_keys', 'check_custom_observations_path', 'check_filename_output_template', 'check_filename_template', 'check_generate_surface_type_land_fraction', 'check_metrics_output_path', 'check_period', 'check_realization', 'check_ref', 'check_reference_data_path', 'check_reference_data_set', 'check_regions', 'check_regions_specs', 'check_regions_values', 'check_regrid_method', 'check_regrid_method_ocn', 'check_regrid_tool', 'check_regrid_tool_ocn', 'check_save_test_clims', 'check_str', 'check_str_seq_in_str_list', 'check_str_var_in_str_list', 'check_surface_type_land_fraction_filename_template', 'check_target_grid', 'check_test_clims_interpolated_output', 'check_test_data_path', 'check_test_data_set', 'check_values', 'check_vars', 'custom_keys', 'custom_observations_path', 'dry_run', 'filename_output_template', 'filename_template', 'generate_sftlf', 'generate_surface_type_land_fraction', 'import_user_parameter_file_as_module', 'load_parameter_from_py', 'load_parameters_from_module', 'metrics_output_path', 'os', 'output_json_template', 'period', 'r', 'realization', 'reference_data_path', 'reference_data_set', 'regions', 'regions_specs', 'regions_values', 'regrid_method', 'regrid_method_ocn', 'regrid_tool', 'regrid_tool_ocn', 'save_test_clims', 'sftlf_filename_template', 'surface_type_land_fraction_filename_template', 't', 'target_grid', 'test_clims_interpolated_output', 'test_data_path', 'test_data_set', 'user_notes', 'v', 'vars']
"""

case_id = parameter.case_id
test_data_set = parameter.test_data_set
vars = parameter.vars
reference_data_set = parameter.reference_data_set
target_grid = parameter.target_grid
regrid_tool = parameter.regrid_tool
regrid_method = parameter.regrid_method
regrid_tool_ocn = parameter.regrid_tool_ocn
save_test_clims = parameter.save_test_clims
test_clims_interpolated_output = parameter.test_clims_interpolated_output
filename_template = parameter.filename_template
sftlf_filename_template = parameter.sftlf_filename_template
generate_sftlf = parameter.generate_sftlf
regions = parameter.regions
test_data_path = parameter.test_data_path
reference_data_path = parameter.reference_data_path
metrics_output_path = parameter.metrics_output_path

print(
    'case_id: ', case_id, '\n',
    'test_data_set:', test_data_set, '\n',
    'vars:', vars, '\n',
    'reference_data_set:', reference_data_set, '\n',
    'target_grid:', target_grid, '\n',
    'regrid_tool:', regrid_tool, '\n',
    'regrid_method:', regrid_method, '\n',
    'regrid_tool_ocn:', regrid_tool_ocn, '\n',
    'save_test_clims:', save_test_clims, '\n',
    'test_clims_interpolated_output:', test_clims_interpolated_output, '\n',
    'filename_template:', filename_template, '\n',
    'sftlf_filename_template:', sftlf_filename_template, '\n',
    'generate_sftlf:', generate_sftlf, '\n',
    'regions:', regions, '\n',
    'test_data_path:', test_data_path, '\n',
    'reference_data_path:', reference_data_path, '\n',
    'metrics_output_path:', metrics_output_path, '\n')

default_regions = ['global', 'NHEX', 'SHEX', 'TROPICS']

print('--- start mean climate metrics calculation ---')

# generate target grid
if target_grid == "2.5x2.5":
    t_grid = xcdat.create_uniform_grid(-88.875, 88.625, 2.5, 0, 357.5, 2.5)
    t_grid_cdms2 = cdms2.createUniformGrid(-88.875, 72, 2.5, 0, 144, 2.5)
    sft = cdutil.generateLandSeaMask(t_grid_cdms2)

# load obs catalogue json
egg_pth = resources.resource_path()
obs_file_name = "obs_info_dictionary.json"
obs_file_path = os.path.join(egg_pth, obs_file_name)
with open(obs_file_path) as fo:
    obs_dict = json.loads(fo.read())
# print('obs_dict:', obs_dict)

# -------------
# variable loop
# -------------
for var in vars:

    if '_' in var or '-' in var:
        varname = split('_|-', var)[0]
        level = float(split('_|-', var)[1]) * 100  # hPa to Pa
    else:
        varname = var
        level = None

    if varname not in list(regions.keys()):
        regions[varname] = default_regions

    print('varname:', varname)
    print('level:', level)

    # ----------------
    # observation loop
    # ----------------
    for ref in reference_data_set:
        # load data
        print('ref:', ref)
        ref_dataset_name = obs_dict[varname][ref]
        ref_data_full_path = os.path.join(
            reference_data_path,
            obs_dict[varname][ref_dataset_name]["template"])
        print('ref_data_full_path:', ref_data_full_path)
        #ds_ref = xcdat_open(ref_data_full_path, data_var=var)
        ds_ref = xcdat_open(ref_data_full_path, data_var=var, decode_times=False)  # NOTE: decode_times=False will be removed once obs4MIP written using xcdat
        print('ds_ref:', ds_ref)
        # regrid
        ds_ref_regridded = ds_ref.regridder.horizontal(var, t_grid, tool=regrid_tool)
        print('ds_ref_regridded:', ds_ref_regridded)


        # ----------
        # model loop
        # ----------
        for model in test_data_set:
            # load data
            print('model:', model)

            # regrid

            # -----------
            # region loop
            # -----------
            for region in regions[varname]:
                print('region:', region)

                if region.split('_')[0] in ['land', 'ocean']:
                    is_masking = True
                else:
                    is_masking = False

            # write JSON for single model / single obs (need to accumulate later) / single variable

    # write JSON for all models / all obs / single variable
