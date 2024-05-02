import glob
import os
import sys
from typing import Union

import xarray as xr
import xcdat as xc
import xmltodict


def xcdat_open(
    infile: Union[str, list], data_var: str = None, decode_times: bool = True
) -> xr.Dataset:
    """Open input file (netCDF, or xml generated by cdscan)

    Parameters
    ----------
    infile : Union[str, list]
        list of string, or string, for path of file(s) to open using xcdat
    data_var : str, optional
        key of the non-bounds data variable to keep in the Dataset, alongside any existing bounds data variables, by default None, which loads all data variables
    decode_times : bool, optional
        If True, attempt to decode times encoded in the standard NetCDF datetime format into cftime.datetime objects. Otherwise, leave them encoded as numbers. This keyword may not be supported by all the backends, by default True

    Returns
    -------
    xr.Dataset
        xarray dataset opened via xcdat

    Usage
    -----
    >>> from pcmdi_metrics.io import xcdat_open
    # Open a single netCDF file
    >>> ds = xcdat_open('mydata.nc')
    # Open multiple files
    >>> ds2 = xcdat_open(['mydata1.nc', 'mydata2.nc']  # Open multipe netCDF files
    # Open with specifing the variable 'ts'
    >>> ds3 = xcdat_open(['mydata1.nc', 'mydata2.nc'], data_var='ts')
    # Open an xml file
    >>> ds = xcdat_open('mydata.xml')
    """
    if isinstance(infile, list):
        ds = xc.open_mfdataset(infile, data_var=data_var, decode_times=decode_times)
    else:
        if infile.split(".")[-1].lower() == "xml":
            ds = xcdat_openxml(infile, data_var=data_var, decode_times=decode_times)
        else:
            ds = xc.open_dataset(infile, data_var=data_var, decode_times=decode_times)

    return ds.bounds.add_missing_bounds()


def xcdat_openxml(
    xmlfile: str, data_var: str = None, decode_times: bool = True
) -> xr.Dataset:
    """Open input file (xml generated by cdscan)

    Parameters
    ----------
    infile: str
        path of xml file to open using xcdat
    data_var: str, optional
        key of the non-bounds data variable to keep in the Dataset, alongside any existing bounds data variables, by default None, which loads all data variables
    decode_times : bool, optional
        If True, attempt to decode times encoded in the standard NetCDF datetime format into cftime.datetime objects. Otherwise, leave them encoded as numbers. This keyword may not be supported by all the backends, by default True

    Returns
    -------
    xr.Dataset
        xarray dataset opened via xcdat
    """
    if not os.path.exists(xmlfile):
        sys.exit(f"ERROR: File not exist: {xmlfile}")

    with open(xmlfile, encoding="utf-8") as fd:
        doc = xmltodict.parse(fd.read())

    ncfile_list = glob.glob(os.path.join(doc["dataset"]["@directory"], "*.nc"))

    if len(ncfile_list) > 1:
        ds = xc.open_mfdataset(
            ncfile_list, data_var=data_var, decode_times=decode_times
        )
    else:
        ds = xc.open_dataset(
            ncfile_list[0], data_var=data_var, decode_times=decode_times
        )

    return ds
