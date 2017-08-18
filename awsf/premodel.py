'''
Created on Feb 14, 2017

@author: pkormos
'''
import mysql.connector
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'pd.options.mode.chained_assignment = None  # default='warn'
import numpy as np
import ConfigParser as cfp
from datetime import timedelta
import matplotlib.pyplot as plt

def var_get(var,stn,st_time,end_time,tbl): # STN is a list of station id's 
    
#     var = 'precip_accum'
#     stn = 'ATLI1'
#     tbl = 'tbl_level2'
#     end_time = '2017-03-01 00:00:00'
#     st_time  = '2016-12-01 00:00:00'
    
    cnx = mysql.connector.connect(user='pkormos', password='outing',host='10.200.28.137',database='weather_db')
    var_qry = ('SELECT weather_db.%s.date_time, weather_db.%s.%s ' % (tbl,tbl,var) +
                'FROM weather_db.%s ' % tbl +
                "WHERE weather_db.%s.date_time between '" % tbl + st_time+ "' and '"+end_time+"'"
                "AND weather_db.%s.station_id IN ('" % tbl + stn + "');")

    data = pd.read_sql(var_qry, cnx, index_col='date_time')
    return data
  
def var_put(pptdf,stn,tbl):
    # pptdf is a dataframe with only cleaned differenced precip... or data
    # var_name is the column name in the data frame pptdf ('precip_accum')
    # stn is the station name ('DHDI1')
    #     pptdf = cppt0['ARAI1_d']
    #     var_name = 'precip_accum'
    #     stn = 'CCDI1'
    cnx = mysql.connector.connect(user='pkormos', password='outing',host='10.200.28.137',database='weather_db')
    cursor = cnx.cursor()
    VALUES = []
 
    for i in range(np.size(pptdf)):
             
        # the current record
        vi = str(pptdf[i])
        date_time = pptdf.index[i]
         
        # the VALUES part of the insert for each row
        VALUES.append("('%s','%s',%s)" % (stn, date_time.strftime("%Y-%m-%d %H:%M:%S"), vi))
             
    VALUES = ',\n'.join(VALUES)
    add_data = "REPLACE INTO %s (station_id,date_time,precip_accum) VALUES %s" %(tbl,VALUES)
    cursor.execute(add_data)
    cursor.close()
    
def stretch(data,old_low,new_low,old_high,new_high):
    slp = (new_high-new_low)/(old_high-old_low)
    itc = new_low - old_low * slp
    return(data*slp+itc)

    
