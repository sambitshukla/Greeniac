# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 11:20:09 2018

@author: sambit
"""

import random
import simpy

import helper as hlp
from Const import Const

# Single Load Balancer
class LoadBalancer(object):
#    __slots__ = ('env', 'csReqQ', 'serverList', 'mostRecentServerId', 'nextServerId', 'action', 'algo', 'prevClusterCfgList', 'loadRatio', 'configTputInfoAvailable', \
#                 'configTputInfo', 'allServersConfigList', 'taskSched')
    def __init__(self, env, csReqQ, serverList, algo="rr"):
        self.env = env
        self.csReqQ = csReqQ
        self.serverList = serverList
        self.mostRecentServerId = 0
        self.nextServerId = 0
        self.action = self.env.process(self.run())
        self.algo = algo
        self.prevClusterCfgList = self.serverList.clusterCfgList
        self.loadRatio = [1, 1, 1, 1]   #TODO: Hardcoded. All reqs to the first server
        self.configTputInfoAvailable = False
        self.configTputInfo = []
        self.allServersConfigList = []
        
    def setLbAlgorithm(self, algo):
        self.algo = algo
        
    def run(self):
        print("LoadBalancerThread thread started")
        while True:
            try:
                yield self.env.timeout(Const.LONG_SLEEP_TIME)
            except simpy.Interrupt:
                while (self.csReqQ.getCurrentQlen() > 0):
                    req = self.csReqQ.dequeueRequest()
    
                    if (self.algo == "rr"):
                        for i in list(range(1, Const.NUM_SERVERS + 1, 1)):
                            serverId = (self.mostRecentServerId + i) % Const.NUM_SERVERS
                            if (self.serverList.getServer(serverId).active == 1):
                                self.nextServerId = serverId
                                break
                            if (i == Const.NUM_SERVERS):
                                if Const.DEBUG_LDBALANCER: print ("ALERT!!! No active servers to process requests")
                                self.nextServerId = -1

                    elif (self.algo == "ratio"):
                        if self.configTputInfoAvailable:
                            if (self.prevClusterCfgList != self.serverList.clusterCfgList):
                                self.loadRatio = hlp.getLoadRatio(self.serverList.clusterCfgList, self.configTputInfo, self.allServersConfigList, Const.NUM_SERVERS)
                                self.prevClusterCfgList = self.serverList.clusterCfgList
                            rand = random.uniform(0, 1)
                            for idx in range(len(self.loadRatio)):
                                if rand < self.loadRatio[idx]:
                                    self.nextServerId = idx
                                    break
                                if (idx == (len(self.loadRatio) - 1)):
                                    if Const.DEBUG_LDBALANCER: print ("ALERT!!! No active servers to process requests")
                                    self.nextServerId = -1
                                
                        else:
                            self.loadRatio = Const.STATIC_LOAD_RATIO
                            loadSum = sum(Const.STATIC_LOAD_RATIO)
                            rand = loadSum*random.uniform(0, 1)
                            for idx in range(len(self.loadRatio)):
                                if rand <= self.loadRatio[idx]:
                                    self.nextServerId = idx
                                    break
                                else:
                                    rand -= self.loadRatio[idx]
                                    
                                if (idx == (len(self.loadRatio) - 1)):
                                    if Const.DEBUG_LDBALANCER: print ("ALERT!!! No active servers to process requests")
                                    self.nextServerId = -1                            

                    if (self.nextServerId == -1):
                        break
                    if Const.DEBUG_LDBALANCER: print ("Request {} being submitted to server {}".format(req.id , self.nextServerId))
                    
                    #Enque request and wake up corresponding server task scheduler
                    self.serverList.getServer(self.nextServerId).getServerReqQ().enqueueRequest(req)
                    self.taskSched = self.serverList.getServer(self.nextServerId).getTaskScheduler()
                    if self.taskSched.idling == 1:
                        self.taskSched.action.interrupt()
                    self.mostRecentServerId = self.nextServerId
