# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 11:18:25 2018

@author: sambit
"""
from Const import Const

#Servers List        
class ServerList(object):
#    __slots__ = ('env', 'serverList', 'prevClusterCfgList', 'clusterCfgList')
    "List of all Servers"
    def __init__(self, env):
        self.env = env
        self.serverList = []
        self.prevClusterCfgList = []
        self.clusterCfgList = []
        self.energyUsageLastEpoch = 0
        self.avgPowerLastEpoch = 0
        self.homogeneousCluster = True
    
    def addtoList(self, server):
        self.serverList.append(server)
        print("Server {} added to Server List".format(server.sid))

    def clearList(self):
        self.serverList[:] = []
        
    def getServer(self, index):
        return self.serverList[index]

    def clearAllQueues(self):
        # Clear queues before start of a new Sampling epoch during training
        for id in range(0, Const.NUM_SERVERS):
            server = self.getServer(id)
            if (server.active == 0) and Const.DEBUG_DETAILED: 
                print("HIGH ALERT :: Server not yet Activated !!!!!")
            server.serverReqQ.clearQueue()
            server.serverRespQ.clearQueue()


    def activateServersAndCores(self, clusterCfgList):
        # Activate servers
        self.clusterCfgList = clusterCfgList
        for sid in range(Const.NUM_SERVERS):
            server = self.getServer(sid)

#            print("ALERT :: Setting up cores for Server {}".format(sid))
            if (server.active == 0) and (self.clusterCfgList[sid*2] == 1):
                server.active = 1
                if Const.DEBUG_INIT: print("ALERT :: New Server {} Activated".format(sid))
            elif (server.active == 1) and (self.clusterCfgList[sid*2] == 0):
                # De-Activate all cores
                server.active = 0
                coreList = server.getCoreList()
                for c in range(coreList.numCores):
                    core = coreList.getCore(c)
                    core.active = 0
                if Const.DEBUG_INIT: print("ALERT :: Server {} De-Activated".format(sid))
                continue
            elif (server.active == 0):
#                print("ALERT :: Server already inactive")
                continue
            
            # De-Activate all cores first
#            print("ALERT :: Server {} cores De-Activating".format(sid))
            coreList = server.getCoreList()
            for c in range(coreList.numCores):
                core = coreList.getCore(c)
                core.active = 0

            # Activate and set the core freq of server sid
            for index in range(0, len(clusterCfgList[(sid*2)+1]), 3):
                coreName = clusterCfgList[(sid*2)+1][index]
                numCores = clusterCfgList[(sid*2)+1][index+1]
                coreFreq = clusterCfgList[(sid*2)+1][index+2]
                
                for c in range(coreList.numCores):
                    core = coreList.getCore(c)
                    if core.cpuName == coreName:
                        if numCores > 0:
                            core.active = 1
                            core.newFreq = coreFreq
                            numCores -= 1
                        else:
                            core.active = 0
        self.prevClusterCfgList = self.clusterCfgList
        