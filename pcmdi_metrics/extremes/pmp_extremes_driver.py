#!/usr/bin/env python
import xarray as xr
import xcdat
import pandas as pd
import numpy as np
import cftime
import datetime
import sys
import os
import glob
import json
import datetime
import regionmask
import geopandas as gpd

from lib import (
    compute_metrics,
    create_extremes_parser,
    utilities,
    region_utilities,
    metadata,
    plot_extremes
)


##########
# Set up
##########

parser = create_extremes_parser.create_extremes_parser()
parameter = parser.get_parameter(argparse_vals_only=False)

# Parameters
# I/O settings
case_id = parameter.case_id
model_list = parameter.test_data_set
realization = parameter.realization
variable_list = parameter.vars
filename_template = parameter.filename_template
sftlf_filename_template = parameter.sftlf_filename_template
test_data_path = parameter.test_data_path
reference_data_path = parameter.reference_data_path
reference_data_set = parameter.reference_data_set
reference_sftlf_template = parameter.reference_sftlf_template
metrics_output_path = parameter.metrics_output_path
nc_out = parameter.nc_out
plots = parameter.plots
debug = parameter.debug
cmec = parameter.cmec
start_year = parameter.year_range[0]
end_year = parameter.year_range[1]
generate_sftlf = parameter.generate_sftlf
regrid = parameter.regrid
# Block extrema related settings
annual_strict = parameter.annual_strict
exclude_leap = parameter.exclude_leap
dec_mode = parameter.dec_mode
drop_incomplete_djf = parameter.drop_incomplete_djf
# Region masking
shp_path = parameter.shp_path
col = parameter.attribute
region_name = parameter.region_name
coords = parameter.coords

# TODO: logging

# Check the region masking parameters, if provided
use_region_mask,region_name,coords = region_utilities.check_region_params(shp_path,coords,region_name,col,"land")

# Verifying output directory
metrics_output_path = utilities.verify_output_path(metrics_output_path,case_id)

# Initialize output.json file
meta = metadata.MetadataFile(metrics_output_path)

if nc_out:
    nc_dir = os.path.join(metrics_output_path,"data")
    os.makedirs(nc_dir,exist_ok=True)
if plots:
    plot_dir = os.path.join(metrics_output_path,"plots")
    os.makedirs(plot_dir,exist_ok=True)

# Setting up model realization list
find_all_realizations,realizations = utilities.set_up_realizations(realization)

# Only include reference data in loop if it exists
if reference_data_path is not None:
    model_loop_list = ["Reference"]+model_list
else:
    model_loop_list = model_list

# Initialize output JSON structures
# FYI: if the analysis output JSON is changed, remember to update this function!
metrics_dict = compute_metrics.init_metrics_dict(model_loop_list,dec_mode,drop_incomplete_djf,annual_strict,region_name)

obs = {}

##############
# Run Analysis
##############

