# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 10:01:39 2018

@author: sambit
"""
import simpy

from Const import Const

class Core(object):
    "Base CPU core class"
    def __init__(self, env, freq, serverReqQ, serverRespQ, sid, cid, cpuName):
        self.env = env
        self.cpuName = cpuName
        self.baseFreq = freq
        self.currFreq = freq
        self.newFreq = freq
        self.dynEnergyUsage = 0
        self.serverReqQ = serverReqQ
        self.serverRespQ = serverRespQ
        self.timeStarted = self.env.now
        self.idling = 1   # When no task is running
        self.active = 1     # Task Scheduler Policy-driven: sleeping or active
        self.taskQ = []
        self.totalServiceTime = 0
        self.currFreqServiceTime = 0
        self.currSampEpochServiceTime = 0
        self.reqsProcessed = 0
        self.reqsProcessedLastEpoch = 0
        self.sid = sid
        self.cid = cid
        self.taskSched = None
        self.action = self.env.process(self.run())
        
    def enqueueTask(self, req):
        self.taskQ.append(req)

    def dequeueTask(self):
        if len(self.taskQ) == 0:
            if Const.DEBUG_CORE: print ("Empty Queue")
        else:
            self.taskQ.pop(0)

    def pickTask(self):
        if len(self.taskQ) == 0:
            if Const.DEBUG_CORE: print ("Empty Queue")
            return None
        else:
            task = self.taskQ[0]
            return task

    def calcDynEnergyForCurrFreq(self):
        idx = (Const.CPU_FREQ_PROFILES[self.cpuName]).index(self.currFreq)
        #TODO: assumes linear freq-energy model. Try quadratic model
        dynEnergy = self.currFreqServiceTime * (Const.CPU_POWER_PROFILES[self.cpuName])[idx+1]
        if Const.DEBUG_CORE: print("Dynamic Energy @ freq {}GHz for {:.3f} secs on core {} server {} = {:.6f}".format(self.currFreq, self.currFreqServiceTime, self.cid, self.sid, dynEnergy))
        return dynEnergy

    def calcStaticEnergyForCurrEpoch(self, epoch):
        statEnergy = epoch * (Const.CPU_POWER_PROFILES[self.cpuName])[0]
        if Const.DEBUG_CORE: print("Static Energy for {:.3f} secs on core {} server {} = {:.6f}".format(epoch, self.cid, self.sid, statEnergy))
        return statEnergy
        

    def run(self):
        print("CPU thread started for server {} core {} at {} GHz frequency".format(self.sid, self.cid, self.currFreq))
        while True:
            try:
                yield self.env.timeout(Const.LONG_SLEEP_TIME)
            except simpy.Interrupt:
                if Const.DEBUG_CORE: print("Core {} of server {} interrupted".format(self.cid, self.sid))
                self.idling = 0
                while (len(self.taskQ) > 0):
                    #update frequency if instructed by Task Scheduler
                    if (self.newFreq != self.currFreq):
                        if Const.DEBUG_CORE: print("Core {} of server {} freq updated to {}".format(self.cid, self.sid, self.newFreq))

                        # calculate power usage for last freq (lineor model)
                        self.dynEnergyUsage += self.calcDynEnergyForCurrFreq()
                        self.currSampEpochServiceTime += self.currFreqServiceTime

                        self.currFreq = self.newFreq
                        self.currFreqServiceTime = 0
                        
                    req = self.pickTask()
                    if Const.DEBUG_CORE: print("Core {} of server {} has {} requests left in queue".format(self.cid, self.sid, len(self.taskQ)))
                    
                    #Task Servicing
                    # Service time dependent on Request Size
                    serviceTime = req.taskSize * (Const.CPU_BASE_SERVICE_RATE / self.currFreq)
                    # TODO: Non-linear scaling of service time for OOO and In-order cpus
                    if (self.cpuName == Const.ATOM_STR):
                        serviceTime = float(serviceTime) / Const.BIG_TO_SMALL_SLOWDOWN
                    yield self.env.timeout(serviceTime)
                    
                    req.responseLatency = self.env.now - req.timeCreated
                    req.serviceTime = serviceTime
                    req.sid = self.sid
                    req.cid = self.cid
                    
                    self.totalServiceTime += serviceTime    #Track total service time to calculate energy usage
                    self.currFreqServiceTime += serviceTime
                    self.reqsProcessed += 1
                    self.reqsProcessedLastEpoch += 1
                    
                    #Push response to server response Queue
                    self.serverRespQ.enqueueRequest(req)
                    if Const.DEBUG_CORE: print("Request {} @ core {} server {} in {:.3f} secs. Response sent to Q {} server {}".format(req.id, req.cid, req.sid, req.serviceTime, self.serverRespQ.qId, self.serverRespQ.sid))
                    
                    #Inform task scheduler about emply task queue slot
                    self.dequeueTask()
                    if self.taskSched.idling == 1:
                        self.taskSched.action.interrupt()
                    
                self.idling = 1
                if Const.DEBUG_CORE: print("Core {} of server {} going to sleep".format(self.cid, self.sid))
