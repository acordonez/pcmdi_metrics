#!/usr/bin/env python
import cftime
import datetime
import numpy as np
import os
import xarray as xr
import xcdat as xc
import climextremes
import glob
from pcmdi_metrics.extremes.lib import utilities

def compute_rv_from_file(filelist,cov_filepath,cov_name,outdir,return_period,maxes=True):
    # Go through all files and get return value and standard error by file.
    # Write results to netcdf file.
    for ncfile in filelist:
        ds = xc.open_dataset(ncfile)
        rv,se = get_dataset_rv(ds,cov_filepath,cov_name,return_period,maxes)
        if rv is None:
            print("Error in calculating return value for",ncfile)
            print("Skipping file.")
            continue
        fname = os.path.basename(ncfile).replace(".nc","")
        utilities.write_netcdf_file(outdir+"/"+fname+"_return_value.nc",rv)
        utilities.write_netcdf_file(outdir+"/"+fname+"_standard_error.nc",se)


def compute_rv_for_model(filelist,cov_filepath,cov_varname,ncdir,return_period,maxes=True):
    # Similar to compute_rv_from_file, but to work on multiple realizations
    # from the same model
    # Nonstationary GEV requiring covariate
    nreal = len(filelist)

    ds = xc.open_dataset(filelist[0])

    if cov_filepath is not None:
        nonstationary  = True
    else:
        nonstationary = False
    
    if nonstationary:
        cov_ds = utilities.load_dataset([cov_filepath])

        if len(cov_ds.time) != len(ds.time):
            start_year = int(ds.time.dt.year[0])
            end_year = int(ds.time.dt.year[-1])
            cov_ds = utilities.slice_dataset(cov_ds,start_year,end_year)

        # Even after slicing, it's possible that time ranges didn't overlap
        if len(cov_ds.time) != len(ds.time):
            print("Covariate timeseries must have same number of years as block extremes dataset.")
            print("Skipping return value calculation for files:")
            print(filelist)
            return None,None

        # To numpy array
        cov_np = cov_ds[cov_varname].data.squeeze()
        cov_ds.close()

    dec_mode = str(ds.attrs["december_mode"])
    drop_incomplete_djf = bool(ds.attrs["drop_incomplete_djf"])

    time = len(ds.time) # This will change for DJF cases
    lat = len(ds.lat)
    lon = len(ds.lon)
    # Add and order additional dimension for realization
    if nonstationary:
        return_value = xr.zeros_like(ds).expand_dims(dim={"real": nreal}).assign_coords({"real": range(0,nreal)})
        return_value = return_value[["real","time", "lat", "lon"]]
    else:
        return_value = xr.zeros_like(ds.isel({"time":0})).expand_dims(dim={"real": nreal}).assign_coords({"real": range(0,nreal)})
        return_value = return_value.drop(labels=["time"])
        return_value = return_value[["real","lat", "lon"]]
    standard_error = xr.zeros_like(return_value)

    for season in ["ANN","DJF","MAM","JJA","SON"]:
        if season == "DJF" and dec_mode == "DJF" and drop_incomplete_djf:
            # Step first time index to skip all-nan block
            i1 = 1
        else:
            i1 = 0
        if nonstationary:
            cov = cov_np[i1:]
            cov_tile = np.tile(cov,nreal).squeeze()
        else:
            cov_tile = None
        # Flatten input data and create output arrays
        t = time-i1
        arr = np.ones((t*nreal,lat*lon))
        rep_ind = np.zeros((t*nreal))
        count=0
        for ncfile in filelist:
            ds = xc.open_dataset(ncfile)
            data = np.reshape(ds[season].data,(time,lat*lon))
            ind1 = count*t
            ind2 = ind1+t
            count+=1
            arr[ind1:ind2,:] = data[i1:,:]
            rep_ind[ind1:ind2] = count
            ds.close()
        scale_factor = np.abs(np.nanmean(arr))
        arr = arr / scale_factor
        if nonstationary:
            rv_array = np.ones((t*nreal,lat*lon)) * np.nan
        else:
            rv_array = np.ones((nreal,lat*lon)) * np.nan
        se_array = rv_array.copy()
        # Here's where we're doing the return value calculation
        for j in range(0,lat*lon):
            rv,se = calc_rv(arr[:,j].squeeze(),cov_tile,return_period,nreplicates=nreal,maxes=maxes)
            if rv is not None:
                rv_array[:,j] = rv*scale_factor
                se_array[:,j] = se*scale_factor

        # reshape array to match desired dimensions and add to Dataset
        if nonstationary:
            rv_array = np.reshape(rv_array,(nreal,t,lat,lon))
            se_array = np.reshape(se_array,(nreal,t,lat,lon))
            if season == "DJF" and dec_mode == "DJF" and drop_incomplete_djf:
                nans = np.ones((nreal,1,lat,lon))*np.nan
                rv_array = np.concatenate((nans,rv_array),axis=1)
                se_array = np.concatenate((nans,se_array),axis=1)
            return_value[season] = (("real","time", "lat", "lon"),rv_array)
            standard_error[season] = (("real","time","lat","lon"),se_array)
        else:
            rv_array = np.reshape(rv_array,(nreal,lat,lon))
            se_array = np.reshape(se_array,(nreal,lat,lon))
            return_value[season] = (("real","lat", "lon"),rv_array)
            standard_error[season] = (("real","lat","lon"),se_array)
    
    if nonstationary:
        # reorder dimensions
        return_value = return_value[["time", "real", "lat", "lon"]]
        standard_error = standard_error[["time", "real", "lat", "lon"]]
    return_value = return_value.bounds.add_missing_bounds() 
    standard_error = standard_error.bounds.add_missing_bounds()

    fname = os.path.basename(filelist[0])
    real = fname.split("_")[1]
    fname = fname.replace(real+"_","").replace(".nc","")
    outfile = os.path.join(ncdir,fname+"_return_value.nc")
    utilities.write_netcdf_file(outfile,return_value)
    outfile = os.path.join(ncdir,fname+"_standard_error.nc")
    utilities.write_netcdf_file(outfile,standard_error)

    return return_value,standard_error

