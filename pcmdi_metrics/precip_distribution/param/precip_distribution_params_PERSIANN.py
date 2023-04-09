import datetime
import os

mip = "obs"
dat = "PERSIANN"
var = "pr"
frq = "day"
ver = "v20230407"

# prd = [2001, 2019]  # analysis period
prd = [1984, 2018]  # analysis period
fac = 86400  # factor to make unit of [mm/day]
# res = [0.25, 0.25]  # target horizontal resolution [degree] for interporation (lon, lat)
# res = [0.5, 0.5]  # target horizontal resolution [degree] for interporation (lon, lat)
# res = [1, 1]  # target horizontal resolution [degree] for interporation (lon, lat)
res = [2, 2]  # target horizontal resolution [degree] for interporation (lon, lat)
# res = [4, 4]  # target horizontal resolution [degree] for interporation (lon, lat)

modpath = "/p/user_pub/PCMDIobs/obs4MIPs/NOAA/PERSIANN-CDRv1r1/day/pr/1x1/latest/"
mod = "pr_day_PERSIANN-CDRv1r1_PCMDIFROGS_1x1_19830102-20190101.nc"

case_id = "{:v%Y%m%d}".format(datetime.datetime.now())
# case_id = ver
pmpdir = "/p/user_pub/pmp/pmp_results/pmp_v1.1.2"
results_dir = os.path.join(pmpdir, "%(output_type)", "precip", "%(mip)", "%(case_id)", "intensity.frequency_distribution")

ref = "IMERG-V06-FU"  # For Perkins socre, P10, and P90
ref_dir = os.path.join(pmpdir, "%(output_type)", "precip", "obs", "%(case_id)", "intensity.frequency_distribution")
