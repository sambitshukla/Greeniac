#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 13:28:12 2018

@author: sambit
"""
from Const import Const

# Per Server Aggregator Thread
class ResponseAggregator(object):
#    __slots__ = ('env', 'sid', 'csRespQ', 'serverRespQ', 'coreList', 'energyUsagePerAggrEpoch', 'energyUsagePerSampEpoch', 'action')
    def __init__(self, env, csRespQ, serverRespQ, coreList, sid):
        self.env = env
        self.sid = sid
        self.csRespQ = csRespQ
        self.serverRespQ = serverRespQ
        self.coreList = coreList
        self.energyUsagePerAggrEpoch = 0
        self.energyUsagePerSampEpoch = 0
        self.action = self.env.process(self.run())

    def implementDvfsUpdateTest(self):
        #round-robin frequency on each core
        for core in self.coreList.coreList:
            currFreq = core.currFreq
            freqProfile = Const.CPU_FREQ_PROFILES[core.cpuName]
            freqIndex = freqProfile.index(currFreq)
            newFreqIndex = (freqIndex + 1) % len(freqProfile)
            core.newFreq = freqProfile[newFreqIndex]

    def calcNonCpuEnergyForCurrEpoch(self, epoch):
        nonCpuEnergy = epoch * Const.NON_CPU_SERVER_POWER_PROFILES[self.sid]
        if Const.DEBUG_RESPAGGR: print("NON-CPU Server Energy for {:.3f} secs on server {} = {:.6f}".format(epoch, self.sid, nonCpuEnergy))
        return nonCpuEnergy
                        
    def calcEnergyUsageAggrEpoch(self, coreList):
        self.energyUsagePerAggrEpoch = 0
        for core in self.coreList.coreList:
            if (core.active == 0):
                continue    #TODO: Energy usage of inactive cores
            dynEnergy = core.calcDynEnergyForCurrFreq()
            dynEnergy += core.dynEnergyUsage
            core.dynEnergyUsage = 0
            core.currSampEpochServiceTime += core.currFreqServiceTime
            core.currFreqServiceTime = 0    #TODO: Logic incorrect if core currently in service
            statEnergy = core.calcStaticEnergyForCurrEpoch(Const.RESP_AGGREGATION_INTERVAL)
            if Const.DEBUG_RESPAGGR: print("Energy: Dyn = {:.6f}, Stat = {:.6f} for core {} server {}".format(dynEnergy, statEnergy, core.cid, core.sid))
            self.energyUsagePerAggrEpoch += (statEnergy + dynEnergy)
        if Const.NON_CPU_SERVER_POWER_CONSIDERED:
            self.energyUsagePerAggrEpoch += self.calcNonCpuEnergyForCurrEpoch(Const.RESP_AGGREGATION_INTERVAL)
        self.energyUsagePerSampEpoch += self.energyUsagePerAggrEpoch
        return self.energyUsagePerAggrEpoch
            
    def setCoreActivationPolicy(self, actList):
        for i in range(len(self.coreList.coreList)):
            self.coreList.coreList[i].active = actList[i]

    def run(self):
        print("ResponseAggregatorThread thread started")
        while True:
            yield self.env.timeout(Const.RESP_AGGREGATION_INTERVAL)
            if Const.DEBUG_RESPAGGR: print("RAT @ server {} woke to find {} responses in server {} queue type {}".format(self.sid, self.serverRespQ.getCurrentQlen(), self.serverRespQ.sid, self.serverRespQ.qId))
            if (self.serverRespQ.getCurrentQlen() > 0):
                qlen = self.serverRespQ.getCurrentQlen()
                
                self.csRespQ.reqQueue.extend(self.serverRespQ.reqQueue[0:qlen])  # Copy requests to csRespQueue
                self.csRespQ.qLen = len(self.csRespQ.reqQueue)
                
                if Const.DEBUG: print("\nRAT :: Copied {} reqs from server {} to csRespQ of new length = {}".format(qlen, self.sid, self.csRespQ.qLen))
                # self.serverRespQ.reqQueue[0:qlen] = []  # clear server response queue
                del self.serverRespQ.reqQueue[0:qlen] # clear server response queue
                self.serverRespQ.qLen = len(self.serverRespQ.reqQueue)
                
            #self.implementDvfsUpdateTest()
            # Aggregate server E usage for current epoch before sched (Core Activation) policy update for next epoch
            energyUsage = self.calcEnergyUsageAggrEpoch(self.coreList)
            if Const.DEBUG: print("RAT :: Energy usage in current epoch = {:.6f}".format(energyUsage))
            #self.setCoreActivationPolicy([1, 0])
