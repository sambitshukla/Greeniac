# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 11:19:27 2018

@author: sambit
"""
import simpy
import numpy as np

from Const import Const
from Request import Request

class ReqGenerator(object):
#    __slots__ = ('env', 'halt', 'reqsGenerated', 'csReqQ', 'lbt', 'action', 'arrivalRate', 'pattern', 'taskSizeType', 'reqCountSampEpochBegin', 'nextArrivalTime')
#    "Request generator based on poisson or file input"
    def __init__(self, env, csReqQ, lbt, pattern="poisson"):
        self.env = env
        self.halt = 0
        self.reqsGenerated = 0
        self.csReqQ = csReqQ
        self.lbt = lbt
        self.action = self.env.process(self.run())
        self.arrivalRate = Const.ARRIVAL_RATE
        self.pattern = pattern
        self.taskSizeType = "exp"
        self.reqCountSampEpochBegin = 0
        
    def setArrivalRate(self, rate):
        self.arrivalRate = rate
        
    def setArrivalPattern(self, pattern):
        self.pattern = pattern
        
    def setReqTaskSizeType(self, taskSizeType):
        self.taskSizeType = taskSizeType
        
    def takeReqCountSnapshot(self):
        self.reqCountSampEpochBegin = self.reqsGenerated

    def getEpochReqCount(self):
        return (self.reqsGenerated - self.reqCountSampEpochBegin)

    def reset(self):
        self.reqsGenerated = 0
        self.reqCountSampEpochBegin = 0
        self.arrivalRate = Const.ARRIVAL_RATE
        self.pattern = "poisson"
        self.taskSizeType = "exp"
        
    def resetCounters(self):
        self.reqsGenerated = 0
        self.reqCountSampEpochBegin = 0
        
    def run(self):
        if Const.DEBUG_REQGEN: print("ReqGeneratorThread thread started")
        while True:
            if (self.halt == 1):
                try:
                    if Const.DEBUG_REQGEN: print("ReqGeneratorThread thread halting")
                    yield self.env.timeout(Const.LONG_SLEEP_TIME)
                except simpy.Interrupt:
                    if Const.DEBUG_REQGEN: print("ReqGeneratorThread thread resuming")
                    
            if (self.pattern == "uniform"):
                self.nextArrivalTime = (1/Const.ARRIVAL_RATE)
            elif (self.pattern == "poisson"):
                self.nextArrivalTime = np.random.exponential(1.0/self.arrivalRate)
                
            if Const.DEBUG_REQGEN: print("next packet arriving in {:.3f}".format(self.nextArrivalTime))
            yield self.env.timeout(self.nextArrivalTime)
            self.reqsGenerated += 1
            req = Request(self.env, self.reqsGenerated - 1)
            
            if (self.taskSizeType == "exp"):
                req.taskSize = np.random.exponential(Const.SERVICE_TIME)

            elif (self.taskSizeType == "fixed"):
                req.taskSize = Const.SERVICE_TIME
                
            elif (self.taskSizeType == "lognormal"):
                #Edit mean and stddev if needed
                req.taskSize = (np.random.lognormal(Const.LOGNORMAL_MEAN, Const.LOGNORMAL_STDDEV)) * Const.SERVICE_TIME
                
            elif (self.taskSizeType == "minmaxexp"):
                taskSize = 0
                while (taskSize < Const.MIN_SERVICE_TIME) or (taskSize > Const.MAX_SERVICE_TIME):
                    taskSize = np.random.exponential(Const.SERVICE_TIME)   # Normalized task size proportional to number of instructions executed
                req.taskSize = taskSize
                
                
            self.csReqQ.enqueueRequest(req)
            if Const.DEBUG_REQGEN: print("Packet {} generated at {:.3f}".format(req.id, self.env.now))
            self.lbt.action.interrupt()
