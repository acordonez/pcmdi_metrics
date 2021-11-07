from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
import cartopy.crs as ccrs
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import sys


def plot_map(mode, model, syear, eyear, season, eof_Nth, frac_Nth, output_file_name):
    # Map Projection
    if "teleconnection" in mode:
        # projection = "PlateCarree"
        projection = "Robinson"
    elif mode in ["NAO", "PNA", "NPO", "PDO", "NPGO"]:
        projection = "Lambert"
    elif mode in ["NAM"]:
        projection = "Stereo_north"
    elif mode in ["SAM"]:
        projection = "Stereo_south"
    else:
        sys.exit('Projection for ' + mode + 'is not defined.')

    # title
    if frac_Nth != -999:
        percentage = (
            str(round(float(frac_Nth * 100.0), 1)) + "%"
        )  # % with one floating number
    else:
        percentage = ""

    plot_title = (
        mode
        + ": "
        + model
        + "\n"
        + str(syear)
        + "-"
        + str(eyear)
        + " "
        + season
        + " "
        + percentage
    )

    if mode == 'PNA' and projection == "Lambert":
        gridline = False
    else:
        gridline = True

    if "PDO" in mode or "NPGO" in mode:
        levels = [r/10 for r in list(range(-5, 6, 1))]
    else:
        levels = list(range(-5, 6, 1))

    plot_map_cartopy(eof_Nth, output_file_name, title=plot_title, proj=projection,
                     gridline=gridline, levels=levels)


