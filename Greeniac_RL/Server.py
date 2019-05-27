# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 11:17:24 2018

@author: sambit
"""

from Const import Const

#Server Object
class Server(object):
#    __slots__ = ('env', 'serverReqQ', 'serverRespQ', 'taskSched', 'respAggregator', 'coreList', 'sid', 'active')
    "All components within a server"
    def __init__(self, env, serverReqQ, serverRespQ, taskSched, respAggregator, coreList, sid):
        self.env = env
        self.serverReqQ = serverReqQ
        self.serverRespQ = serverRespQ
        self.taskSched = taskSched
        self.respAggregator = respAggregator
        self.coreList = coreList
        self.sid = sid
        self.active = 0
        self.energyUsageLastEpoch = 0
        self.avgPowerLastEpoch = 0
        self.slAgent = None
        for core in self.coreList.coreList:
            core.taskSched = self.taskSched
            core.active = 0
        if Const.DEBUG_INIT: print("Server {} created".format(self.sid))
    
    def getServerReqQ(self):
        return self.serverReqQ

    def getServerRespQ(self):
        return self.serverRespQ

    def getTaskScheduler(self):
        return self.taskSched

    def getResponseAggregator(self):
        return self.respAggregator

    def getCoreList(self):
        return self.coreList