def precip_corr(pptdf0,bucketDump,recharge,noise):
#     time = dhd_ppt.index
#     pptdf = precipitation dataframe (example, one returned by var_get function above)
#     noise = 2.6
#     bucketDump = 100
#     recharge = 100
#     pptdf0 = ppt0[sta]
    
    pptdf = pd.DataFrame(pptdf0.copy())   # make a deep copy so no referencing to original
    pptdf = pptdf[~pptdf.index.duplicated(keep='first')]
    pptdf.resample('1H')
    
    if np.nansum(pptdf.ix[:,0]>0) == 0: # if there is no precip data over zero,
        return pptdf.ix[:,0]            # pass back original data

    else:
        pptdf['PPT'] = 0.        # create new col in df
        pptdf['CPPT'] = 0.       # create new col in df
        
        # Look for first positive or non noData value, set all previous values to the first value
        finite_vector = np.isfinite(pptdf.ix[:,0])    # common variable of finite values
        tt0 = pptdf.ix[:,0] >= 0 & finite_vector
        tt1 = next((e for e in range(np.size(tt0)) if tt0[e]==True), None)  # get first index of finite and !neg
        pptdf.ix[:tt1+1,0] = pptdf.ix[tt1,0]      # make all earlier vals = to first good one
        N=np.size(pptdf.ix[:,0])   # get number of timesteps
        for i in range(N):              # for each timestep
            if np.isfinite(pptdf.ix[i,0]) == False:     # if you run into an invalid number
                # previous val
                p = next((e for e in np.flipud(np.arange(0,i)) if finite_vector[e]==True), None)
                # next val
                n = i+1
                if i == N or n == N:
                    n = i
                if np.isfinite(pptdf.ix[n,0]) == False:     # if the next value is missing, find the next one that's good.
                    n = next((e for e in np.arange(n,N) if finite_vector[e]==True), N)
                    if n==N:
                        pptdf.ix[p+1:,0] = pptdf.ix[p,0]
                        break
                if pptdf.ix[p,0] - pptdf.ix[n,0] > bucketDump:  # Bucket Dump occured during the unreasonable data values
                    pptdf.ix[p+1:n,0] = pptdf.ix[p,0]
                else:
                    for j in np.arange(p+1,n):
                        pptdf.ix[j,0] = pptdf.ix[p,0] + (j - p) * (pptdf.ix[n,0] - pptdf.ix[p,0]) / (n - p)
        
        # Scan Cycle 1: remove major noise           
        i = 1               # start on timestep 2
        nSucc = 5           # set number of successive values with in noise limit
        while i+nSucc < N:
    #         print 'i is %s and n is %s'%(i,n) #DEBUGLLINEDEBUGLLINEDEBUGLLINEDEBUGLLINEDEBUGLLINEDEBUGLLINEDEBUGLLINEDEBUGLLINEDEBUGLLINE
            if np.abs(pptdf.ix[i-1,0]-pptdf.ix[i,0]) >= noise: # if the the change is above the noise limit
    #             print '%s-%s > noise (%s)' % (pptdf.precip_accum[i-1],pptdf.precip_accum[i],noise) #DEBUGLLINEDEBUGLLINEDEBUGLLINE
                # Variation is greater than noise limit.  It is major noise
                # Find at least 5 succesive values for which variation is
                # within the noise limit
                n = i           # set n equal to time step
                flag = 1        # set flag high
                while flag:
                    
                    d = pptdf.ix[i-1,0] - pptdf.ix[n,0]        # difference from current
                    consDiff = np.array(pptdf.ix[n:n+nSucc,0]) - np.array(pptdf.ix[n+1:n+1+nSucc,0]) # difference for the next 5 measurements
                    if np.sum(np.abs(consDiff) <= noise) == nSucc or 1+n+nSucc == N:
                        flag = 0
                    n = n + 1
                
                if d > bucketDump or d < -recharge: # If it is a bucket dump or bucket recharge event
                    pptdf.PPT[i:n] = 0
                elif np.abs(d) < noise or d > 0:    # Noise Signal: Sudden decrease then comes back to original
                                                    # Make all intermittent pptdf.PPT = 0
                    pptdf.PPT[i:n-1] = 0
                    pptdf.PPT[n] = pptdf.ix[n,0] - pptdf.ix[i-1,0]
                else:                               # Rise in precip may be associated with high intensity
                                                    # precipitation event
                    pptdf.ix[i:n,'PPT'] = np.array(pptdf.ix[i:n,0]) - np.array(pptdf.ix[i-1:n-1,0])
                    
                i = n
                    
            else:   # Not a high magnitude noise
                pptdf.PPT[i] = pptdf.ix[i,0] - pptdf.ix[i-1,0]
                i = i + 1
        ### CALCULATE THE NEW CUMULATIVE PRECIP ###
        #     pptdf.CPPT = np.cumsum(pptdf.PPT)
        #     pptdf.CPPT.plot()
        #     pptdf.precip_accum.plot()
        ### SCANNING CYCLE 2: REMOVES FLUCTUATION DUE TO WIND AND TEMPERATURE. ###
        # modified on 10/5/2005
        # Soothening loop is modified form a one step procedure to a three step procedure
        
        # THE SMOOTHING IS DONE IN THREE STEPS. ONE STARTS FROM THE BEGINING TO END OF CORRECTED
        # INSTANTUOUS PPT ARRAY AFTER SCANNING CYCLE 1, SECOND STARTS FROM THE END TO BEGINING
        # OF CORRECTED INSTANTUOUS PPT ARRAY. WHEN ANY NEGETIVE INSTANTAOUS PPT IS FOUND THEN NEGETIVE
        # VALUE IS UNIFORMLY DISTRIBUTED AT TWO PREVIOUS AND TWO FOLLOWING VALUES IF SUM OF THESE 5 VALUES
        # IS GREATER THEN 0 OTHRWISE RESIDUAL NEGETIVE VELUE IS ASSIGNED TO N+2 VALUE AND ALL THE FOUR
        # VALUES ARE MADE 0.
        
        pptdf['PPT_B'] = pptdf['PPT']
        pptdf['PPT_E'] = pptdf['PPT']
        
        # Smoothening loop that begins with the starting of the file
        if pptdf.PPT_B[0] < 0:
            if pptdf.PPT_B[0] + pptdf.PPT_B[1] > 0:
                pptdf.PPT_B[0:1] = (pptdf.PPT_B[0] + pptdf.PPT_B[1]) / 2
            else:
                pptdf.PPT_B[1] = pptdf.PPT_B[0] + pptdf.PPT_B[1]
                pptdf.PPT_B[0] = 0
                
        for i in np.arange(2,N-2):
            #         a = plt.gca()
            #         i = i+1; i; pptdf.PPT_B[i]; a.vlines(ymin=-10, ymax=25, x=pptdf.index[i], color='g', linewidth = 2); ind = np.arange(i-2,i+3); pptdf.PPT_B[ind]; 
            if pptdf.PPT_B[i] < 0:
                ind = np.arange(i-2,i+3)
                if np.sum(pptdf.PPT_B[ind]) < 0:
                    sm = np.sum(pptdf.PPT_B[ind])    
                    pptdf.PPT_B[ind] = 0
                    pptdf.PPT_B[i+2] = sm
                else:
                    sm = np.sum(pptdf.PPT_B[ind])/5
                    pptdf.PPT_B[ind] = sm
    #     pptdf.PPT_B.plot(style='-r')
    #     np.cumsum(pptdf.PPT_B).plot(style='.g')
        
        # Smoothing that begins form the end of file: added 10/5/05
        if pptdf.PPT_E[N-1] < 0:
            if pptdf.PPT_E[N-1] + pptdf.PPT_E[N-2] > 0:
                pptdf.PPT_E[N-2:N-1] = (pptdf.PPT_E[N-2] + pptdf.PPT_E[N-1]) / 2
            else:
                pptdf.PPT_E[N-2] = pptdf.PPT_E[N-2] + pptdf.PPT_E[N-1]
                pptdf.PPT_E[N-1] = 0
    #     np.cumsum(pptdf.PPT_E).plot(style='-k')
     
        for i in np.flipud(np.arange(2,N-2)): # leave 2 off each end
            if pptdf.PPT_E[i] < 0:
                ind = np.arange(i-2,i+3)
                if np.sum(pptdf.PPT_E[ind]) < 0:
                    sm = np.sum(pptdf.PPT_E[ind])
                    pptdf.PPT_E[ind] = 0
                    pptdf.PPT_E[i-2] = sm
                else:
                    sm = np.sum(pptdf.PPT_E[ind])/5
                    pptdf.PPT_E[ind] = sm
        
        # Taking average of smoothened values
        pptdf.PPT = (pptdf.PPT_B + pptdf.PPT_E) / 2
        pptdf.PPT[0] = 0
        
        if pptdf.PPT[1] < 0:
            pptdf.PPT[1] = 0
        if pptdf.PPT[N-1] < 0:
            pptdf.PPT[N-1] = 0
        if pptdf.PPT[N-2] < 0:
            pptdf.PPT[N-2] = 0
        
        pptdf['CPPTCrr'] = np.cumsum(pptdf.PPT)
        pptdf.CPPTCrr[0] = 0
        
        # get the final time vector
        #     rng = pd.date_range(pptdf.index[0].round('H'),pptdf.index[-1].round('H') , freq='H')
        pptdf = pptdf[~pptdf.index.duplicated(keep='first')]
        pptdf.resample('1H')
        ppt = pd.DataFrame(pptdf.CPPTCrr)
        #     ppt = ppt[~ppt.index.duplicated(keep='first')]    
        #     ppt.to_frame()
        return ppt




