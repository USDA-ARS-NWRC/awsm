import numpy as np
import pandas as pd
from awsf.knn import knn

# run knn

sql_user = {'user':'micahsandusky',
            'password':'B3rj3r+572',
            'host':'10.200.28.137',
            'database':'weather_db',
            'port':'32768'}

# fpath = '/data/blizzard/awsftest/weatherGenerator_warmwet/'
fpath = '/data/blizzard/awsftest/febWeather/regular/'
add_temp = 0.0
mult_precip = 1.0

#start_date = pd.to_datetime('2017-07-18')
#end_date = pd.to_datetime('2017-07-29')
start_date = pd.to_datetime('2017-02-14')
end_date = pd.to_datetime('2017-02-25')
scen_num = 20
# scen_num = 2

print('writing to {} for {}'.format(fpath, start_date))
knn.do_knn(None, fpath, sql_user, start_date, end_date, scen_num, add_temp, mult_precip)
