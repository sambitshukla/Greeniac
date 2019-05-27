# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 10:42:41 2018

@author: sambit
"""

class Const:
    "List of Simultaion Constants"

    SIMULATION_TIME = 500.001
    DELTA_TIME = 0.001
    LONG_SLEEP_TIME = 10000000000
    LONG_DELAY = 10000000000
    
    MAX_QSIZE = 10000000
    DEF_QSIZE = 1000000
    MAX_TASKQ_LEN = 4
    
    MAX_ARRIVAL_RATE = 299
    ARRIVAL_RATE = 100.0 #packets per second
    SERVICE_TIME = 0.037 #time based on 3GHz
    TAIL_LATENCY_SLO = 1.0 #10.000    #500ms per tail latency target (Application specific)
    TAIL_Px_TARGET = 95
    MIN_SERVICE_TIME = SERVICE_TIME / 10
    MAX_SERVICE_TIME = SERVICE_TIME * 4
    
    # (-0.28875, 0.8)
    LOGNORMAL_MEAN = 0
    LOGNORMAL_STDDEV = 0.25

    CPU_BASE_SERVICE_RATE = 3000.0    #Freq at which service time is calculated
    BIG_TO_SMALL_SLOWDOWN = 0.66    #Speedup of Big core over small core at 1200 MHz, Big service time / Small service time
    
    SL_LOAD_BIN = 5.0  # SLAgent bucket with every n req/sec increments
    NUM_SL_SAMPLES = 10
    CL_LOAD_BIN = 1.0  # CLAgent bucket with every n req/sec increments
    NUM_CL_SAMPLES = 1
    
    NUM_SERVERS = 2
    NUM_ACTIVE_SERVERS = 1
    
    RESP_AGGREGATION_INTERVAL = 5.0   # aggregate response every 1 second
    SL_SAMPLING_EPOCH = 500.0   # calculate tail latency and make decisions
    CL_SAMPLING_EPOCH = 500.0   # calculate tail latency and make decisions
    DEF_SAMPLING_EPOCH = 100.0   # calculate tail latency and make decisions
    MAX_LOAD_PER_EPOCH = DEF_SAMPLING_EPOCH * MAX_ARRIVAL_RATE  #TODO: Not exceed 20000 to allow learning and avoid mem running out on kelewan
    
    INACTIVE_SERVER_POWER_CONSIDERED = False
    NON_CPU_SERVER_POWER_CONSIDERED = False
    DVFS_ENABLED = False
    CUSTOM_CORE_TASK_SCHEDULING = False

    TEST_SIM1_RUN = False

    DEBUG_CORE = 0
    DEBUG_QUEUE = 0
    DEBUG_REQGEN = 0
    DEBUG_CLMONITOR = 0
    DEBUG_TSCHED = 0
    DEBUG_LDBALANCER = 0
    DEBUG_RESPAGGR = 0
    DEBUG_GREENMGR = 1
    DEBUG_SLAGENT = 1
    DEBUG_CLAGENT = 1
    DEBUG_RLAGENT = 1
    DEBUG = 0
    DEBUG_DETAILED = 0
    DEBUG_WARN = 0
    DEBUG_INIT = 0
    DEBUG_TEST = 0
    SIMPY_HEAP_FIX = 1
    
    ATOM_STR = 'atom'
    XEON1_STR = 'xeon1'
    XEON2_STR = 'xeon2'

    if (DVFS_ENABLED):
        CPU_FREQ_PROFILES = {ATOM_STR: (800.0, 1000.0, 1200.0),
                             XEON1_STR: (1200.0, 1600.0, 1900.0, 2200.0, 2600.0, 2900.0, 3200.0),
                             XEON2_STR: (1200.0, 1500.0, 1800.0, 2100.0)
                             }
    
    # power profiles (static_pwr_sleep_enabled, dynamic_pwr_at_max_util ....)
        CPU_POWER_PROFILES = {ATOM_STR: (0.7, 1.4, 1.8, 2.15),
                             XEON1_STR: (10.0, 6.88, 7.74, 9.05, 10.5, 12.15, 13.64, 15.92),
                             XEON2_STR: (11.0, 10.03, 12.23, 15.10, 18.34)
                             }
        
    elif not TEST_SIM1_RUN:
        CPU_FREQ_PROFILES = {ATOM_STR: [1200.0],
                             XEON1_STR: [3200.0],
                             XEON2_STR: [2100.0]
                             }
    
        CPU_POWER_PROFILES = {ATOM_STR: (0.7, 2.15),
                             XEON1_STR: (10.0, 15.92),
                             XEON2_STR: (11.0, 18.34)
                             }
        
    elif TEST_SIM1_RUN:
        CPU_FREQ_PROFILES = {ATOM_STR: [3000.0],
                             XEON1_STR: [3000.0],
                             XEON2_STR: [3000.0]
                             }
    
        CPU_POWER_PROFILES = {ATOM_STR: (1, 4),
                             XEON1_STR: (8, 16),
                             XEON2_STR: (8, 16)
                             }
        
#    NON_CPU_SERVER_POWER_PROFILES = [30, 30, 30, 30]   #Medium EP
    NON_CPU_SERVER_POWER_PROFILES = [15, 15, 15, 15]    #High EP
    
# DEFINE THE Cluster Configuration HERE
    CPU_NAME_LIST = [ATOM_STR, XEON1_STR, XEON2_STR]
    if (TEST_SIM1_RUN):
        NUM_SERVERS = 4
        CORE_COUNT_MATRIX = [[1, 1, 0]]*NUM_SERVERS
#        NUM_SERVERS = 4
#        CORE_COUNT_MATRIX = [[2, 0, 0], [2, 0, 0], [0, 2, 0], [0, 2, 0]]
#        NUM_SERVERS = 2
#        CORE_COUNT_MATRIX = [[2, 0, 0], [0, 2, 0]]
    else:
#        CORE_COUNT_MATRIX = [[1, 1, 0]]*NUM_SERVERS
        CORE_COUNT_MATRIX = [[2, 2, 0]]*NUM_SERVERS
    STATIC_LOAD_RATIO = [1]*NUM_SERVERS
    CORE_MASK_LIST = [0, 1, 2]