# # this one doesn't do the wind rotations and stuff. use ncl script.
# def wrf_download(filename_in,filename_out):
#     from netCDF4 import Dataset
#     from urllib import urlretrieve as ult
#     print filename_in
#     wrfnc = Dataset(filename_in)        # open dataset
#     t = wrfnc.variables['T2']   # pull temp var for shape
#     ntdim = t.shape[0]          # get length of time dimension
#     nydim = t.shape[1]          # get length of north south dimension
#     nxdim = t.shape[2]          # get length of east west dimension
#     wrfnc.close                 # close dataset
# 
#     sT = "Times[0:1:%s]"%(ntdim-1) # build time download string
#     sX = "XLAT[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1) 
#     sY = "XLONG[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1) 
#     sH = "HGT[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1) 
#     sC = "CLDFRA[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1) 
#     sS = "SWDOWN[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     sL = "GLW[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     sTa = "T2[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     # sR = "rh2[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     # sTd = "td2[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     sPr = "RAINNC[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     # sW = "uvmet10[0:1:%s][0:1:%s][0:1:%s]"%(ntdim-1,nydim-1,nxdim-1)
#     
#     url2 = "%s?%s,%s,%s,%s,%s,%s,%s,%s,%s"%(filename_in,sT,sX,sY,sH,sC,sS,sL,sTa,sPr)
#     ult(url2, filename_out)

