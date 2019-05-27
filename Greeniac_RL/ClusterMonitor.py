# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 22:45:56 2018

@author: sambit
"""

import numpy as np
import simpy

from Const import Const

# Single Tail Latency Monitoring Thread
class ClusterMonitor(object):
#    __slots__ = ('env', 'csRespQ', 'serverList', 'totalEnergyUsageCurrEpoch', 'reqGenThread', 'lbThread', 'allServerPSConfigsList', 'aspsValidConfigsList', \
#                 'manager', 'iterCount', 'slAgentList', 'aspsValidConfigsEnergyList', 'aspsValidConfigsTputList', 'aspsValidConfigsEfficiencyList', \
#                 'testSim', 'slLearning', 'clLearning', 'fullSim', 'allServerQTable', 'CQTable', 'clAgent')
    def __init__(self, env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList, manager):
        self.env = env
        self.csRespQ = csRespQ
        self.samplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.pxLat = 0
        self.meanLat = 0
        self.pxSvcTime = 0
        self.pxQTime = 0
        self.respCount = 0
        self.manager = manager
        self.action = self.env.process(self.run())
        self.halt = 0
        
        
    def run(self):
        if Const.DEBUG_INIT: print("ClusterMonitor thread started")
        yield self.env.timeout(Const.DELTA_TIME)
        while True:
            if (self.halt == 1):
                try:
                    if Const.DEBUG_CLMONITOR: print("ClusterMonitor thread halting")
                    yield self.env.timeout(Const.LONG_SLEEP_TIME)
                except simpy.Interrupt:
                    if Const.DEBUG_CLMONITOR: print("ClusterMonitor thread resuming")
                    yield self.env.timeout(Const.DELTA_TIME)
            try:
                if Const.DEBUG_CLMONITOR: print("ClusterMonitor thread sleeping for ", self.samplingEpoch)
                yield self.env.timeout(self.samplingEpoch)
            except simpy.Interrupt:
                if Const.DEBUG_CLMONITOR: print("ClusterMonitor thread interrupted while sleeping")
                continue

            self.collectLatencyStat()
            self.csRespQ.reqQueue[0:self.respCount] = []
            
            #Inform Greeniac Manager
            if (self.manager != None):
                self.manager.action.interrupt()
                self.samplingEpoch = self.manager.nextSamplingEpoch
            
            
    def collectLatencyStat(self):
        if Const.DEBUG_CLMONITOR: print("TailLatency being calculated for last epoch")
        self.respCount = self.csRespQ.getCurrentQlen()
        if Const.DEBUG_CLMONITOR: print("{} Response received in last {} secs".format(self.csRespQ.getCurrentQlen(), self.samplingEpoch))
        respLatencyList = []
        serviceTimeList = []
        queueTimeList = []
        for i in range(self.respCount):
            req = self.csRespQ.reqQueue[i]
            respLatencyList.append(req.responseLatency)
            serviceTimeList.append(req.serviceTime)
            queueTimeList.append(req.responseLatency - req.serviceTime)
        self.pxLat = np.percentile(np.array(respLatencyList), Const.TAIL_Px_TARGET)
        self.pxSvcTime = np.percentile(np.array(serviceTimeList), Const.TAIL_Px_TARGET)
        self.pxQTime = np.percentile(np.array(queueTimeList), Const.TAIL_Px_TARGET)
        self.meanLat = np.mean(np.array(respLatencyList))
        del respLatencyList
        del serviceTimeList
        del queueTimeList
            