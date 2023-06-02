#!/usr/bin/env python
from pcmdi_metrics.mean_climate.lib import pmp_parser

def create_extremes_parser():

    parser = pmp_parser.PMPMetricsParser()
    parser.add_argument(
        "--case_id",
        dest="case_id",
        help="Defines a subdirectory to the metrics output, so multiple"
        + "cases can be compared",
        required=False,
    )

    parser.add_argument(
        "-v",
        "--vars",
        type=str,
        nargs="+",
        dest="vars",
        help="Variables to use",
        required=False,
    )
    
    parser.add_argument(
        "-r",
        "--reference_data_set",
        default = None,
        type=str,
        nargs="+",
        dest="reference_data_set",
        help="List of observations or models that are used as a "
        + "reference against the test_data_set",
        required=False,
    )

    parser.add_argument(
        "--reference_data_path",
        default = None,
        dest="reference_data_path",
        help="Path for the reference climitologies",
        required=False,
    )
    parser.add_argument(
        "--reference_sftlf_template",
        default = None,
        dest="reference_sftlf_template",
        help="Path for the reference sftlf file",
        required=False,
    )

    parser.add_argument(
        "-t",
        "--test_data_set",
        type=str,
        nargs="+",
        dest="test_data_set",
        help="List of observations or models to test "
        + "against the reference_data_set",
        required=False,
    )

    parser.add_argument(
        "--test_data_path",
        dest="test_data_path",
        help="Path for the test climitologies",
        required=False,
    )

    parser.add_argument(
        "--realization",
        dest="realization",
        help="A simulation parameter",
        required=False,
    )

    parser.add_argument(
        "--dry_run",
        # If input is 'True' or 'true', return True. Otherwise False.
        type=lambda x: x.lower() == "true",
        dest="dry_run",
        help="True if output is to be created, False otherwise",
        required=False,
    )

    parser.add_argument(
        "--filename_template",
        dest="filename_template",
        help="Template for climatology files",
        required=False,
    )

    parser.add_argument(
        "--sftlf_filename_template",
        dest="sftlf_filename_template",
        help='Filename template for landsea masks ("sftlf")',
        required=False,
    )

    parser.add_argument(
        "--metrics_output_path",
        dest="metrics_output_path",
        default=None,
        help="Directory of where to put the results",
        required=False,
    )

    parser.add_argument(
        "--filename_output_template",
        dest="filename_output_template",
        help="Filename for the interpolated test climatologies",
        required=False,
    )

    parser.add_argument(
        "--output_json_template",
        help="Filename template for results json files",
        required=False,
    )

    parser.add_argument(
        "--user_notes",
        dest="user_notes",
        help="Provide a short description to help identify this run of the PMP mean climate.",
        required=False,
    )

    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Turn on debugging mode by printing more information to track progress",
        required=False,
    )

    parser.add_argument(
        "--cmec",
        dest="cmec",
        action="store_true",
        help="Save metrics in CMEC format",
        required=False,
    )

    parser.add_argument(
        "--no_cmec",
        dest="cmec",
        action="store_false",
        help="Option to not save metrics in CMEC format",
        required=False,
    )    

    parser.add_argument(
        "--chunk_size",
        dest="chunk_size",
        default=None,
        help="Chunk size for latitude/longitude",
        required=False
    )

    parser.add_argument(
        "--annual_strict",
        dest="annual_strict",
        action="store_true",
        help="Flag to only include current year in rolling data calculations"
    )

    parser.add_argument(
        "--exclude_leap_day",
        dest="exclude_leap",
        action="store_true",
        help="Flag to exclude leap days"
    )

    parser.add_argument(
        "--keep_incomplete_djf",
        dest="drop_incomplete_djf",
        action="store_false",
        help="Flag to include data from incomplete DJF seasons"
    )

    parser.add_argument(
        "--dec_mode",
        dest="dec_mode",
        default="DJF",
        help="'DJF' or 'JFD' format for December/January/February season"
    )

    parser.add_argument(
        "--nc_out",
        type=bool,
        default=True,
        help="Option for generate netCDF file output: True (default) / False",
    )

    parser.add_argument(
        "--year_range",
        type=list,
        default=[None, None],
        help="List containing the start and end year"
    ),
    parser.add_argument(
        "--covariate_path",
        type=str,
        default=None,
        help="Covariate file path"
    )
    parser.add_argument(
        "--covariate",
        type=str,
        default="CO2mass",
        help="Covariate variable name"
    )

    parser.add_argument(
        "--shp_path",
        type=str,
        default=None,
        help="Region shapefile path. Must also provide --column and --region_name. Only one of --shp_path, --coords can be used.",
        required=False
    )

    parser.add_argument(
        "--attribute",
        type=str,
        default=None,
        help="Name of region attribute column in shapefile",
        required=False
    )
    parser.add_argument(
        "--region_name",
        type=str,
        default=None,
        help="Name of region. If from shapefile, value must be found under attribute given by --column",
        required=False
    )

    parser.add_argument(
        "--coords",
        type=list,
        default=None,
        help="List of coordinates for region bounds. Must be provided in consecutive order around shape perimeter. Only one of --shp_path, --coords can be used.",
        required=False
    )

    parser.add_argument(
        "--generate_sftlf",
        type=bool,
        default=False,
        help="Flag to generate land sea mask if not found.",
        required=False
    )

    parser.add_argument(
        "--regrid",
        type=bool,
        default=True,
        help="Set to False if model and reference data all use same grid.",
        required=False
    )

    parser.add_argument(
        "--plots",
        type=bool,
        default=False,
        help="Set to True to generate figures.",
        required=False
    )

    return parser