def ppt_zero(ppt_ts_in): # function to zero precip and take out bucket dumps for plotting
    #     ppt_ts_in = ppt0[sta]
    #     tt0 = np.array(ppt_ts_in.ix[:,0])
    tt0 = np.array(ppt_ts_in)
    tt1 = np.diff(tt0)
    tt1[np.isnan(tt1)] = 0
    ind = np.where(np.abs(tt1)>100)
    ind = ind[0]
    if np.any(ind):
        for i in ind:
            print 'bucket dump is %s' % tt1[int(i)]
            tt0[int(i+1):] = tt0[int(i+1):]-tt1[int(i)]
    ppt_ts_in = tt0 - np.nanmin(tt0)
    return ppt_ts_in

def zro(var_in): # function to zero precip and take out bucket dumps for plotting
    tt0 = np.array(var_in)
    var_in = tt0 - np.nanmin(tt0)
    return var_in

def date2wy(datetime):
    if datetime.month > 9:
        wy = datetime.year+1
    else:
        wy = datetime.year
    return(wy)
        
def wyb(datetime): ### water year beginning year
    if datetime.month > 9:
        wyb = datetime.year
    else:
        wyb = datetime.year-1
    return(wyb)

def wyh2date(wyh,wy): # water year hour to date time, water year
    wyh0 = pd.to_datetime('%s-10-01'%(wy-1))
    time =  wyh0 + pd.to_timedelta(wyh,unit='h')
    return time
   
    
