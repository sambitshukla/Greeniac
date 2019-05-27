# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 22:33:58 2018

@author: sambit
"""
from Const import Const
import helper as hlp
import simpy

from Core import Core
from Server import Server
from ServerList import ServerList
from CoreList import CoreList
import Queues

from TaskScheduler import TaskScheduler
from ReqGenerator import ReqGenerator
from ResponseAggregator import ResponseAggregator
from LoadBalancer import LoadBalancer
from ClusterMonitor import ClusterMonitor
from GreeniacManager import GreeniacManager
#from myMgr import TestManager


#Const.DEBUG_CORE = 1
#Const.DEBUG_QUEUE = 1
#Const.DEBUG_REQGEN = 1
#Const.DEBUG_CLMONITOR = 1
#Const.DEBUG_TSCHED = 1
#Const.DEBUG_LDBALANCER = 1
#Const.DEBUG_RESPAGGR = 1
#Const.DEBUG_GREENMGR = 1
#Const.DEBUG_CLAGENT = 1
#Const.DEBUG_RLAGENT = 1
#Const.DEBUG = 1
#Const.DEBUG_DETAILED = 1
Const.DEBUG_WARN = 1
Const.DEBUG_INIT = 1
Const.DEBUG_TEST = 1

# Generate and Sort Configurations for the each server in the cluster
allServerCfgsList = []
for sid in range(Const.NUM_SERVERS):
    cfgList = []
    hlp.generateAllConfigs(cfgList, sid, Const.CORE_COUNT_MATRIX, Const.CPU_NAME_LIST)
    allServerCfgsList.append(cfgList)

if Const.DEBUG_INIT:
    for sid in range(Const.NUM_SERVERS):
        print("\nList of all possible configurations for server {} : Total = {}".format(sid, len(allServerCfgsList[sid])))
        for cfg in allServerCfgsList[sid]:
            print(cfg)

allServerPwrDictList = []
allServerPwrSortedConfigsList = []
for sid in range(Const.NUM_SERVERS):
    pwrDict = {}
    pwrSortedConfigs = hlp.genSortPwrConfigs(pwrDict, allServerCfgsList[sid])
    allServerPwrDictList.append(pwrDict)
    allServerPwrSortedConfigsList.append(pwrSortedConfigs)

if Const.DEBUG_INIT:
    for sid in range(Const.NUM_SERVERS):
        print("\n\nSorted list of configurations for server {} : ".format(sid))
        for cfg in allServerPwrSortedConfigsList[sid]: 
            print("{}\t\t{:.3f}".format(cfg, allServerPwrDictList[sid][cfg]))


# Instantiate cluster components
env = simpy.Environment()

csReqQ = Queues.CSReqQ(env)
csRespQ = Queues.CSRespQ(env)
serverList = ServerList(env)

for sid in range(0, Const.NUM_SERVERS):
    coreList = CoreList(env, sid)
    serverReqQ = Queues.ServerReqQ(env, sid)
    serverRespQ = Queues.ServerRespQ(env, sid)
    coreId = 0
    for cpuName in Const.CPU_NAME_LIST:
        index = Const.CPU_NAME_LIST.index(cpuName)
        for count in range(Const.CORE_COUNT_MATRIX[sid][index]):
            initFreq = max(Const.CPU_FREQ_PROFILES[cpuName])   #start running cores at highest supported frequency
            if Const.DEBUG_INIT: print("Assigning Q type {} server {} to core {} server {}".format(serverRespQ.qId, serverRespQ.sid, coreId, sid))
            core = Core(env, initFreq, serverReqQ, serverRespQ, sid, coreId, cpuName)
            coreList.addtoList(core)
            coreId += 1
    taskSchedulerThread = TaskScheduler(env, serverReqQ, coreList, sid)
    if Const.DEBUG_INIT: print("Assigning Q type {} server {} to RAT of server {}".format(serverRespQ.qId, serverRespQ.sid, sid))
    responseAggregatorThread = ResponseAggregator(env, csRespQ, serverRespQ, coreList, sid)
    server = Server(env, serverReqQ, serverRespQ, taskSchedulerThread, responseAggregatorThread, coreList, sid)
    serverList.addtoList(server)

#initialize a cluster configuration    
#TODO: Hardcoded initial config
clusterCfgList = [0, []]*Const.NUM_SERVERS
clusterCfgList[0] = 1
clusterCfgList[1] = allServerCfgsList[0][0]
serverList.activateServersAndCores(clusterCfgList)
if Const.DEBUG: hlp.listAllCores(serverList)


lbt = LoadBalancer(env, csReqQ, serverList, algo = "rr")
#rgt = ReqGenerator(env, csReqQ, lbt, pattern = "poisson")
rgt = ReqGenerator(env, csReqQ, lbt, pattern = "uniform")

#testMgr = TestManager(env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList)
greenMgr = GreeniacManager(env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList)

#clMonitor = ClusterMonitor(env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList, testMgr)
clMonitor = ClusterMonitor(env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList, greenMgr)

#testMgr.clMonitor = clMonitor
greenMgr.clMonitor = clMonitor

env.run(until=rgt.action)
print("Simulation Finish")

#Post Simulation Analysis
