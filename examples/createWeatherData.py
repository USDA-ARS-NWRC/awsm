import numpy as np
import pandas as pd
from awsf.knn import knn

# run knn

sql_user = {'user':'micahsandusky',
            'password':'B3rj3r+572',
            'host':'10.200.28.137',
            'database':'weather_db',
            'port':'32768'}

fpath = '/data/blizzard/awsftest/weatherGenerator/'

start_date = pd.to_datetime('2017-07-18')
end_date = pd.to_datetime('2017-07-29')
scen_num = 100

knn.do_knn(None, fpath, sql_user, start_date, end_date, scen_num)

# next steps
# run instance of awsf...
