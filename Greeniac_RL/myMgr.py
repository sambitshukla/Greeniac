#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 15:19:06 2019

@author: sambit
"""

import simpy
import sys

from Const import Const
import helper as hlp
from heapq import heapify

import objgraph
import inspect
import resource

# Simulation Orchestrator thread
class TestManager(object):
    def __init__(self, env, csRespQ, serverList, rgt, lbt, allServerPSConfigsList):
        self.env = env
        self.csRespQ = csRespQ
        self.lbThread = lbt
        self.serverList = serverList
        self.reqGenThread = rgt
        self.samplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.respCount = 0
        self.clMonitor = None
        self.action = self.env.process(self.run())
        self.arrivalRate = 0
        self.bigCoreServiceTime = 0
        self.allServerPSConfigsList = allServerPSConfigsList
        
    def run(self):
        if Const.DEBUG_INIT: print("Test Manager started for cluster")
        print("Simulation started")
        
        minRate = 0.025
        maxRate = 1.0
        rateIncr = 0.025
        bigCoreServiceRate = maxRate * (1.0/3.0) / 2
#        bigCoreServiceRate = maxRate * (5.0/12.0)
        bigCoreServiceTime = 1/bigCoreServiceRate
        smallCoreServiceRateRatio = 1.0 / 2
#        smallCoreServiceRateRatio = 0.2
        px = 95
        epochPkts = 100000.0

        Const.MAX_TASKQ_LEN = 1
        Const.ARRIVAL_RATE = 100.0 #packets per second
        Const.SERVICE_TIME = bigCoreServiceTime
        Const.TAIL_Px_TARGET = px
        Const.DEF_SAMPLING_EPOCH = 100000.0
        Const.RESP_AGGREGATION_INTERVAL = 500.0
        Const.DVFS_ENABLED = False
        Const.CPU_BASE_SERVICE_RATE = 3000
        Const.BIG_TO_SMALL_SLOWDOWN = smallCoreServiceRateRatio

        self.reqGenThread.setReqTaskSizeType("exp")
        self.reqGenThread.setArrivalPattern("poisson")
        self.lbThread.configTputInfoAvailable = False
        self.lbThread.setLbAlgorithm("ratio")
        Const.STATIC_LOAD_RATIO = [2.0, 2.0, 4.0, 4.0]
#        Const.STATIC_LOAD_RATIO = [2.0, 4.0]
#        Const.STATIC_LOAD_RATIO = [3.0]*Const.NUM_SERVERS
        
        clusterCfgList = [1, []]*Const.NUM_SERVERS
        for sid in range(Const.NUM_SERVERS):
            clusterCfgList[sid*2] = 1
            clusterCfgList[(sid*2)+1] = self.allServerPSConfigsList[sid][-1]
            self.serverList.getServer(sid).serverReqQ.maxQlen = Const.MAX_QSIZE
            self.serverList.getServer(sid).taskSched.schedAlgo = "fcfs-small"
        self.serverList.activateServersAndCores(clusterCfgList)

        self.arrivalRate = minRate
        self.reqGenThread.setArrivalRate(self.arrivalRate)
        self.samplingEpoch = epochPkts/self.arrivalRate
        self.clMonitor.samplingEpoch = self.samplingEpoch
            
        i = 0
        for self.arrivalRate in hlp.frange(minRate + rateIncr, maxRate + rateIncr, rateIncr):
            self.nextSamplingEpoch = epochPkts/self.arrivalRate
            try:
                yield self.env.timeout(Const.LONG_SLEEP_TIME)
            except simpy.Interrupt:
                if Const.DEBUG_DETAILED: print("Interrupt from Cluster Monitor at epoch end")

            self.collectEnergyStat()
            clusterEnergy = self.serverList.energyUsageLastEpoch
            clusterPower = float(clusterEnergy) / self.samplingEpoch
            if Const.DEBUG_TEST: print("Power {:.3f}, pkts {}, rate {:.3f}, secs {:.1f}, P95 {:.3f}, mean {:.3f}, P95svc {:.3f}, P95qtime {:.3f}".format(clusterPower, self.respCount, self.reqGenThread.arrivalRate, self.samplingEpoch, self.clMonitor.pxLat, self.clMonitor.meanLat, self.clMonitor.pxSvcTime, self.clMonitor.pxQTime))
#            if Const.DEBUG_TEST: print("pkts {}, rate {:.3f}, secs {:.1f}, P95 {:.3f}".format(self.respCount, self.reqGenThread.arrivalRate, self.samplingEpoch, self.clMonitor.pxLat))

            if Const.DEBUG_DETAILED:
                objgraph.show_most_common_types()
                memUsed = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                print("Memory used = {} KB".format(memUsed))
                print("Env queue Length = {}, mem used = {}, eid = {}, pushed = {}, popped = {}".format(len(self.env._queue), sys.getsizeof(self.env._queue), self.env._eid, self.env.totalPushed, self.env.totalPopped))

                print("env Queue list = ")
                for i in range(10): print(self.env._queue[i][0])
                temp = []
                for tim in self.env._queue:
                    temp.append(tim[0])
                print("min value = {}, now = {}".format(min(temp), self.env.now))
                
                self.env._queue[1000:-1] = []
                memUsed = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                print("New Memory used = {} KB".format(memUsed))
                print("Env queue Length = {}, mem used = {}".format(len(self.env._queue), sys.getsizeof(self.env._queue)))


            if Const.SIMPY_HEAP_FIX:
                tempQ = []
                for i in range(len(self.env._queue)):
                    if self.env._queue[i][0] <= Const.LONG_SLEEP_TIME:
                        tempQ.append(self.env._queue[i])
                self.env._queue[:] = []
                self.env._queue.extend(tempQ)
#                print(tempQ)
                heapify(self.env._queue)
                
#            self.env._queue[1000:-1] = []
            
            self.reqGenThread.setArrivalRate(self.arrivalRate)
            self.samplingEpoch = epochPkts/self.arrivalRate
            
#            self.resetMySim()
            self.serverList.clearAllQueues()
            self.csRespQ.clearQueue()
            self.reqGenThread.resetCounters()
            self.resetClusterSamplingStats()
            
        print("Simulation Finish")
            
            
    def collectEnergyStat(self):
        self.epochReqCount = self.reqGenThread.getEpochReqCount()
        self.respCount = self.clMonitor.respCount
        self.reqTput = float(self.respCount) / self.samplingEpoch
        self.reqLoad = float(self.epochReqCount) / self.samplingEpoch
        energyUsageForCurrClusterConfig = 0
        
        for sid in range(Const.NUM_SERVERS):
            server = self.serverList.getServer(sid)
            server.energyUsageLastEpoch = server.respAggregator.energyUsagePerSampEpoch
            server.avgPowerLastEpoch = float(server.energyUsageLastEpoch) / self.samplingEpoch
            if (server.active == 1) or Const.INACTIVE_SERVER_POWER_CONSIDERED:
                energyUsageForCurrClusterConfig += server.energyUsageLastEpoch
            if Const.DEBUG_DETAILED: print("For Server {}, Last Epoch Energy = {:.3f}, Power = {:.3f}".format(sid, server.energyUsageLastEpoch, server.avgPowerLastEpoch))
            self.resetServerSamplingStats(server)
            
        if Const.DEBUG_DETAILED: print("PxLat = {:.3f}, Energy = {:.3f} for {} / {} packets per second in {} secs".format(self.clMonitor.pxLat, energyUsageForCurrClusterConfig, self.reqTput, self.reqLoad, self.samplingEpoch))
        self.serverList.energyUsageLastEpoch = energyUsageForCurrClusterConfig
        self.serverList.avgPowerLastEpoch = float(energyUsageForCurrClusterConfig) / self.samplingEpoch


    def resetServerSamplingStats(self, server):
        server.respAggregator.energyUsagePerSampEpoch = 0
        for core in server.coreList.coreList:
            if core.active == 1:
                if Const.DEBUG_DETAILED: print("Total service time of core {} server {} in last epoch = {:.3f}".format(core.cid, server.sid, core.currSampEpochServiceTime))
            core.currSampEpochServiceTime = 0
            core.reqsProcessedLastEpoch = 0
            

    def resetClusterSamplingStats(self):
        for sid in range(Const.NUM_SERVERS):
            server = self.serverList.getServer(sid)
            server.respAggregator.energyUsagePerSampEpoch = 0
            for core in server.coreList.coreList:
                if core.active == 1:
                    if Const.DEBUG_DETAILED: print("Total service time of core {} server {} in last epoch = {:.3f}".format(core.cid, server.sid, core.currSampEpochServiceTime))
                core.currSampEpochServiceTime = 0
                core.reqsProcessedLastEpoch = 0

                
    def resetMySim(self):
        print("Resetting Simulation")
        self.reqGenThread.halt = 1
        self.clMonitor.halt = 1
        self.clMonitor.action.interrupt()
        self.serverList.clearAllQueues()
        yield self.env.timeout(Const.DELTA_TIME + Const.RESP_AGGREGATION_INTERVAL)
        self.serverList.clearAllQueues()
        self.csRespQ.clearQueue()
        self.reqGenThread.halt = 0
        self.clMonitor.halt = 0
        self.reqGenThread.resetCounters()
        self.resetClusterSamplingStats()
        self.reqGenThread.action.interrupt()
        self.clMonitor.action.interrupt()
