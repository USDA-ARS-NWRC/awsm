"""
Distribute thermal long wave using only 1 method

20170731 Micah Sandusky
"""

import smrf
from smrf.utils import queue, io
from threading import Thread
from smrf.envphys import radiation
import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from awsm.interface import ipysnobal
from awsm.interface import interface


def run_smrf_ipysnobal(myawsm):

    # first create config file to run smrf
    fp_smrfini = interface.create_smrf_config(myawsm)

    start = datetime.now()

    if len(sys.argv) > 1:
        configFile = sys.argv[1]

    # initialize
    with smrf.framework.SMRF(fp_smrfini, myawsm._logger) as s:
        # load topo data
        s.loadTopo()

        # 3. initialize the distribution
        s.initializeDistribution()

        # load weather data  and station metadata
        s.loadData()

        # initialize ipysnobal state
        options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(myawsm, s)

        #s.initializeOutput()
        if 'output' in s.thread_variables:
            s.thread_variables.remove('output')
        if not 'isnobal' in s.thread_variables:
            s.thread_variables.append('isnobal')

        # 7. Distribute the data
        # -------------------------------------
        t, q = s.create_distributed_threads()

        # isnobal thread
        t.append(ipysnobal.QueueIsnobal(q, s.date_time,
                                   s.thread_variables,
                                   options,
                                   params,
                                   tstep_info,
                                   init,
                                   output_rec,
                                   s.topo.nx,
                                   s.topo.ny,
                                   myawsm.soil_temp,
                                   myawsm._logger,
                                   myawsm.tzinfo))

        # the cleaner
        t.append(queue.QueueCleaner(s.date_time, q))

        # start all the threads
        for i in range(len(t)):
            t[i].start()

        # wait for all the threads to stop
    #         for v in q:
    #             q[v].join()

        for i in range(len(t)):
            t[i].join()


        s._logger.debug('DONE!!!!')
