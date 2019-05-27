# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 22:45:56 2018

@author: sambit
"""

import Const
import numpy as np

# Single Tail Latency Monitoring Thread
class ClusterMonitor(object):
#    __slots__ = ('env', 'csRespQ', 'serverList', 'totalEnergyUsageCurrEpoch', 'reqGenThread', 'lbThread', 'allServerPSConfigsList', 'aspsValidConfigsList', \
#                 'rlLogic', 'iterCount', 'slAgentList', 'aspsValidConfigsEnergyList', 'aspsValidConfigsTputList', 'aspsValidConfigsEfficiencyList', \
#                 'testSim', 'slLearning', 'clLearning', 'fullSim', 'allServerQTable', 'CQTable', 'clAgent')
    def __init__(self, env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList, rlLogic):
        self.env = env
        self.csRespQ = csRespQ
        self.serverList = serverList
        self.totalEnergyUsageCurrEpoch = 0
        self.reqGenThread = rgt
        self.lbThread = lbt
        self.allServerPSConfigsList = allServerPwrSortedConfigsList
        self.aspsValidConfigsList = []
        self.rlLogic = rlLogic
        self.iterCount = 0
        self.slAgentList = []
        self.aspsValidConfigsEnergyList = []
        self.aspsValidConfigsTputList = []
        self.aspsValidConfigsEfficiencyList = []
        
        self.samplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.pxLat = 0
        self.respCount = 0
        self.energyMonitoringEnabled = False
        
        
    def run(self):
        if Const.DEBUG_INIT: print("TailLatencyMonitor thread started")
        yield self.env.timeout(0.01)
        while True:
            yield self.env.timeout(self.samplingEpoch)
            self.collectLatencyStat()
            if self.energyMonitoringEnabled: 
                self.collectEnergyStat()
            self.csRespQ.reqQueue[0:self.respCount] = []
            

    def resetServerSamplingStats(self, server):
        server.respAggregator.energyUsagePerSampEpoch = 0
        for core in server.coreList.coreList:
            if core.active == 1:
                if Const.DEBUG: print("Total service time of core {} server {} in last epoch = {:.3f}".format(core.cid, server.sid, core.currSampEpochServiceTime))
            core.currSampEpochServiceTime = 0
            core.reqsProcessedLastEpoch = 0
            
                        
    def collectLatencyStat(self):
        if Const.DEBUG_TLMONITOR: print("TailLatency being calculated for last epoch")
        self.respCount = self.csRespQ.getCurrentQlen()
        if Const.DEBUG_TLMONITOR: print("{} Response received in last {} secs".format(self.csRespQ.getCurrentQlen(), self.samplingEpoch))
        respLatencyList = []
        for i in range(self.respCount):
            respLatencyList.append(self.csRespQ.reqQueue[i].responseLatency)
        self.pxLat = np.percentile(np.array(respLatencyList), Const.TAIL_Px_TARGET)
        del respLatencyList


    def collectEnergyStat(self):
        epochReqCount = self.reqGenThread.getEpochReqCount()
        reqTput = float(self.respCount) / self.samplingEpoch
        reqLoad = float(epochReqCount) / self.samplingEpoch
        energyUsageForCurrClusterConfig = 0
        
        for sid in range(Const.NUM_SERVERS):
            server = self.serverList.getServer(sid)
            server.energyUsageLastEpoch = server.respAggregator.energyUsagePerSampEpoch
            server.avgPowerLastEpoch = float(server.energyUsageLastEpoch) / self.samplingEpoch
            energyUsageForCurrClusterConfig += server.energyUsageLastEpoch
            if Const.DEBUG_TLMONITOR: print("For Server {}, Last Epoch Energy = {:.3f}, Power = {:.3f}".format(sid, server.energyUsageLastEpoch, server.avgPowerLastEpoch))
            self.resetServerSamplingStats(server)
            
        if Const.DEBUG_TLMONITOR: print("PxLat = {:.3f}, Energy = {:.3f} for {} / {} packets in {} secs".format(self.pxLat, energyUsageForCurrClusterConfig, reqTput, reqLoad, self.samplingEpoch))
        self.serverList.energyUsageLastEpoch = energyUsageForCurrClusterConfig
        self.serverList.avgPowerLastEpoch = float(energyUsageForCurrClusterConfig) / self.samplingEpoch

            