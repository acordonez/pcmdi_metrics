import os

#import cdms2
#import cdtime
import MV2
import numpy as np

from datetime import datetime

from pcmdi_metrics.mjo.lib import (
    Remove_dailySeasonalCycle,
    calculate_ewr,
    generate_axes_and_decorate,
    get_daily_ano_segment,
    #interp2commonGrid,
    interp2commonGrid_xcdat,
    output_power_spectra,
    space_time_spectrum,
    #subSliceSegment,
    subSliceSegment_xcdat,
    #unit_conversion,
    write_netcdf_output,
)

from .debug_chk_plot import debug_chk_plot
from .plot_wavenumber_frequency_power import plot_power

from pcmdi_metrics.io import xcdat_open, get_time, get_latitude, get_longitude, get_time_key
from pcmdi_metrics.utils import adjust_units


def mjo_metric_ewr_calculation(
    mip,
    model,
    exp,
    run,
    debug,
    plot,
    nc_out,
    cmmGrid,
    degX,
    UnitsAdjust,
    inputfile,
    data_var: str,
    startYear: int,
    endYear: int,
    segmentLength: int,
    dir_paths: str,
    season: str="NDJFMA",
):
    # Open file to read daily dataset
    if debug:
        print("debug: open file")
    #f = cdms2.open(inputfile)
    #d = f[data_var]
    ds = xcdat_open(inputfile)
    
    #tim = d.getTime()
    #comTim = tim.asComponentTime()
    #lat = d.getLatitude()
    #lon = d.getLongitude()
    
    #tim = get_time(ds)
    lat = get_latitude(ds)
    lon = get_longitude(ds)

    # Get starting and ending year and month
    if debug:
        print("debug: check time")
        
    #first_time = comTim[0]
    #last_time = comTim[-1]
    
    time_key = get_time_key(ds)
    first_time = ds.indexes[time_key].to_datetimeindex()[0].to_pydatetime()
    last_time = ds.indexes[time_key].to_datetimeindex()[-1].to_pydatetime()    

    if season == "NDJFMA":
        # Adjust years to consider only when continuous NDJFMA is available
        """
        if first_time > cdtime.comptime(startYear, 11, 1):
            startYear += 1
        if last_time < cdtime.comptime(endYear, 4, 30):
            endYear -= 1
        """
        if first_time > datetime(startYear, 11, 1):
            startYear += 1
        if last_time < datetime(endYear, 4, 30):
            endYear -= 1
        
    # Number of grids for 2d fft input
    #NL = len(d.getLongitude())  # number of grid in x-axis (longitude)
    NL = len(lon.values)  # number of grid in x-axis (longitude)
    if cmmGrid:
        NL = int(360 / degX)
    NT = segmentLength  # number of time step for each segment (need to be an even number)

    if debug:
        # endYear = startYear + 2
        print("debug: startYear, endYear:", startYear, endYear)
        print("debug: NL, NT:", NL, NT)

    #
    # Get daily climatology on each grid, then remove it to get anomaly
    #
    if season == "NDJFMA":
        mon = 11
        numYear = endYear - startYear
    elif season == "MJJASO":
        mon = 5
        numYear = endYear - startYear + 1
    day = 1
    # Store each year's segment in a dictionary: segment[year]
    segment = {}
    segment_ano = {}
    #daSeaCyc = MV2.zeros((NT, d.shape[1], d.shape[2]))
    daSeaCyc = np.zeros((NT, ds[data_var].shape[1], ds[data_var].shape[2]))
    
    # Loop over years
    for year in range(startYear, endYear):
        print(year)
        #segment[year] = subSliceSegment(d, year, mon, day, NT)
        segment[year] = subSliceSegment_xcdat(ds, year, mon, day, NT)
        # units conversion
        #segment[year] = unit_conversion(segment[year], UnitsAdjust)
        segment[year][data_var] = adjust_units(segment[year][data_var], UnitsAdjust)
        # Get climatology of daily seasonal cycle
        #daSeaCyc = MV2.add(MV2.divide(segment[year], float(numYear)), daSeaCyc)
        daSeaCyc = np.add(np.divide(segment[year][data_var].values, float(numYear)), daSeaCyc)
        
    # Remove daily seasonal cycle from each segment
    if numYear > 1:
        # Loop over years
        for year in range(startYear, endYear):
            #segment_ano[year] = Remove_dailySeasonalCycle(segment[year], daSeaCyc)
            segment_ano[year] = segment[year] - daSeaCyc
    else:
        segment_ano[year] = segment[year]
    
    # Assign lat/lon to arrays
    # daSeaCyc.setAxis(1, lat)
    # daSeaCyc.setAxis(2, lon)
    # segment_ano[year].setAxis(1, lat)
    # segment_ano[year].setAxis(2, lon)
    
    # -----------------------------------------------------------------
    # Space-time power spectra
    # -----------------------------------------------------------------
    # Handle each segment (i.e. each year) separately.
    # 1. Get daily time series (3D: time and spatial 2D)
    # 2. Meridionally average (2D: time and spatial, i.e., longitude)
    # 3. Get anomaly by removing time mean of the segment
    # 4. Proceed 2-D FFT to get power.
    # Then get multi-year averaged power after the year loop.
    # -----------------------------------------------------------------

    # Define array for archiving power from each year segment
    Power = np.zeros((numYear, NT + 1, NL + 1), np.float)

    # Year loop for space-time spectrum calculation
    if debug:
        print("debug: year loop start")
    for n, year in enumerate(range(startYear, endYear)):
        print("chk: year:", year)
        d_seg = segment_ano[year]
        # Regrid: interpolation to common grid
        if cmmGrid:
            #d_seg = interp2commonGrid(d_seg, degX, debug=debug)
            d_seg = interp2commonGrid_xcdat(d_seg, degX, debug=debug)
        # Subregion, meridional average, and remove segment time mean
        d_seg_x_ano = get_daily_ano_segment(d_seg)
        # Compute space-time spectrum
        if debug:
            print("debug: compute space-time spectrum")
        Power[n, :, :] = space_time_spectrum(d_seg_x_ano)

    # Multi-year averaged power
    Power = np.average(Power, axis=0)
    # Generates axes for the decoration
    Power, ff, ss = generate_axes_and_decorate(Power, NT, NL)
    # Output for wavenumber-frequency power spectra
    OEE = output_power_spectra(NL, NT, Power, ff, ss)

    # E/W ratio
    ewr, eastPower, westPower = calculate_ewr(OEE)
    print("ewr: ", ewr)
    print("east power: ", eastPower)
    print("west power: ", westPower)

    # Output
    output_filename = f"{mip}_{model}_{exp}_{run}_mjo_{startYear}-{endYear}_{season}"
    if cmmGrid:
        output_filename += "_cmmGrid"

    # NetCDF output
    if nc_out:
        os.makedirs(dir_paths["diagnostic_results"], exist_ok=True)
        fout = os.path.join(dir_paths["diagnostic_results"], output_filename)
        write_netcdf_output(OEE, fout)

    # Plot
    if plot:
        os.makedirs(dir_paths["graphics"], exist_ok=True)
        fout = os.path.join(dir_paths["graphics"], output_filename)
        if model == "obs":
            title = f"OBS ({run})\n{data_var.capitalize()}, {season} {startYear}-{endYear}"
        else:
            title = f"{mip.upper()}: {model} ({run})\n{data_var.capitalize()}, {season} {startYear}-{endYear}"

        if cmmGrid:
            title += ", common grid (2.5x2.5deg)"
        plot_power(OEE, title, fout, ewr)

    # Output to JSON
    metrics_result = {
        "east_power": eastPower,
        "west_power": westPower,
        "east_west_power_ratio": ewr,
        "analysis_time_window_start_year": startYear,
        "analysis_time_window_end_year": endYear,
    }

    # Debug checking plot
    if debug and plot:
        debug_chk_plot(
            d_seg_x_ano, Power, OEE, segment[year], daSeaCyc, segment_ano[year]
        )

    #f.close()
    ds.close()
    return metrics_result
