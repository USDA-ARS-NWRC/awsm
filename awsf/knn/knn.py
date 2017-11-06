"""
K nearest neighbor approach to generating weather data based on
the paper Yates et al 2003. This is only for testing and will
be integrated into AWSF or SMRF

Scott Havens 20171016
"""

import pandas as pd
import numpy as np
from scipy import linalg
import matplotlib.pyplot as plt
import mysql.connector
import os

def wind_dir_resampler(array):
    """Wind direction resample from componenents"""
    return np.mean(array)

conversion = {
        'air_temp': np.mean,
        'dew_point_temperature': np.mean,
        'relative_humidity': np.mean,
        'wind_speed': np.mean,
        'wind_direction': np.mean,
        'wind_gust': np.mean,
        'solar_radiation': np.mean,
        'snow_smoothed': np.mean,
        'precip_accum': np.sum,
        'precip_intensity': np.sum,
        'snow_depth': np.max,
        'snow_interval': np.max,
        'snow_water_equiv': np.max,
        'vapor_pressure': np.mean,
        'cloud_factor': np.mean
    }

model_keys = ['air_temp', 'cloud_factor', 'precip_intensity', 'vapor_pressure', 'wind_speed', 'wind_direction',
              'solar_radiation', 'precip_accum']
#model_keys = ['air_temp', 'precip_accum', 'vapor_pressure'] # for a quick comparison

def organize_data(df, resample=None, smooth=False):
    """
    Take a dataframe that contains all the data for every station
    and organize into a dict for each variable containing the station
    data.
    """

    DF = {}
    station_ids = df.station_id.unique()
    for v in model_keys:
#         print('    Creating dataframe for {}'.format(v))

        # create an empty dataframe
        dp = pd.DataFrame(index=df.index.unique(), columns=station_ids)
        dp.index.name = 'date_time'
        for s in station_ids:
            dp[s] = df.loc[df['station_id'] == s, v].copy()

        # remove columns with all nan
        dp.dropna(axis=1, how='all', inplace=True)

        if smooth:
            pass

        # resample here
        if resample is not None:
            dp = dp.resample(resample).apply(conversion[v])

        DF[v] = dp

    return DF

def get_data(start_date, end_date, sql_user, w=14, resample='1D'):

    cnx = mysql.connector.connect(user=sql_user['user'],
                                  password=sql_user['password'],
                                  host=sql_user['host'],
                                  database=sql_user['database'],
                                  port=sql_user['port'])

    # get the station id's
    qry = "SELECT tbl_metadata.* FROM tbl_metadata INNER JOIN tbl_stations_view ON tbl_metadata.primary_id=tbl_stations_view.primary_id WHERE client='TUOL_2017'"
    d = pd.read_sql(qry, cnx, index_col='primary_id')

    # select the data from tbl_level2
    sta = "','".join(d.index)

    # save metadata
    d_meta = d.copy()
    # check to see if UTM locations are calculated
    d_meta['X'] = d_meta['utm_x']
    d_meta['Y'] = d_meta['utm_y']

    ww = '{}D'.format(np.ceil(w/2))
    sd = start_date - pd.to_timedelta(ww)
    ed = end_date + pd.to_timedelta(ww)

    qry = """SELECT * FROM tbl_level2
         WHERE DATE_FORMAT(date_time,'%m-%d') BETWEEN '{0}' AND '{1}' AND
         station_id IN ('{2}') ORDER BY date_time ASC""".format(
            sd.strftime('%m-%d'), ed.strftime('%m-%d'), sta)

    # loads all the data
    print('Reading database')
    d = pd.read_sql(qry, cnx, index_col='date_time')

    if d.empty:
        raise Exception('No data found in database')

    # Fill returned values 'None' with NaN
    d = d.fillna(value=np.nan, axis='columns')

    cnx.close()

    print('Parsing data')

    # now we need to parse the data frame into stations
    DF = None
    sta = d.station_id.unique()
    for s in sta:
        idx = d.station_id == s
        dp = d[idx].copy()

        df = pd.DataFrame()
        df['air_temp_max'] = dp['air_temp'].resample(resample).max()
        df['air_temp_min'] = dp['air_temp'].resample(resample).min()
        df['precip_accum'] = dp['precip_accum'].resample(resample).sum()
        df['vapor_pressure_max'] = dp['vapor_pressure'].resample(resample).max()
        df['vapor_pressure_min'] = dp['vapor_pressure'].resample(resample).min()

        df.dropna(axis=1, how='all', inplace=True)
        df.dropna(axis=0, how='all', inplace=True)

        if not df.empty:
            df['station_id'] = s

            if DF is None:
                DF = df.copy()
            else:
                DF = pd.concat([DF, df])

    return DF, d, d_meta