def plot_map_cartopy(
    data, filename, title=None, gridline=True, levels=None,
    proj='PlateCarree', data_area='global', 
    cmap='RdBu_r',
    debug=False):
    """
    Parameters
    ----------
    data : trainsisent variable
        2D cdms2 TransientVariable with lat/lon coordinates attached.
    filename : str
        Output file name (it is okay to omit '.png')
    title : str, optional
        Figure title
    gridline : bool
        Show grid lines (default is True)
    levels : list
        List of numbers for colormap levels (optional)
    proj : str
        Map projection: PlateCarree (default), Robinson, Stereo_north, Stereo_south, Lambert
    data_area : str
        Spatial coverage area of data: global (default), regional
    cmap : str
        Matplotlib colormap name. See https://matplotlib.org/stable/gallery/color/colormap_reference.html for available options
    debug: bool
        Switch for debugging print statements (default is False)
    """
    
    lons = data.getLongitude()
    lats = data.getLatitude()
    
    min_lon = min(lons)
    max_lon = max(lons)
    min_lat = min(lats)
    max_lat = max(lats)
    if debug:
        print(min_lon, max_lon, min_lat, max_lat)
    
    ''' map types:
    https://github.com/SciTools/cartopy-tutorial/blob/master/tutorial/projections_crs_and_terms.ipynb
    '''
    if proj == 'PlateCarree':
        projection = ccrs.PlateCarree(central_longitude=180)
    elif proj == 'Robinson':
        projection = ccrs.Robinson(central_longitude=180)
    elif proj == 'Stereo_north':
        projection = ccrs.NorthPolarStereo()
    elif proj == 'Stereo_south':
        projection = ccrs.SouthPolarStereo()
    elif proj == 'Lambert':
        max_lat = min(max_lat, 80)
        if debug:
            print('revised maxlat:', max_lat)
        central_longitude = (min_lon + max_lon) / 2.
        central_latitude = (min_lat + max_lat) / 2.
        """
        projection = ccrs.LambertConformal(
            central_longitude=central_longitude, 
            cutoff=min_lat)
        projection = ccrs.LambertAzimuthalEqualArea(
            central_longitude=central_longitude,
            central_latitude=central_latitude)
        """
        projection = ccrs.AlbersEqualArea(
            central_longitude=central_longitude,
            central_latitude=central_latitude,
            standard_parallels=(20, max_lat))

    # Generate plot
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=projection)
    im = ax.contourf(lons, lats, data, 
                     transform=ccrs.PlateCarree(), 
                     cmap=cmap,
                     levels=levels,
                     extend='both')
    ax.coastlines()

    # Grid Lines and tick labels
    if proj == 'PlateCarree':
        if data_area == 'global':
            if gridline:
                gl = ax.gridlines(alpha=0.5, linestyle='--')
            ax.set_xticks([0, 60, 120, 180, 240, 300, 360], crs=ccrs.PlateCarree())
            ax.set_yticks([-90, -60, -30, 0, 30, 60, 90], crs=ccrs.PlateCarree())
            lon_formatter = LongitudeFormatter(zero_direction_label=True)
            lat_formatter = LatitudeFormatter()
            ax.xaxis.set_major_formatter(lon_formatter)
            ax.yaxis.set_major_formatter(lat_formatter)
        else:
            if gridline:
                gl = ax.gridlines(draw_labels=True, alpha=0.5, linestyle='--')
    elif proj == 'Robinson':
        if gridline:
            gl = ax.gridlines(alpha=0.5, linestyle='--')
    elif 'Stereo' in proj:
        if gridline:
            gl = ax.gridlines(draw_labels=True, alpha=0.5, linestyle='--')
            gl.xlocator = mticker.FixedLocator(
                np.concatenate([np.arange(-180, -89, 30), np.arange(-90, 181, 30)]))
            gl.xformatter = LONGITUDE_FORMATTER
            gl.xlabel_style = {'size': 12, 'color': 'k','rotation':0}
            gl.yformatter = LATITUDE_FORMATTER
            if 'north' in proj:
                ax.set_extent([-180, 180, 0, 90], crs=ccrs.PlateCarree())
                gl.ylocator = mticker.FixedLocator(np.arange(20, 90, 20), 200)
            elif 'south' in proj:
                ax.set_extent([-180, 180, -90, 0], crs=ccrs.PlateCarree())
                gl.ylocator = mticker.FixedLocator(np.arange(-90, -20, 20), 200)
        # Compute a circle in axes coordinates, which we can use as a boundary
        # for the map. We can pan/zoom as much as we like - the boundary will be
        # permanently circular.
        # https://scitools.org.uk/cartopy/docs/v0.15/examples/always_circular_stereo.html
        theta = np.linspace(0, 2*np.pi, 100)
        center, radius = [0.5, 0.5], 0.4
        verts = np.vstack([np.sin(theta), np.cos(theta)]).T
        circle = mpath.Path(verts * radius + center)
        ax.set_boundary(circle, transform=ax.transAxes)
    elif proj == 'Lambert':
        if gridline:
            gl = ax.gridlines(draw_labels=True, alpha=0.5, linestyle='--')
            gl.top_labels = False   # suppress top labels
            gl.right_labels = False   # suppress top labels
        # Make a boundary path in PlateCarree projection, I choose to start in
        # the bottom left and go round anticlockwise, creating a boundary point
        # every 1 degree so that the result is smooth:
        # https://stackoverflow.com/questions/43463643/cartopy-albersequalarea-limit-region-using-lon-and-lat
        vertices = [(lon, min_lat) for lon in range(int(min_lon), int(max_lon+1), 1)] + \
                   [(lon, max_lat) for lon in range(int(max_lon), int(min_lon-1), -1)]
        boundary = mpath.Path(vertices)
        ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
        ax.set_boundary(boundary, transform=ccrs.PlateCarree())

    # Add title
    plt.title(title, pad=15, fontsize=15)

    # Add colorbar
    posn = ax.get_position()
    cbar_ax = fig.add_axes([0, 0, 0.1, 0.1])
    cbar_ax.set_position([posn.x0 + posn.width + 0.025, posn.y0,
                          0.02, posn.height])
    cbar = plt.colorbar(im, cax=cbar_ax)
    cbar.ax.tick_params(labelsize=12) 

    if proj == 'PlateCarree':
        ax.set_aspect('auto', adjustable=None)
    
    # Done, save figure
    fig.savefig(filename)