def plot_precip(stations,st_time,end_time,st_time0,tbl_in1,tbl_in2):
    #
    # INPUT: stations: list of station ID's
    #        st_time: start time for new data to be cleaned in 'yyyy-mm-dd HH:MM:SS' format
    #        end_time: end time for new data to be cleaned in 'yyyy-mm-dd HH:MM:SS' format
    #        st_time0: start time for plotting... plotting will go back to this data, but precip correction will not
    #        tbl_in1 level 1 data table, hourly but not cleaned
    #        tbl_in2 level 2 data, cleaned.
    
    from itertools import cycle
    from math import isnan

    # stations = ["FSBC1"]
    #     st_time  = '2016-10-01 00:00:00'
    #     end_time = '2016-10-31 00:00:00'
    #     st_time0  = '2016-10-01 00:00:00'

    ppt02 = pd.DataFrame(index=pd.date_range(st_time0, st_time, freq='H'),columns=stations)  # make dataframe for corrected ppt
    ppt01 = pd.DataFrame(index=pd.date_range(st_time, end_time, freq='H'),columns=stations)  # make dataframe for level 1 ppt
    swe00 = pd.DataFrame(index=pd.date_range(st_time0, end_time, freq='H'),columns=stations)  # make dataframe for ppt
    ppt00 = pd.DataFrame(index=pd.date_range(st_time0, end_time, freq='H'),columns=stations)  # make dataframe for ppt
    cppt0 = pd.DataFrame(index=pd.date_range(st_time, end_time, freq='H'),columns=stations) # make dataframe for corrected ppt
    ttc = ["b","orange","g","r","purple","c","m"]

    fig0 = plt.figure(num=1,figsize=(13,7.5))
    ax01 = fig0.add_axes([.05, .05, .8, .9])
    ttc1 = ttc[:np.size(stations)]
    ccycler = cycle(ttc1)
    for sta in stations:
        c = next(ccycler)
        ppt00[sta] = var_get('precip_accum',sta,st_time0,end_time,tbl_in1)   # pull in level 1 precip for whole time period
        if np.nansum(ppt00[sta]>0) > 0: # if there is no precip data over zero,
            ppt00[sta] = ppt_zero(ppt00[sta])    
            plt.plot(ppt00[sta].index,ppt00[sta],color=c, ls='-.',label='%s orig'%sta)  # plot it in the same color)
    
        ppt02[sta] = var_get('precip_accum',sta,st_time0,st_time,tbl_in2)   # get corrected precip from level 2 data
        if ppt02[sta].any(): 
            ppt02[sta] = np.cumsum(ppt02[sta])
            plt.plot(ppt02[sta].index,ppt02[sta],color=c, ls='-', label='%s prev. corr'%sta) # plot it
            
        swe00[sta] = var_get('snow_water_equiv',sta,st_time0,end_time,tbl_in1) # get swe from level1 data
        if swe00[sta].any(): 
            swe00[sta] = ppt_zero(swe00[sta])
            plt.plot(swe00[sta].index,swe00[sta],color=c, ls='--', label='%s swe'%sta)  # plot it in the same color
            
        ppt01[sta] = var_get('precip_accum',sta,st_time,end_time,tbl_in1)   # get precip from level 1 data
        if ppt01[sta].any():
            ttz = zro(ppt01[sta])
            if np.nansum(ttz>0) >= 0: # if there is precip data over zero,
                ppt01[sta] = ppt_zero(ppt01[sta])
                cppt0[sta] = precip_corr(ppt01[sta],20,80,2.6 )                                # correct precipitation
                if ppt02[sta].any():    
                    plt.plot(ppt01[sta].index,ttz+ppt02[sta][ppt02[sta].last_valid_index()],color = 'c',ls=':',label='%s raw ppt'%sta)  # plot it in the same color)
                    plt.plot(ppt01[sta].index,ppt01[sta]+ppt02[sta][ppt02[sta].last_valid_index()],ls=':',label='%s ppt'%sta)  # plot it in the same color)
                    plt.plot(cppt0[sta].index,cppt0[sta]+ppt02[sta][ppt02[sta].last_valid_index()], color='k', ls=':',label='%s corr. ppt.'%sta) # plot it in the same color
                elif isnan(ppt00[sta][st_time]):
                    plt.plot(ppt01[sta].index,ttz,color = 'c',ls=':',label='%s raw ppt'%sta)  # plot it in the same color)
                    plt.plot(ppt01[sta].index,ppt01[sta],ls=':',label='%s ppt'%sta)  # plot it in the same color)
                    plt.plot(cppt0[sta].index,cppt0[sta], color='k', ls=':',label='%s corr. ppt.'%sta) # plot it in the same color
                else:
                    plt.plot(ppt01[sta].index,ttz+ppt00[sta][st_time],color = 'c',ls=':',label='%s raw ppt'%sta)  # plot it in the same color)
                    plt.plot(ppt01[sta].index,ppt01[sta]+ppt00[sta][st_time],ls=':',label='%s ppt'%sta)  # plot it in the same color)
                    plt.plot(cppt0[sta].index,cppt0[sta]+ppt00[sta][st_time], color='k', ls=':',label='%s corr. ppt.'%sta) # plot it in the same color
    plt.legend(bbox_to_anchor=(1.2,.5), loc='right', ncol=1)                 # plot legend
    plt.vlines(x=st_time,ymin=0,ymax=ax01.get_ylim()[1],color='k',label='start new data')