def create_weather(data, t, w=14):
    """
    Create random weather using the data for the period
    between the start_date and end_date

    This follows Yates et al 2003
    """

    print('Creating weather, muh ha ha ha!!')

    N = len(data.index.year.unique())
    K = np.max([np.ceil(np.sqrt((w + 1) * N - 1)).astype(int), 15])

    ww = '{}day'.format(np.ceil(w/2))

    # Step 5: Get the intial date to start which will be the basis of the weather
    xbar = data.loc[data.index == t[0], :]
    F_t = {}
    F_t[t[0]] = t[0]

    # Step 8: Probability metric with a weight function
    den = np.sum([1/i for i in range(1, K)])
    p_j = np.array([1/j for j in range(1, K)]) / den

    data['dt'] = data.index.strftime('%m-%d')

    for i, ti in enumerate(t[1:], 1):
#         print(ti)

        # Step 1: get all the measurements for the given time and get the regional min
        xbar_t = xbar.mean()

        # Step 2: Retrieve all days within the time window to get the potential t+1 day
        sd = ti - pd.to_timedelta(ww)
        ed = ti + pd.to_timedelta(ww)

        ind = (data.dt >= sd.strftime('%m-%d')) & (data.dt <= ed.strftime('%m-%d'))
        step2 = data.loc[ind, :]

        # Step 3: Get the regional mean for all potential days
        # window around the current time
        tw = pd.date_range(sd, ed, freq=t.freq)
        xbar_i = pd.DataFrame(columns=xbar_t.keys())
        for twi in tw:
            xbar_i.loc[twi, :] = data.loc[data.index == twi, :].mean()

        # Step 4: Compute the covariance matrix from all the data within the window from Step 2
        S_t = step2.cov()

        # Step 6: Mahalanobis distances between the mean vector of current F_t[t] and xbar_i
        # The calculation of d_i was adapted from scikit-learn
        S_t_inv = linalg.pinvh(S_t)
        centered_obs = (xbar_t - xbar_i).as_matrix().astype(float)
        d_i = np.sqrt(np.sum(np.dot(centered_obs, S_t_inv) * centered_obs, 1))

        d_i = pd.DataFrame(d_i, index=xbar_i.index, columns=['d'])

        # Step 7: Sort d_i and retain the first K-nearest neighbors
        knn = d_i.sort_values(by='d').iloc[1:K]

        # Step 9: Select t+1 day using the probability metric p_j
        u = np.random.uniform()
        idx = np.argmin(np.abs(p_j - u))

        tp1 = knn.index[idx]
        F_t[ti] = tp1

        print('    {}'.format(tp1))

        xbar = data.loc[data.index == tp1, :]


    return F_t

def construct_senario(data, days, resample='3h'):
    """
    Take the data and randomly generated senario and
    reconstruct the resampled senario
    """

    data['date'] = data.index.date
    data['time'] = data.index.time

    df = None
    for ti,di in days.items():

        # find the random day di in the data
        d_org = data.loc[data['date'] == di.date(), :].copy()

        # Change the date to the new date ti
        d_org['date'] = ti.date()
        d_org['date_time'] = d_org.apply(lambda r: pd.datetime.combine(r['date'], r['time']),1)
        d_org.set_index('date_time', inplace=True)

        # create a new dataframe that contains all the random data
        if df is None:
            df = d_org.copy()
        else:
            df = pd.concat([df, d_org])

    del df['id']
    del df['date']
    del df['time']

    # now we need to parse the data frame
    DF = organize_data(df, resample=resample, smooth=False)

    return DF

def do_knn(myawsf, fpath, sql_user, start_date, end_date, scen_num, add_temp, mult_precip):

    resample = '1D'
    w = 20

    t = pd.date_range(start_date, end_date, freq=resample)

    data, all_data, d_meta = get_data(start_date, end_date, sql_user, w, resample)
    org_data = organize_data(all_data)

    # loop through and create a bunch of random weather senarios
    D = []
    for i in range(scen_num):
        print('Scenario {}'.format(i))
        dd = create_weather(data, t, w=w)

        # from the data construct the new wether sequence
        s = construct_senario(all_data, dd, '3h')

        s['precip_intensity'] = s['precip_accum'].copy()

        # perturb results
        s['air_temp'] = s['air_temp'] + add_temp
        s['precip_intensity'] = s['precip_intensity'] * mult_precip

        s['precip_accum'] = s['precip_accum'].cumsum()
        D.append(s)

    # make directory for each scenario and output station data to csv
    for j, DD in enumerate(D):
        # '/data/blizzard/awsftest/tuolumne/devel'
        #fpath = './weatherdata/scenario'
        # output directory
        dir_out = os.path.join(fpath, 'scenario_{}'.format(j))
        # metadata name
        meta_out = os.path.join(dir_out, 'metadata.csv')
        # create
        if not os.path.exists(dir_out):
            os.makedirs(dir_out)
            print('Making {} scenario data'.format(j))
        else:
            raise ValueError('Path {} exists'.format(dir_out))

        for v in model_keys:
            #if v != 'precip_accum':
                # file for each variable
                fp_out = os.path.join(dir_out, '{}.csv'.format(v))
                m = DD[v]
                # output file to csv
                m.to_csv(fp_out, na_rep='NaN')
                # output metadata to csv
                d_meta.to_csv(meta_out)

    print('Done')