def get_dataset_rv(ds,cov_filepath,cov_varname,return_period=20,maxes=True):
    # Get the return value for a single model & realization
    # Set cov_filepath and cov_varname to None for stationary GEV.
    dec_mode = str(ds.attrs["december_mode"])
    drop_incomplete_djf = bool(ds.attrs["drop_incomplete_djf"])

    if cov_filepath is not None:
        nonstationary = True
    else:
        nonstationary = False
    
    if nonstationary:
        cov_ds = utilities.load_dataset([cov_filepath])
        if len(cov_ds.time) != len(ds.time):
            start_year = int(ds.time.dt.year[0])
            end_year = int(ds.time.dt.year[-1])
            cov_ds = utilities.slice_dataset(cov_ds,start_year,end_year)

        # Even after slicing, it's possible that time ranges didn't overlap
        if len(cov_ds.time) != len(ds.time):
            print("Covariate timeseries must have same number of years as block extremes dataset.")
            print("Skipping return value calculation.")
            return None,None

        # To numpy array
        cov_ds = cov_ds[cov_varname].data.squeeze()

    lat = len(ds["lat"])
    lon = len(ds["lon"])
    time = len(ds["time"])
    dim2 = lat*lon
    rep_ind = np.ones((time))

    if nonstationary:
        return_value = xr.zeros_like(ds)
    else:
        return_value = xr.zeros_like(ds.isel({"time":0}))
        return_value = return_value.drop(labels=["time"])
    return_value.drop(labels=["lon_bnds","lat_bnds","time_bnds"])
    standard_error = return_value.copy()

    for season in ["ANN","DJF","MAM","JJA","SON"]:
        print("\n-----",season,"-----\n")
        data = ds[season].data
        # Scale x to be around magnitude 1
        scale_factor = np.abs(np.nanmean(data))
        data = data / scale_factor

        if season == "DJF" and dec_mode == "DJF" and drop_incomplete_djf:
            # Step first time index to skip all-nan block
            i1 = 1
        else:
            i1 = 0

        data = np.reshape(data,(time,dim2))
        if cov_filepath is not None:
            rv_array = np.ones(np.shape(data)) * np.nan
        else:
            rv_array = np.ones((1,dim2)) * np.nan
        se_array = rv_array.copy()
        success = np.zeros((dim2))

        # Turn nans to zeros
        data = np.nan_to_num(data)

        if nonstationary:
            cov_slice = cov_ds[i1:]
        else:
            cov_slice = None

        for j in range(0,dim2):
            b=data[i1:,j]
            if np.sum(b) == 0:
                continue
            rv_tmp,se_tmp = calc_rv(data[i1:,j].squeeze(),cov_slice,return_period,1,maxes)
            if rv_tmp is not None:
                rv_array[i1:,j] = rv_tmp*scale_factor
                se_array[i1:,j] = se_tmp*scale_factor
                success[j] = 1

        if nonstationary:
            rv_array = np.reshape(rv_array,(t,lat,lon))
            se_array = np.reshape(se_array,(t,lat,lon))
            success = np.reshape(success,(lat,lon))
            return_value[season] = (("time","lat","lon"),rv_array)
            return_value[season+"_success"] = (("lat","lon"),success)
            standard_error[season] = (("time","lat","lon"),se_array)
            standard_error[season+"_success"] = (("lat","lon"),success)
        else:
            rv_array = np.reshape(rv_array,(lat,lon))
            se_array = np.reshape(se_array,(lat,lon))
            success = np.reshape(success,(lat,lon))
            return_value[season] = (("lat","lon"),rv_array)
            return_value[season+"_success"] = (("lat","lon"),success)
            standard_error[season] = (("lat","lon"),se_array)
            standard_error[season+"_success"] = (("lat","lon"),success)            

    return_value = return_value.bounds.add_missing_bounds() 
    standard_error = standard_error.bounds.add_missing_bounds()

    return return_value,standard_error

def calc_rv(data,covariate,return_period,nreplicates=1,maxes=True):
    # This function contains the code that does the actual return value calculation.
    # Changes to the return value algorithm can be made here.
    # Returns the return value and standard error.
    return_value = None
    standard_error = None
    if covariate is None: # Stationary
        tmp = climextremes.fit_gev(
            data.squeeze(),
            returnPeriod=return_period,
            nReplicates=nreplicates,
            maxes=maxes)
    else: # Nonstationary
        tmp = climextremes.fit_gev(
            data.squeeze(),
            covariate,
            returnPeriod=return_period,
            nReplicates=nreplicates,
            locationFun = 1,
            maxes=maxes,
            xNew=covariate)
    success = tmp['info']['failure'][0]
    if success == 0:
        return_value = tmp['returnValue']
        standard_error = tmp['se_returnValue']
    return return_value,standard_error