def diff_plot_put(stations,st_time,end_time,tbl):

    import matplotlib.pyplot as plt
    ppt01 = pd.DataFrame(index=pd.date_range(st_time, end_time, freq='H'),columns=stations)  # make dataframe for level 1 ppt
    cppt0 = pd.DataFrame(index=pd.date_range(st_time, end_time, freq='H'),columns=stations) # make dataframe for corrected ppt

    for j,sta in enumerate(stations,tbl_in,tbl_out):
        ppt01[sta] = var_get('precip_accum',sta,st_time,end_time,tbl_in)   # get precip from level 1 data
        ppt01[sta] = ppt_zero(ppt01[sta])
        cppt0[sta] = precip_corr(ppt01[sta],20,80,2.6 )                                # correct precipitation
        cppt0['%s_d'%sta] = cppt0[sta].diff()               # get incremental ppt        
        cppt0['%s_d'%sta][0]=0                              # fix first diff value = nan
        cppt0['%s_s'%sta] = scale_ppt_vec(cppt0['%s_d'%sta],0.1) # filter and rescale precip.   
        f1 = plt.figure(num=j+10,figsize=(12,7.5))
        ax01 = f1.add_axes([.05, .05, .9, .9])
        ppt01[sta].plot(ax=ax01)
        cppt0[sta].plot(ax=ax01)
        cppt0['%s_d'%sta].plot(ax=ax01)
        cppt0['%s_s'%sta].plot(ax=ax01)
        check = np.cumsum(cppt0['%s_s'%sta])
        check.plot(ax=ax01)
        plt.title(sta)
        var_put(cppt0['%s_s'%sta],sta,tbl_out)  # put corrected data into database

def subplot_spacing(prows,pcols,bot_brd,top_brd,rit_brd,lef_brd,v_space,h_space):
    # le,bo,wi,he = subplot_spacing(prows,pcols,bot_brd,top_brd,rit_brd,lef_brd,v_space,h_space)
    # subplot spacing code by Pat Kormos 8_30_2012, ported to python 4/4/2017
    # le,bo,wi,he = subplot_spacing(prows,pcols,bot_brd,top_brd,rit_brd,lef_brd,v_space,h_space)
    # use following line for easiest use
    # i = 12; subplot('position',[le(i) bo(i) wi he]);
    
    # user defined variables
    #     prows = 3;    # number of subplot rows
    #     pcols = 4;    # number of subplot cols
    #     bot_brd = 0.05; # bottom border
    #     top_brd = .05; # top border
    #     rit_brd = .04; # right border
    #     lef_brd = .05; # left border
    #     v_space = .06; # verticle space between subplots
    #     h_space = .04; # horizontal space between subplots

    # calculated vars
    he = (1-(top_brd+bot_brd+v_space*(prows-1)))/prows # height of subplots
    wi = (1-(lef_brd+rit_brd+h_space*(pcols-1)))/pcols # width of subplots
    x,y = np.meshgrid(range(prows),range(pcols))
    x1 = x.reshape(x.size,1)+1
    le =  lef_brd + y.reshape((y.size,1)) * wi + y.reshape((y.size,1)) * h_space
    le = le.squeeze()
    bo = 1 - top_brd - he * x1 - v_space * x.reshape((x.size,1))
    bo = bo.squeeze()
    return (le,bo,wi,he)
#  
# figure(1); clf
# # set(gcf,'Position',get(0,'Screensize'))
# for i = 1:(prows*pcols)
#     subplot('position',[le(i) bo(i) wi he]);
# end
# 