# Loop over models
for model in model_loop_list:

    if model=="Reference":
        list_of_runs = [str(reference_data_set)] #TODO: realizations set in multiple places
    elif find_all_realizations:
        test_data_full_path = os.path.join(
            test_data_path,
            filename_template).replace('%(model)', model).replace('%(model_version)', model).replace('%(realization)', '*')
        ncfiles = glob.glob(test_data_full_path)
        realizations = []
        for ncfile in ncfiles:
            realizations.append(ncfile.split('/')[-1].split('.')[3])
        print('=================================')
        print('model, runs:', model, realizations)
        list_of_runs = realizations
    else:
        list_of_runs = realizations
    
    metrics_dict["RESULTS"][model] = {}

    # Loop over realizations
    for run in list_of_runs:

        # SFTLF
        sftlf_exists = True
        if run == reference_data_set:
            if os.path.exists(reference_sftlf_template):
                sftlf_filename = reference_sftlf_template
            else:
                print("No reference sftlf file template provided.")
                if not generate_sftlf:
                    print("Skipping reference data")
                else:
                    # Set flag to generate sftlf after loading data
                    sftlf_exists = False
        else:
            try:
                sftlf_filename_list = sftlf_filename_template.replace('%(model)', model).replace('%(model_version)', model).replace('%(realization)', run)
                sftlf_filename = glob.glob(sftlf_filename_list)[0]
            except (AttributeError, IndexError):
                print("No sftlf file found for",model,run)
                if not generate_sftlf:
                    print("Skipping realization",run)
                    continue
                else:
                    # Set flag to generate sftlf after loading data
                    sftlf_exists = False
        if sftlf_exists:
            sftlf = xcdat.open_dataset(sftlf_filename,decode_times=False)
            # Stats calculation is expecting sfltf scaled from 0-100
            if sftlf["sftlf"].max() <= 20:
                sftlf["sftlf"] = sftlf["sftlf"] * 100.
            if use_region_mask:
                print("\nCreating sftlf region mask.")
                sftlf = region_utilities.mask_region(sftlf,region_name,coords=coords,shp_path=shp_path,column=col)
        
        metrics_dict["RESULTS"][model][run] = {}
        
        # Loop over variables - tasmax, tasmin, or pr
        for varname in variable_list:
            # Find model data, determine number of files, check if they exist
            if run==reference_data_set:
                test_data_full_path = reference_data_path
            else:
                test_data_full_path = os.path.join(
                    test_data_path,
                    filename_template
                    ).replace('%(variable)', varname).replace('%(model)', model).replace('%(model_version)', model).replace('%(realization)', run)
            test_data_full_path = glob.glob(test_data_full_path)
            if len(test_data_full_path) == 0:
                print("")
                print("-----------------------")
                print("Not found: model, run, variable:", model, run, varname)
                continue
            else:
                print("")
                print('-----------------------')
                print('model, run, variable:', model, run, varname)
                print('test_data (model in this case) full_path:')
                for t in test_data_full_path:
                    print("  ",t)

            # Load and prep data
            if len(test_data_full_path) > 1 or test_data_full_path[0].endswith(".xml"):
                ds = xcdat.open_mfdataset(test_data_full_path)
            else:
                ds = xcdat.open_dataset(test_data_full_path[0])

            if not sftlf_exists and generate_sftlf:
                print("Generating land sea mask.")
                sftlf = utilities.generate_land_sea_mask(ds,debug=debug)
                if use_region_mask:
                    print("\nCreating sftlf region mask.")
                    sftlf = region_utilities.mask_region(sftlf,region_name,coords=coords,shp_path=shp_path,column=col)

            if use_region_mask:
                print("Creating dataset mask.")
                ds = region_utilities.mask_region(ds,region_name,coords=coords,shp_path=shp_path,column=col)

            if start_year is not None and end_year is not None:
                start_time = cftime.datetime(start_year,1,1) - datetime.timedelta(days=0)
                end_time = cftime.datetime(end_year+1,1,1) - datetime.timedelta(days=1)
                ds = ds.sel(time=slice(start_time,end_time))

            if ds.time.encoding["calendar"] != "noleap" and exclude_leap:
                ds = self.ds.convert_calendar('noleap')

            # This dict is going to hold results for just this run
            stats_dict = {}

            # Here's where the extremes calculations are happening
            if varname == "tasmax":
                TXx,TXn = compute_metrics.temperature_indices(ds,varname,sftlf,dec_mode,drop_incomplete_djf,annual_strict)
                stats_dict["TXx"] = TXx
                stats_dict["TXn"] = TXn

                if run==reference_data_set:
                    obs["TXx"] = TXx
                    obs["TXn"] = TXn

                if nc_out:
                    print("Writing results to netCDF.")
                    filepath = os.path.join(
                        nc_dir,
                        "TXx_{0}.nc".format("_".join([model,run,region_name])))
                    utilities.write_to_nc(filepath,TXx)
                    meta.update_data("TXx",filepath,"TXx","Seasonal maximum of maximum temperature.")

                    filepath = os.path.join(
                        nc_dir,
                        "TXn_{0}.nc".format("_".join([model,run,region_name])))
                    utilities.write_to_nc(filepath,TXn)
                    meta.update_data("TXn",filepath,"TXn","Seasonal minimum of maximum temperature.")

                if plots:
                    print("Creating figures")
                    # TODO: pull out figure path
                    # TODO: Add year range
                    plot_extremes.plot_extremes(TXx,"TXx",model,run,plot_dir)
                    plot_extremes.plot_extremes(TXn,"TXn",model,run,plot_dir)
                    meta.update_plots("TXx","","TXx","Seasonal maximum of maximum temperature.")
                    meta.update_plots("TXn","","TXn","Seasonal minimum of maximum temperature.")

   
            if varname == "tasmin":
                TNx,TNn = compute_metrics.temperature_indices(ds,varname,sftlf,dec_mode,drop_incomplete_djf,annual_strict)
                stats_dict["TNx"] = TNx
                stats_dict["TNn"] = TNn

                if run==reference_data_set:
                    obs["TNx"] = TNx
                    obs["TNn"] = TNn

                if nc_out:
                    print("Writing results to netCDF.")
                    filepath = os.path.join(
                        nc_dir,
                        "TNx_{0}.nc".format("_".join([model,run,region_name])))
                    utilities.write_to_nc(filepath,TNx)
                    meta.update_data("TNx",filepath,"TNx","Seasonal maximum of minimum temperature.")

                    filepath = os.path.join(
                        nc_dir,
                        "TNn_{0}.nc".format("_".join([model,run,region_name])))
                    utilities.write_to_nc(filepath,TNx)
                    meta.update_data("TNn",filepath,"TNn","Seasonal minimum of minimum temperature.")

                if plots:
                    print("Creating figures")
                    plot_extremes.plot_extremes(TNx,"TNx",model,run,plot_dir)
                    plot_extremes.plot_extremes(TNn,"TNn",model,run,plot_dir)
                    meta.update_plots("TNx","","TNx","Seasonal maximum of minimum temperature.")
                    meta.update_plots("TNn","","TNx","Seasonal minimum of minimum temperature.")

            if varname in ["pr","PRECT","precip"]:
                # Rename possible precipitation variable names for consistency
                if varname in ["precip","PRECT"]:
                    ds = ds.rename({variable: "pr"})
                Rx1day,Rx5day = compute_metrics.precipitation_indices(ds,sftlf,dec_mode,drop_incomplete_djf,annual_strict)
                stats_dict["Rx1day"] = Rx1day
                stats_dict["Rx5day"] = Rx5day

                if run==reference_data_set:
                    obs["Rx1day"] = Rx1day
                    obs["Rx5day"] = Rx5day

                if nc_out:
                    print("Writing results to netCDF.")
                    filepath = os.path.join(
                        nc_dir,
                        "Rx1day_{0}.nc".format("_".join([model,run,region_name])))
                    utilities.write_to_nc(filepath,Rx1day)
                    meta.update_data("Rx1day",filepath,"Rx1day","Seasonal maximum value of daily precipitation")

                    filepath = os.path.join(
                        nc_dir,
                        "Rx5day_{0}.nc".format("_".join([model,run,region_name])))
                    utilities.write_to_nc(filepath,Rx5day)
                    meta.update_data("Rx5day",filepath,"Rx5day","Seasonal maximum value of 5-day mean precipitation")

                if plots:
                    print("Creating figures")
                    plot_extremes.plot_extremes(Rx1day,"Rx1day",model,run,plot_dir)
                    plot_extremes.plot_extremes(Rx5day,"Rx5day",model,run,plot_dir)
                    meta.update_plots("Rx5day","","Rx5day","Seasonal maximum value of 5-day mean precipitation")
                    meta.update_plots("Rx1day","","Rx1day","Seasonal maximum value of daily precipitation")

            
            # Get stats and update metrics dictionary
            print("Generating metrics.")
            result_dict = compute_metrics.metrics_json(stats_dict,sftlf,obs_dict=obs,region=region_name,regrid=regrid)
            metrics_dict["RESULTS"][model][run].update(result_dict)
            if run not in metrics_dict["DIMENSIONS"]["realization"]:
                metrics_dict["DIMENSIONS"]["realization"].append(run)

    # Pull out metrics for just this model
    # and write to JSON
    metrics_tmp = metrics_dict.copy()
    metrics_tmp["DIMENSIONS"]["model"] = model
    metrics_tmp["DIMENSIONS"]["realization"] = list_of_runs
    metrics_tmp["RESULTS"] = {model: metrics_dict["RESULTS"][model]}
    metrics_path = "{0}_extremes_metrics.json".format(model)
    utilities.write_to_json(metrics_output_path,metrics_path,metrics_tmp)

    meta.update_metrics(
        model,
        os.path.join(metrics_output_path,metrics_path),
        model+" results",
        "Seasonal metrics for block extrema for single dataset")

# Output single file with all models
metrics_dict["DIMENSIONS"]["model"] = model_loop_list
utilities.write_to_json(metrics_output_path,"extremes_metrics.json",metrics_dict)
fname=os.path.join(metrics_output_path,"extremes_metrics.json")
meta.update_metrics(
    "All",
    fname,
    "All results",
    "Seasonal metrics for block extrema for all datasets")

# Update and write metadata file
try:
        with open(fname,"r") as f:
            tmp = json.load(f)
        meta.update_provenance("environment",tmp["provenance"])
except:
    pass

meta.update_provenance("modeldata", os.path.join(test_data_path,filename_template))
if reference_data_path is not None:
    meta.update_provenance("obsdata", os.path.join(reference_data_path,reference_data_set))
meta.write()
