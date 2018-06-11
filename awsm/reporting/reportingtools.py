import pandas as pd
import numpy as np
from smrf import ipw
import matplotlib.pyplot as plt
import os
import sys
import seaborn as sns
from netCDF4 import Dataset
from smrf.utils import utils
# import reporting module if installed
try:
    import snowav
except:
    print('No snowav to import, not installed')

def plot_dashboard(myawsm):
    """
    Function to plot summary information and make reports after an AWSM run
    """

    # initialize reporting tool
    myawsm._logger.info('Plotting summary information as requested')
    snow = snowav.plotting.framework.SNOWAV(config_file = myawsm.report_config,
                                            external_logger=myawsm._logger)

    if not hasattr(snow,'error'):
        # process and plot the data
        snow.process()
        snowav.plotting.accumulated.accumulated(snow)
        snowav.plotting.current_image.current_image(snow)
        snowav.plotting.state_by_elev.state_by_elev(snow)
        snowav.plotting.image_change.image_change(snow)
        snowav.plotting.basin_total.basin_total(snow)
        snowav.plotting.pixel_swe.pixel_swe(snow)
        snowav.plotting.density.density(snow)
        snowav.plotting.water_balance.water_balance(snow)
        snowav.plotting.stn_validate.stn_validate(snow)
        # If options exist in config file
        if hasattr(snow,'flt_flag'):
            snowav.plotting.flt_image_change.flt_image_change(snow)

        snowav.plotting.write_summary.write_summary(snow,'accum')
        snowav.plotting.write_summary.write_summary(snow,'state')
        # snowav.plotting.basin_detail.basin_detail(snow)

        if snow.report_flag == True:
            myawsm._logger.info('Creating report')
            snowav.report.report.report(snow)


def plot_waterbalance(myawsm):
    """
    Function to plot the mass balance after an AWSM run has completed
    """

    u = myawsm.u
    v =  myawsm.v
    du = myawsm.du
    dv = myawsm.dv
    nx = myawsm.nx
    ny = myawsm.ny
    pixel = np.abs(du)

    run_dir = myawsm.pathro
    path_ppt = myawsm.ppt_desc

    mask = ipw.IPW(myawsm.fp_mask).bands[0].data
    numpix = np.sum(mask)

    # get precip from ipw
    header = ['hour', 'path']
    df_ppt = pd.read_csv(path_ppt, names = header, sep = ' ')

    # Paths to the snow and em files
    run_files   = sorted(os.listdir(run_dir))

    # If we are setting a subrange within the directory, just grab those

    em_files    = [value for value in run_files if 'em' in value]
    snow_files    = [value for value in run_files if 'snow' in value]

    # Get full domain SWI and then apply masks
    swi         = np.zeros((ny,nx))

    myawsm._logger.info('Grabbing snow and em for plotting')
    # Go through the files...
    for iters,(ename,sname) in enumerate(zip(em_files,snow_files)):

        em_file = ipw.IPW('%s%s'%(run_dir,ename))
        snow_file = ipw.IPW('%s%s'%(run_dir,sname))

        # Initialize total and daily, and then add up over the run
        if iters == 0:
            swi     = np.zeros((ny,nx))
            swi_day = np.zeros(len(em_files))
            swi     = swi + em_file.bands[8].data

            swe     = np.zeros((ny,nx))
            swe_day = np.zeros(len(snow_files))
            swe = snow_file.bands[2].data

            evap     = np.zeros((ny,nx))
            evap_day = np.zeros(len(em_files))
            evap = evap + em_file.bands[6].data

        else:
            swi = swi + em_file.bands[8].data
            swe = snow_file.bands[2].data
            evap = evap + em_file.bands[6].data

        swi_day[iters] = sum(sum(np.multiply(swi,mask)))
        swe_day[iters] = sum(sum(np.multiply(swe,mask)))
        evap_day[iters] = sum(sum(np.multiply(evap,mask)))

    # Convert to acre-ft
    swi_day = np.divide(swi_day,numpix)
    swe_day = np.divide(swe_day,numpix)
    evap_day = np.divide(evap_day,numpix)

    sum_snow = swi_day + swe_day - evap_day

    # find ranges and dates
    startdate = myawsm.start_date.replace(tzinfo=myawsm.tzinfo)

    tt = myawsm.end_date-myawsm.start_date
    tdiff = tt.days*24 +  tt.seconds//3600 # number of timesteps
    offset = utils.water_day(startdate)[0]
    # print(offset)
    # print(tdiff)
    day_hr = range(int(offset+23), int(tdiff+offset+23), int(24))

    ppt_hr = df_ppt['hour'].values
    ppt_desc = df_ppt['path'].values
    # make ppt arraymyawsf.fp_mask
    #ppt_m = np.zeros(ppt_hr[-1])
    ppt_m = np.zeros(int(tdiff+offset))

    myawsm._logger.info('Grabbing precip for plotting')

    for fp, hr in zip(ppt_desc, ppt_hr):
        # read in file
        tmp_ppt = ipw.IPW(fp).bands[0].data
        ppt_sum = np.sum(np.multiply(tmp_ppt,mask))
        ppt_m[hr] = ppt_sum

    # cumulative ppt_m
    ppt_m = np.divide(np.cumsum(ppt_m), numpix)

    # print('Getting smrf precip')
    # # get precip stuff
    # smppt_ds =         Dataset(path_smrf_ppt,'r')
    # smppt_spatial = smppt_ds.variables['precip'][:]
    # smppt_spatial = np.multiply(smppt_spatial,mask)
    # smppt = np.sum(smppt_spatial, axis=(1,2))
    # smppt = np.cumsum(np.divide(smppt,numpix))
    # time = smppt_ds.variables['time'][:]

    #hr_hr = time
    # Plot it up!
    myawsm._logger.info('Plotting mass balance')
    plt.figure(2)

    sns.set_style('darkgrid')
    sns.set_context("notebook")

    plt.plot(day_hr,swi_day, label='swi')
    plt.plot(day_hr,swe_day, label = 'swe')
    plt.plot(day_hr,-1.0*evap_day, label = 'evap')
    plt.plot(day_hr,sum_snow, label = 'sum snow')
    #plt.plot(smppt, label = 'smrf precip')
    plt.plot(ppt_m, label = 'ppt4b precip')
    plt.legend()
    plt.show()
