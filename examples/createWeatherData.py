import numpy as np
import pandas as pd
from awsf.knn import knn

# run knn
fpath = '../test_data/weatherGenerator/'
knn.do_knn(None, fpath)

# next steps
# run instance of awsf...
