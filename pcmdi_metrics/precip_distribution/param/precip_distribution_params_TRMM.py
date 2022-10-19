import datetime
import os

mip = "obs"
dat = "TRMM"
var = "pr"
frq = "day"
ver = "v20220709"

# prd = [2001, 2019]  # analysis period
prd = [1998, 2018]  # analysis period
# fac = 24  # factor to make unit of [mm/day]
fac = 86400  # factor to make unit of [mm/day]
# res = [0.25, 0.25]  # target horizontal resolution [degree] for interporation (lon, lat)
# res = [0.5, 0.5]  # target horizontal resolution [degree] for interporation (lon, lat)
# res = [1, 1]  # target horizontal resolution [degree] for interporation (lon, lat)
res = [2, 2]  # target horizontal resolution [degree] for interporation (lon, lat)
# res = [4, 4]  # target horizontal resolution [degree] for interporation (lon, lat)


indir = "/p/user_pub/PCMDIobs/obs4MIPs/NASA-GSFC/TRMM-3B42v-7/day/pr/1x1/latest/"
infile = "pr_day_TRMM-3B42v-7_PCMDIFROGS_1x1_19980101-20191230.nc"

xmldir = "./xml_obs/"
if not (os.path.isdir(xmldir)):
    os.makedirs(xmldir)
os.system(
    "cdscan -x " + xmldir + var + "." + frq + "." + dat + ".xml " + indir + infile
)

modpath = xmldir
mod = var + "." + frq + "." + dat + ".xml"


case_id = "{:v%Y%m%d}".format(datetime.datetime.now())
pmpdir = "/p/user_pub/pmp/pmp_results/pmp_v1.1.2"
results_dir = os.path.join(
    pmpdir, "%(output_type)", "precip_distribution", "obs", "%(case_id)"
)


ref = "IMERG"  # For Perkins socre, P10, and P90
ref_dir = os.path.join(
    pmpdir, "%(output_type)", "precip_distribution", "obs", "%(case_id)"
)