def stormer(ppt_data,ppt_threshold,time_threshold):
    # returns storm totals, start indexes, and end indexs of storms given mass and time thresholds 
    
    #     ppt_data = ppt0[0:50]
    #     ppt_threshold = 0  # in mm
    #     time_threshold = 4 # in hours
    
    # define storms 
    ind_p = np.zeros(np.size(ppt_data)) # create vector
    ind_p[ppt_data>ppt_threshold] = 1   # times when ppt
    ind_s = np.diff(ind_p)              # 1 when start -1 when end
    st = np.where(ind_s==1)[0] +1       # start indexes
    nd = np.where(ind_s==-1)[0]         # end indexes
    if ppt_data[0] > 0:                 # if the first value has precipitation
        st = np.insert(st,0,0)          # add the start time of zero.

    # get time between storms.  need 2 hours w/out ppt to call storm end
    if st.size>0:
        t = np.zeros(st.size-1)             # preallocate time span mem.
        for i in range(nd.size-1):          # for each end time
            t[i] = st[i+1]-nd[i]-1          # time span is next st time minus previous end time
    
        small_t = np.where(t<time_threshold) # find time between storms less than 2 hours (winstral 2012)
        st = np.delete(st,small_t[0]+1)      # get rid of those start times
        nd = np.delete(nd,small_t[0])        # get rid of those end times
    
    st_tot = np.zeros(nd.size)
    for i in range(nd.size):
        st_tot[i] = ppt_data[st[i]:nd[i]+1].sum() 
    #     plt.plot(ppt_data)
    #     plt.plot(ind_s*.2,'ok')
    #     plt.plot(st,ppt_data[st],'oc')
    #     plt.plot(nd,ppt_data[nd],'om')
    return (st_tot,st,nd)

def stormer3(ppt_data,ppt_threshold,time_threshold): # still in development
    '''
    this function will take a 3d data cube (time,y,x) and conduct the same function as stormer above
    '''
    # returns storm totals, start indexes, and end indexs of storms given mass and time thresholds 
    #     ppt_data = ppt0[0:50]
    #     ppt_threshold = 0  # in mm
    #     time_threshold = 4 # in hours
    
    # define storms 
    ind_p = np.zeros(np.shape(ppt_data)) # create vector
    ind_p[ppt_data>ppt_threshold] = 1   # times when ppt
    ind_s = np.diff(ind_p,axis=0)       # 1 when start -1 when end
    st = np.where(ind_s==1)             # start indexes (need to add one to time dimension)
    st[0][:] = st[0][:]+1
    nd = np.where(ind_s==-1)            # end indexes
    nd[0][:] = nd[0][:]+1
    
    st_tot = np.nan()
    i = 1
    ppt_data[st[0][i]:nd[0][i],st[1][i],st[2][i]]
    
    # get time between storms.  need 2 hours w/out ppt to call storm end
    t = np.zeros(st.size-1)             # preallocate time span mem.
    for i in range(nd.size-1):          # for each end time
        t[i] = st[i+1]-nd[i]-1          # time span is next st time minus previous end time
    
    small_t = np.where(t<time_threshold) # find time between storms less than 2 hours (winstral 2012)
    st = np.delete(st,small_t[0]+1)      # get rid of those start times
    nd = np.delete(nd,small_t[0])        # get rid of those end times
    
    st_tot = np.zeros(nd.size)
    for i in range(nd.size):
        st_tot[i] = ppt_data[st[i]:nd[i]+1].sum() 
    #     plt.plot(ppt_data)
    #     plt.plot(ind_s*.2,'ok')
    #     plt.plot(st,ppt_data[st],'oc')
    #     plt.plot(nd,ppt_data[nd],'om')
    return (st_tot,st,nd)

