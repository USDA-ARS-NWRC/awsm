
For configuration file syntax information please visit http://inicheck.readthedocs.io/en/latest/


awsm master
-----------

| **model_type**
| 	Model used to simulate snowpack for given time period. Choose None if not running model
| 		*Default: None*
| 		*Type: string*
| 		*Options:*
 *none smrf_ipysnobal ipysnobal*
| 

| **run_smrf**
| 	Specifies whether or not to run SMRF to distribute forcing data.
| 		*Default: False*
| 		*Type: bool*
| 


paths
-----

| **basin**
| 	name of basin to run. i.e. tuolumne or brb. No spaces please
| 		*Default: None*
| 		*Type: string*
| 

| **folder_date_style**
| 	style of date that gets appended to generated folders for each date range that is simulated
| 		*Default: start_end*
| 		*Type: string*
| 		*Options:*
 *day start_end*
| 

| **path_dr**
| 	path to starting drive for AWSM directory structure. This path MUST exist
| 		*Default: None*
| 		*Type: criticaldirectory*
| 

| **project_description**
| 	project description that will be stored in text file in project directory. You cannot use punctuation here because config readers cannot deal with that
| 		*Default: None*
| 		*Type: string*
| 

| **project_name**
| 	name of project that will be used in directory structure. No spaces please.
| 		*Default: None*
| 		*Type: string*
| 


awsm system
-----------

| **daily_folders**
| 	seperate daily output folders. Used mainly for shortterm forecasts
| 		*Default: False*
| 		*Type: bool*
| 

| **log_level**
| 	level of information to be logged
| 		*Default: debug*
| 		*Type: string*
| 		*Options:*
 *debug info error*
| 

| **log_to_file**
| 	log to auto generated file or print to screen
| 		*Default: True*
| 		*Type: bool*
| 

| **netcdf_output_precision**
| 	NetCDF variable output precision for float (32-bit) or double (64-bit)
| 		*Default: float*
| 		*Type: string*
| 		*Options:*
 *float double*
| 

| **output_frequency**
| 	frequency of snow model outputs in hours. This is sepreate from SMRF
| 		*Default: 24*
| 		*Type: int*
| 

| **run_for_nsteps**
| 	number of timesteps to run iSnobal. This is optional and mainly used in model crash scenarios
| 		*Default: None*
| 		*Type: int*
| 


update depth
------------

| **buffer**
| 	number of buffer cells for update interpolation of variables
| 		*Default: 400*
| 		*Type: int*
| 

| **flight_numbers**
| 	list of flight number integers to use. Integers start at 1. Default uses all within date range
| 		*Default: None*
| 		*Type: int*
| 

| **update**
| 	should we update depth with LiDAR at given intervals
| 		*Default: False*
| 		*Type: bool*
| 

| **update_change_file**
| 	optional file to save the changes in swe depth and density resulting from a depth update
| 		*Default: None*
| 		*Type: filename*
| 

| **update_file**
| 	netCDF containing depth images and dates for updating
| 		*Default: None*
| 		*Type: discretionarycriticalfilename*
| 


isnobal restart
---------------

| **depth_thresh**
| 	threshold in meters for depth to be removed upon restart. This can help with shallow snowpack that causes crashes
| 		*Default: 0.05*
| 		*Type: float*
| 

| **output_folders**
| 	let the restart procedure know where to look for the previous outputs. If standard then it looks in the same directory but it may look in the previous day output if daily
| 		*Default: standard*
| 		*Type: string*
| 		*Options:*
 *standard daily*
| 

| **restart_crash**
| 	whether or not to restart iSnobal from crashed run
| 		*Default: False*
| 		*Type: bool*
| 

| **wyh_restart_output**
| 	last iSnobal output wyhr. Program will look at output files to find output state at this wyhr for restart
| 		*Default: None*
| 		*Type: int*
| 


ipysnobal
---------

| **active_layer**
| 	height of iSnobal active layer in meters
| 		*Default: 0.25*
| 		*Type: float*
| 

| **init_file**
| 	init file containing model state to initialize snow model
| 		*Default: None*
| 		*Type: filename*
| 

| **init_type**
| 	type of file for initializing model
| 		*Default: None*
| 		*Type: string*
| 		*Options:*
 *none netcdf netcdf_out*
| 

| **ithreads**
| 	numbers threads for running snow model
| 		*Default: 1*
| 		*Type: int*
| 

| **mask_isnobal**
| 	Mask snowpack model output.
| 		*Default: False*
| 		*Type: bool*
| 

| **max_h2o**
| 	maximum volumetric content of liquid water in the snowpack
| 		*Default: 0.01*
| 		*Type: float*
| 

| **output_file_name**
| 	name of the output file
| 		*Default: ipysnobal*
| 		*Type: string*
| 

| **restart_date_time**
| 	Restart iPysnobal at this date time which will keep the output in the same project and run directory. This will be the first time step that iPysnobal will perform.
| 		*Default: None*
| 		*Type: datetime*
| 

| **thresh_medium**
| 	medium mass threshold for timestep refinement within iSnobal
| 		*Default: 10*
| 		*Type: int*
| 

| **thresh_normal**
| 	normal mass threshold for timestep refinement within iSnobal
| 		*Default: 60*
| 		*Type: int*
| 

| **thresh_small**
| 	small mass threshold for timestep refinement within iSnobal
| 		*Default: 1*
| 		*Type: int*
| 

| **variables**
| 	Output variables for Pysnobal
| 		*Default: thickness snow_density specific_mass liquid_water temperature_surface temperature_lower temperature_snowcover thickness_lower water_saturation net_radiation sensible_heat latent_heat snow_soil precip_advected sum_energy_balance evaporation snowmelt surface_water_input cold_content*
| 		*Type: string*
| 		*Options:*
 *thickness snow_density specific_mass liquid_water temperature_surface temperature_lower temperature_snowcover thickness_lower water_saturation net_radiation sensible_heat latent_heat snow_soil precip_advected sum_energy_balance evaporation snowmelt surface_water_input cold_content*
| 

| **z_g**
| 	depth of soil temperature data in meters
| 		*Default: 0.5*
| 		*Type: float*
| 

| **z_t**
| 	height of temperature data in meters
| 		*Default: 5.0*
| 		*Type: float*
| 

| **z_u**
| 	height of wind speed data in meters
| 		*Default: 5.0*
| 		*Type: float*
| 