def densify_strm1d(dpt,ppt):
    '''
    inputs:
    dpt: dew point temp. vector (C)
    ppt: precip vector (mm)
    outputs: 
    density time series
    percent snow time series
    '''
    import numpy as np
    ex_max = 1.75
    exr = 0.75
    ex_min = 1.0
    c1_min = 0.026
    c1_max = 0.069
    c1r = 0.043
    c_min = 0.0067
    cfac = 0.0013
    Tmin = -10.0
    Tmax = 0.0
    Tz = 0.0
    Tr0 = 0.5
    Pcr0 = 0.25
    Pc0 = 0.75
    water = 1000.0

    pcs_0 = np.zeros(np.size(dpt))
    rho_0 = np.zeros(np.size(dpt))
    
    for ts in range(np.size(dpt)):
        # set precipitation temperature, % snow, and SWE
        Tpp = dpt[ts]
        pp = np.sum(ppt)
        if Tpp < Tmin:
            Tpp = Tmin
            tsnow = Tmin
        else :
            if Tpp > Tmax:
                tsnow = Tmax
            else:
                tsnow = Tpp
    
        if Tpp <= -0.5:
            pcs_0[ts] = 1.0
    
        elif Tpp > -0.5 and Tpp <= 0.0:
            pcs_0[ts] = (((-Tpp) / Tr0) * Pcr0) + Pc0
    
        elif Tpp > 0.0 and Tpp <= (Tmax +1.0):
            pcs_0[ts] = (((-Tpp) / (Tmax + 1.0)) * Pc0) + Pc0
    
        else:
            pcs_0[ts] = 0.0
    
        swe = pp * pcs_0[ts] # storm total times percent snow for that time step.
    
        if swe > 0.0:
            # new snow density - no compaction
            Trange = Tmax - Tmin
            ex = ex_min + (((Trange + (tsnow - Tmax)) / Trange) * exr)
    
            if ex > ex_max:
                ex = ex_max
    
            rho_ns = (50.0 + (1.7 * (((Tpp - Tz) + 15.0)**ex))) / water
    
            # proportional total storm mass compaction
            d_rho_c = (0.026 * np.exp(-0.08 * (Tz - tsnow)) * swe * np.exp(-21.0 * rho_ns))
    
            if rho_ns * water < 100.0:
                c11 = 1.0
            else:
                #c11 = np.exp(-0.046 * ((rho_ns * water) - 100.0))
                c11 = (c_min + ((Tz - tsnow) * cfac)) + 1.0
    
            d_rho_m = 0.01 * c11 * np.exp(-0.04 * (Tz - tsnow))
    
            # compute snow denstiy, depth & combined liquid and snow density
            rho_0[ts] = rho_ns +((d_rho_c + d_rho_m) * rho_ns)
    
            zs = swe / rho_0[ts]
    
            if swe < pp:
                if pcs_0[ts] > 0.0:
                    rho = (pcs_0[ts] * rho_0[ts]) + (1 - pcs_0[ts])
                if rho > 1.0:
                    rho = water / water
            else:
                rho = rho_0[ts]
        else:
            rho_ns = 0.0
            d_rho_m = 0.0
            d_rho_c = 0.0
            zs = 0.0
            rho_0[ts] = 0.0
            rho = water / water

    # convert densities from proportions, to kg/m^3 or mm/m^2
    rho_ns *= water
    rho_0[ts] *= water
    rho *= water
    return(rho_0,pcs_0)


def scale_ppt_vec(pptdat,thresh):
    '''
    pptdat = incremental (not cumulative) precipitation data in pandas format
    thresh = precip threshold below which is zeroed and added back into other precip. (in units of original data)
    '''
    fppt0 = pptdat.copy()                        # copy differenced series
    fppt0[fppt0<=thresh] = 0                     # impose threshold (make a function variable)
    ppt_out = fppt0 * (pptdat.sum()/fppt0.sum())
    #print('ratio = %s'%(pptdat.sum()/fppt0.sum()))
    return(ppt_out)

def scale_ppt_mat(pptdata,thresh):
    ppt0_tot_2d = np.sum(pptdata,axis=0)
    ppt_out = pptdata.copy()
    ppt_out[ppt_out<=thresh] = 0                     # impose threshold (make a function variable)
    ppt1_tot_2d = np.sum(ppt_out,axis=0)
    pptfscale_2d = ppt0_tot_2d/ppt1_tot_2d
    ppt_out = ppt_out * pptfscale_2d[np.newaxis, :,:]
    #     plt.plot(pptdata[:,1,1])
    #     plt.plot(fppt0[:,1,1])
    #     plt.plot(fppt[:,1,1])
    #print('ratio = %s'%(pptdat.sum()/fppt0.sum()))
    return(ppt_out)

