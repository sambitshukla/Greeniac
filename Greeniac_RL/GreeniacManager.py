# -*- coding: utf-8 -*-
"""
Created on Sat Dec 29 00:26:48 2018

@author: sambit
"""

import pprint
import simpy
from heapq import heapify
import objgraph

from Const import Const
import helper as hlp
import sl_agent as slagent
import cl_agent as clagent


# Simulation Orchestrator thread
class GreeniacManager(object):
    def __init__(self, env, csRespQ, serverList, rgt, lbt, allServerPwrSortedConfigsList):
        self.env = env
        self.csRespQ = csRespQ
        self.lbThread = lbt
        self.allServerPSConfigsList = allServerPwrSortedConfigsList
        self.aspsValidConfigsList = []
        self.aspsValidConfigsEnergyList = []
        self.aspsValidConfigsTputList = []
        self.serverList = serverList
        self.reqGenThread = rgt
        self.samplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.respCount = 0
        self.clMonitor = None
        self.allServerQTable = []
        self.simStage = 0
        self.simProcess = None
        self.action = self.env.process(self.run())
        
        
    def run(self):
        if Const.DEBUG_INIT: print("Greeniac Manager started for cluster")
        print("Simulation started")
        
        self.collectConfigStats = self.env.process(self.collectConfigStats())
        self.slLearning = self.env.process(self.runSLLearning())
        self.clLearning = self.env.process(self.runCLLearning())
        self.exploitRL = self.env.process(self.exploitRL())
        
        self.simProcess = self.collectConfigStats
        
#        if Const.DEBUG_GREENMGR: print("Start Step 1: Collect Configuration Throughput stats for workload")
#        self.collectConfigStats()
#        
#        if Const.DEBUG_GREENMGR: print("Start Step 2: Perform Server Level Learning")
#        self.runSLLearning()
#        
#        if Const.DEBUG_GREENMGR: print("Start Step 3: Perform Cluster Level Learning")
#        self.runCLLearning()
#        
#        if Const.DEBUG_GREENMGR: print("Start Step 4: Run Workload exploiting fully trained RL logic")
#        self.exploitRL()

        while (self.simProcess != None):
            try:
                yield self.env.timeout(Const.LONG_SLEEP_TIME)
            except simpy.Interrupt:
                self.simProcess.interrupt()
                
        print("Simulation Finish")
        yield self.env.timeout(Const.RESP_AGGREGATION_INTERVAL)
            
            
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
            if Const.DEBUG_GREENMGR: print("For Server {}, Last Epoch Energy = {:.3f}, Power = {:.3f}".format(sid, server.energyUsageLastEpoch, server.avgPowerLastEpoch))
            self.resetServerSamplingStats(server)
            
        if Const.DEBUG_GREENMGR: print("PxLat = {:.3f}, Energy = {:.3f} for {} / {} packets per second in {} secs".format(self.clMonitor.pxLat, energyUsageForCurrClusterConfig, self.reqTput, self.reqLoad, self.samplingEpoch))
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
            

    def resetSim(self):
        print("Resetting Simulation")
        self.reqGenThread.halt = 1
        self.clMonitor.halt = 1
        self.clMonitor.action.interrupt()
        self.serverList.clearAllQueues()
        yield self.env.timeout(2 * Const.RESP_AGGREGATION_INTERVAL)
        self.csRespQ.clearQueue()
        self.reqGenThread.halt = 0
        self.clMonitor.halt = 0
        self.reqGenThread.reset()
        self.reqGenThread.setReqTaskSizeType("lognormal")
        self.resetClusterSamplingStats()
        self.reqGenThread.action.interrupt()
        self.clMonitor.action.interrupt()


    def exploitRL(self):
        try:
            yield self.env.timeout(Const.LONG_SLEEP_TIME)
        except simpy.Interrupt:
            if Const.DEBUG_RLAGENT: print("Exploiting RL Logic started")
            self.simProcess = self.exploitRL
            
        self.nextSamplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.clMonitor.samplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.samplingEpoch = self.clMonitor.samplingEpoch

        self.aspsValidConfigsList = hlp.load_obj("aspsValidConfigsList")
        self.aspsValidConfigsEnergyList = hlp.load_obj("aspsValidConfigsEnergyList")
        self.aspsValidConfigsTputList = hlp.load_obj("aspsValidConfigsTputList")
        self.allServerQTable = hlp.load_obj("allServerQTable")
        self.clusterCQTable = hlp.load_obj("CQTable")

        aspsQTableValidConfigsTputList, aspsQTableValidConfigsEnergyList = \
            hlp.getLearntConfigs(self.aspsValidConfigsList, self.aspsValidConfigsEnergyList, self.allServerQTable)

        self.lbThread.allServersConfigList = self.aspsValidConfigsList
        self.lbThread.configTputInfo = self.aspsValidConfigsTputList   #aspsQTableValidConfigsTputList  or  self.aspsValidConfigsTputList
        self.lbThread.setLbAlgorithm("ratio")
        self.lbThread.configTputInfoAvailable = True
        
#        clLoadMin = min(tputList[0] for tputList in self.aspsValidConfigsTputList)
        clLoadMax = min(sum(tputList[-1] for tputList in self.aspsValidConfigsTputList), Const.MAX_ARRIVAL_RATE + Const.CL_LOAD_BIN)
        resultFile = open("GreeniacDiscreteLoads.txt", 'w')
#        resultFile = open("BinPackDiscreteLoads.txt", 'w')
#        resultFile = open("EquiDistDiscreteLoads.txt", 'w')
#        optCfgDict = self.getOptServerCfgDict(self.aspsValidConfigsList, self.allServerQTable[0])
        
#        self.resetSim()
        if Const.DEBUG_SLAGENT: print("Resetting Simulation")
        self.reqGenThread.halt = 1
        self.clMonitor.halt = 1
        self.clMonitor.action.interrupt()
        self.serverList.clearAllQueues()
        yield self.env.timeout(2 * Const.RESP_AGGREGATION_INTERVAL)
        self.csRespQ.clearQueue()
        self.reqGenThread.halt = 0
        self.clMonitor.halt = 0
        self.reqGenThread.reset()
        self.reqGenThread.setReqTaskSizeType("lognormal")
        self.resetClusterSamplingStats()
        self.reqGenThread.action.interrupt()
        self.clMonitor.action.interrupt()
        
        clusterCfgList = hlp.getMaxClusterCfg(self.aspsValidConfigsList)
        self.serverList.activateServersAndCores(clusterCfgList)
        
        print("Load Trace Begin")
        for cLoad in hlp.frange(10.0, clLoadMax, 10.0):
            avgPower = 0
            avgTailLat = 0
            iterations = 5
            
            self.reqGenThread.setArrivalRate(cLoad)
            
            nextCfgList = self.serverList.clAgent.getNextAction(0, 0, 0, cLoad, False)   #TODO: TEST only
            clusterCfgList = hlp.getBestClusterCfg(cLoad, self.clusterCQTable, Const.CL_LOAD_BIN)
#                clusterCfgList = hlp.getBinPackClusterCfg(cLoad, optCfgDict, Const.NUM_SERVERS)
#                clusterCfgList = hlp.getEquiDistClusterCfg(cLoad, optCfgDict, Const.CL_LOAD_BIN, Const.NUM_SERVERS)
            if (clusterCfgList == []):
                print("No more cluster config supported for load ", cLoad)
                break
            print("nextCfgList = {}, clusterCfgList = {}".format(nextCfgList, clusterCfgList))
            
            self.serverList.activateServersAndCores(clusterCfgList)
        
            for iter in range(iterations):
                try:
                    yield self.env.timeout(Const.LONG_SLEEP_TIME)
                except simpy.Interrupt:
                    #Interrupt from Cluster Monitor at epoch end
                    self.collectEnergyStat()
                    clusterEnergyUsageForCurrConfig = self.serverList.energyUsageLastEpoch
                    currPower = float(clusterEnergyUsageForCurrConfig) / self.samplingEpoch

                    self.reqGenThread.takeReqCountSnapshot()
                    clusterEnergyUsageForCurrConfig = 0
                    avgPower += currPower
                    avgTailLat += self.clMonitor.pxLat
            self.serverList.clearAllQueues()
            avgPower /= iterations
            avgTailLat /= iterations
            resultFile.write("{:.1f} : {:.3f} : {:.3f} : {} : {}\n".format(cLoad, avgTailLat, avgPower, self.lbThread.loadRatio, clusterCfgList))
            print("Load, TL, Avg Power : {:.1f} : {:.3f} : {:.3f}".format(cLoad, avgTailLat, avgPower))

            if Const.SIMPY_HEAP_FIX:
                tempQ = []
                for i in range(len(self.env._queue)):
                    if self.env._queue[i][0] <= Const.LONG_SLEEP_TIME:
                        tempQ.append(self.env._queue[i])
                self.env._queue[:] = []
                self.env._queue.extend(tempQ)
                heapify(self.env._queue)
                
        print("Load Trace Completed")
        resultFile.close()
        self.simProcess = None



    def runCLLearning(self):
        try:
            yield self.env.timeout(Const.LONG_SLEEP_TIME)
        except simpy.Interrupt:
            if Const.DEBUG_CLAGENT: print("CL-Agent learning started")
            self.simProcess = self.clLearning
            
#        self.resetSim()
        if Const.DEBUG_CLAGENT: print("Resetting Simulation")
        self.reqGenThread.halt = 1
        self.clMonitor.halt = 1
        self.clMonitor.action.interrupt()
        self.serverList.clearAllQueues()
        yield self.env.timeout(2 * Const.RESP_AGGREGATION_INTERVAL)
        self.csRespQ.clearQueue()
        self.reqGenThread.halt = 0
        self.clMonitor.halt = 0
        self.reqGenThread.reset()
        self.reqGenThread.setReqTaskSizeType("lognormal")
        self.resetClusterSamplingStats()
        self.reqGenThread.action.interrupt()
        self.clMonitor.action.interrupt()
        
        self.allServerQTable = []
        self.learning = True
        self.nextSamplingEpoch = self.samplingEpoch = self.clMonitor.samplingEpoch = Const.CL_SAMPLING_EPOCH

        self.aspsValidConfigsList = hlp.load_obj("aspsValidConfigsList")
        self.aspsValidConfigsEnergyList = hlp.load_obj("aspsValidConfigsEnergyList")
        self.aspsValidConfigsTputList = hlp.load_obj("aspsValidConfigsTputList")
        self.allServerQTable = hlp.load_obj("allServerQTable")

        aspsQTableValidConfigsTputList, aspsQTableValidConfigsEnergyList = \
            hlp.getLearntConfigs(self.aspsValidConfigsList, self.aspsValidConfigsEnergyList, self.allServerQTable)

        self.lbThread.allServersConfigList = self.aspsValidConfigsList
        self.lbThread.configTputInfo = self.aspsValidConfigsTputList   #aspsQTableValidConfigsTputList  or  self.aspsValidConfigsTputList
        self.lbThread.setLbAlgorithm("ratio")
        self.lbThread.configTputInfoAvailable = True

        maxPower = sum(energyList[-1] for energyList in self.aspsValidConfigsEnergyList)
        clLoadMin = min(tputList[0] for tputList in self.aspsValidConfigsTputList)
        clLoadMax = min(sum(tputList[-1] for tputList in aspsQTableValidConfigsTputList), Const.MAX_ARRIVAL_RATE + Const.CL_LOAD_BIN)
        clLoadBegin = clLoadMin - (clLoadMin % Const.CL_LOAD_BIN)
        clLoadEnd = clLoadMax - (clLoadMax % Const.CL_LOAD_BIN) + Const.CL_LOAD_BIN
        if (clLoadBegin == 0): clLoadBegin = Const.CL_LOAD_BIN

        clAgent = clagent.CLAgent(self.env, clLoadBegin, clLoadEnd, maxPower, clLoadMax, Const.CL_LOAD_BIN, \
                                       self.aspsValidConfigsList, aspsQTableValidConfigsEnergyList, aspsQTableValidConfigsTputList, \
                                       self.allServerQTable, Const.TAIL_LATENCY_SLO, Const.DEF_SAMPLING_EPOCH, Const.NUM_SERVERS)
        self.serverList.clAgent = clAgent        

        for cLoad in hlp.frange(clLoadBegin, clLoadEnd + Const.CL_LOAD_BIN, Const.CL_LOAD_BIN):
            self.reqGenThread.setArrivalRate(cLoad)
            print("")

            #TODO: get least energy consuming config from all servers
            clusterCfgList = self.serverList.clAgent.getInitConfig(cLoad)  #list {{0,cfg0}, {2,cfg2}, {3,cfg3}}
            self.serverList.activateServersAndCores(clusterCfgList)

            for iter in range(Const.NUM_CL_SAMPLES):
                try:
                    yield self.env.timeout(Const.LONG_SLEEP_TIME)
                except simpy.Interrupt:
                    #Interrupt from Cluster Monitor at epoch end
                    self.collectEnergyStat()
                    clusterEnergyUsageForCurrConfig = self.serverList.energyUsageLastEpoch
                    currPower = float(clusterEnergyUsageForCurrConfig) / self.samplingEpoch
                        
#                    nextCfgList = self.serverList.clAgent.getNextAction(pct95Lat, currPower, reqTput, reqLoad, learning)
                    nextCfgList = self.serverList.clAgent.getNextAction(self.clMonitor.pxLat, currPower, self.reqTput, cLoad, self.learning)   #TODO: HACK only
                    clusterCfgList = nextCfgList
                    
                    self.serverList.activateServersAndCores(clusterCfgList)
                    self.reqGenThread.takeReqCountSnapshot()
                    clusterEnergyUsageForCurrConfig = 0
            self.serverList.clearAllQueues()

            if Const.SIMPY_HEAP_FIX:
                objgraph.show_most_common_types()
                print("\nCleaning up heap of length = {}\n".format(len(self.env._queue)))
                tempQ = []
                for i in range(len(self.env._queue)):
                    if self.env._queue[i][0] <= Const.LONG_SLEEP_TIME:
                        tempQ.append(self.env._queue[i])
                self.env._queue[:] = []
                self.env._queue.extend(tempQ)
                heapify(self.env._queue)
                
        self.CQTable = self.serverList.clAgent.getCQTable()
        print("The CQTable for cluster")
        pprint.pprint(self.serverList.clAgent.getCQTable())
        print("CLLearning completed for the cluster ")
        hlp.save_obj(self.CQTable, "CQTable")
        
        self.exploitRL.interrupt()

                    

    def runSLLearning(self):
        try:
            yield self.env.timeout(Const.LONG_SLEEP_TIME)
        except simpy.Interrupt:
            if Const.DEBUG_SLAGENT: print("SL-Agent learning started")
            self.simProcess = self.slLearning            

        self.allServerQTable = []
        self.learning = True
        self.nextSamplingEpoch = self.samplingEpoch = self.clMonitor.samplingEpoch = Const.SL_SAMPLING_EPOCH

        self.aspsValidConfigsList = hlp.load_obj("aspsValidConfigsList")
        self.aspsValidConfigsEnergyList = hlp.load_obj("aspsValidConfigsEnergyList")
        self.aspsValidConfigsTputList = hlp.load_obj("aspsValidConfigsTputList")
        
        for sid in range(Const.NUM_SERVERS):
            if Const.DEBUG_SLAGENT: print("\nRunning SL Agent for server {}".format(sid))
            minPower = self.aspsValidConfigsEnergyList[sid][0]
            maxPower = self.aspsValidConfigsEnergyList[sid][-1]
            slLoadMin = self.aspsValidConfigsTputList[sid][0]
            slLoadMax = self.aspsValidConfigsTputList[sid][-1]

            slLoadBegin = slLoadMin - (slLoadMin % Const.SL_LOAD_BIN)
            slLoadEnd = slLoadMax - (slLoadMax % Const.SL_LOAD_BIN) + Const.SL_LOAD_BIN
            if (slLoadBegin == 0): slLoadBegin = slLoadBegin + Const.SL_LOAD_BIN
            
            if Const.DEBUG_SLAGENT:
                print("\nslLoadMin = {:.3f}, slLoadMax = {:.3f}, slLoadBegin = {}, slLoadEnd = {}, maxPower = {:.3f}".format(slLoadMin, slLoadMax, slLoadBegin, slLoadEnd, maxPower))

            server = self.serverList.getServer(sid)
            slAgent = slagent.SLAgent(self.env, sid, slLoadBegin, slLoadEnd, Const.SL_LOAD_BIN, self.aspsValidConfigsList[sid], \
                                      Const.TAIL_LATENCY_SLO, minPower, maxPower, slLoadMax)
            server.slAgent = slAgent
            
#            self.resetSim()            
#            self.reqGenThread.setArrivalPattern("poisson")
            if Const.DEBUG_SLAGENT: print("Resetting Simulation")
            self.reqGenThread.halt = 1
            self.clMonitor.halt = 1
            self.clMonitor.action.interrupt()
            self.serverList.clearAllQueues()
            yield self.env.timeout(2 * Const.RESP_AGGREGATION_INTERVAL)
            self.csRespQ.clearQueue()
            self.reqGenThread.halt = 0
            self.clMonitor.halt = 0
            self.reqGenThread.reset()
            self.reqGenThread.setReqTaskSizeType("lognormal")
            self.resetClusterSamplingStats()
            self.reqGenThread.action.interrupt()
            self.clMonitor.action.interrupt()
        
            clusterCfgList = [0, []]*Const.NUM_SERVERS
            clusterCfgList[sid*2] = 1
            clusterCfgList[(sid*2)+1] = self.aspsValidConfigsList[sid][0]
            self.serverList.activateServersAndCores(clusterCfgList)
            
            for sLoad in hlp.frange(slLoadBegin, slLoadEnd + Const.SL_LOAD_BIN, Const.SL_LOAD_BIN):
                if Const.DEBUG_SLAGENT: print("\nRunning SL Agent for load = {} on server {}".format(sLoad, sid))
                self.reqGenThread.setArrivalRate(sLoad)
                minPxLat = Const.LONG_DELAY

                for iter in range(Const.NUM_SL_SAMPLES):
                    if Const.DEBUG_SLAGENT: print("\nIteration ", iter)
                    try:
                        yield self.env.timeout(Const.LONG_SLEEP_TIME)
                    except simpy.Interrupt:
                        #Interrupt from Cluster Monitor at epoch end
                        self.collectEnergyStat()
                        energyUsageForCurrConfig = server.energyUsageLastEpoch
                        currPower = float(energyUsageForCurrConfig) / self.samplingEpoch
                        if Const.DEBUG_SLAGENT:
                            print("Energy = {:.3f} for {} packets in {} secs".format(server.energyUsageLastEpoch, self.respCount, self.samplingEpoch))
                        
                        nextCfg = slAgent.getNextAction(self.clMonitor.pxLat, currPower, self.reqTput, self.reqLoad, self.learning)
                        clusterCfgList[(sid*2)+1] = nextCfg
                        self.serverList.activateServersAndCores(clusterCfgList)
                        self.serverList.clearAllQueues()
                        self.reqGenThread.takeReqCountSnapshot()
                        if Const.DEBUG_SLAGENT: print("csRespQLen before next epoch = ", self.csRespQ.getCurrentQlen())
                        
                        if self.clMonitor.pxLat < minPxLat:
                            minPxLat = self.clMonitor.pxLat
                            
                if (minPxLat > Const.TAIL_LATENCY_SLO):
                    if Const.DEBUG_WARN: print("Min pct latency for load {} was {}".format(sLoad, minPxLat))
                    break

                if Const.SIMPY_HEAP_FIX:
                    objgraph.show_most_common_types()
                    print("\nCleaning up heap\n")
                    tempQ = []
                    for i in range(len(self.env._queue)):
                        if self.env._queue[i][0] <= Const.LONG_SLEEP_TIME:
                            tempQ.append(self.env._queue[i])
                    self.env._queue[:] = []
                    self.env._queue.extend(tempQ)
                    heapify(self.env._queue)
                
            if self.serverList.homogeneousCluster:
                for id in range(Const.NUM_SERVERS):
                    self.allServerQTable.append(slAgent.getQTable())
                break
            else:
                self.allServerQTable.append(slAgent.getQTable())
            
        if Const.DEBUG_DETAILED: 
            for sid in range(Const.NUM_SERVERS):
                print("\n\nThe QTable for server ", sid)
                pprint.pprint(self.allServerQTable[sid])
        
        hlp.save_obj(self.allServerQTable, "allServerQTable")
        if Const.DEBUG_DETAILED:
            for sid in range(Const.NUM_SERVERS):
                hlp.printMaxValuedServerConfigs(sid, self.serverList.getServer(sid).getQTable(), self.aspsValidConfigsList, self.aspsValidConfigsTputList)
                
        print("Completed SL Learning")
        self.clLearning.interrupt()



    def collectConfigStats(self):
        numSamples = 5
        configsResultDictList = [{}]
        configsEnergyDictList = [{}]
        
        self.reqGenThread.setReqTaskSizeType("fixed")
        self.nextSamplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.clMonitor.samplingEpoch = Const.DEF_SAMPLING_EPOCH
        self.samplingEpoch = self.clMonitor.samplingEpoch
        
        for sid in range(Const.NUM_SERVERS):
            for cfg in self.allServerPSConfigsList[sid]:
                if Const.DEBUG_GREENMGR: print("Collecting Config Stats for ", cfg)
                avgEnergyUsageForCurrConfig = 0
                avgRespCount = 0
                clusterCfgList = [0, []]*Const.NUM_SERVERS
                clusterCfgList[sid*2] = 1
                clusterCfgList[(sid*2)+1] = cfg
                self.serverList.activateServersAndCores(clusterCfgList)

                for ctr in range(numSamples):
                    try:
                        yield self.env.timeout(Const.LONG_SLEEP_TIME)
                    except simpy.Interrupt:
                        #Interrupt from Cluster Monitor at epoch end
                        self.collectEnergyStat()
                        self.respCount = self.clMonitor.respCount
                        server = self.serverList.getServer(sid)
                        energyUsageForCurrConfig = server.energyUsageLastEpoch
                        if Const.DEBUG_GREENMGR:
                            print("Energy = {:.3f} for {} packets in {} secs".format(server.energyUsageLastEpoch, self.respCount, self.samplingEpoch))

                        self.serverList.clearAllQueues()
                        self.reqGenThread.takeReqCountSnapshot()
                        avgEnergyUsageForCurrConfig += energyUsageForCurrConfig
                        avgRespCount += self.respCount
                
                avgEnergyUsageForCurrConfig /= numSamples
                avgRespCount /= numSamples
                configsResultDictList[sid][cfg] = avgRespCount / self.samplingEpoch
                configsEnergyDictList[sid][cfg] = avgEnergyUsageForCurrConfig / self.samplingEpoch
                if Const.DEBUG_GREENMGR: print("Cfg = {}, Tput = {}, Energy = {:.3f}".format(cfg, avgRespCount, avgEnergyUsageForCurrConfig))

            if Const.DEBUG_GREENMGR: 
                print("\nCONFIG : THRU_PUT  :  ENERGY_USAGE : TOTAL = {} for sid = {}".format(len(self.allServerPSConfigsList[sid]), sid))
                for cfg in self.allServerPSConfigsList[sid]:
                    print("{}   :  {}   :  {:.3f}".format(cfg, configsResultDictList[sid][cfg], configsEnergyDictList[sid][cfg]))

            thisValidConfigsList = []
            thisValidConfigsEnergyList = []
            thisValidConfigsTputList = []
            
            if Const.SIMPY_HEAP_FIX:
                tempQ = []
                for i in range(len(self.env._queue)):
                    if self.env._queue[i][0] <= Const.LONG_SLEEP_TIME:
                        tempQ.append(self.env._queue[i])
                self.env._queue[:] = []
                self.env._queue.extend(tempQ)
                heapify(self.env._queue)
                
            # sorting the e-SCs
            prevCfg = self.allServerPSConfigsList[sid][0]
            for idx in range(1, len(self.allServerPSConfigsList[sid])):
                currCfg = self.allServerPSConfigsList[sid][idx]
                if (configsResultDictList[sid][prevCfg] < configsResultDictList[sid][currCfg]):
                    thisValidConfigsList.append(prevCfg)
                    thisValidConfigsEnergyList.append(configsEnergyDictList[sid][prevCfg])
                    thisValidConfigsTputList.append(configsResultDictList[sid][prevCfg])
                    prevCfg = currCfg
            if (configsResultDictList[sid][prevCfg] > configsResultDictList[sid][thisValidConfigsList[-1]]): 
                thisValidConfigsList.append(prevCfg)
                thisValidConfigsEnergyList.append(configsEnergyDictList[sid][prevCfg])
                thisValidConfigsTputList.append(configsResultDictList[sid][prevCfg])

            if self.serverList.homogeneousCluster:
                for id in range(Const.NUM_SERVERS):
                    self.aspsValidConfigsList.append(thisValidConfigsList)
                    self.aspsValidConfigsEnergyList.append(thisValidConfigsEnergyList)
                    self.aspsValidConfigsTputList.append(thisValidConfigsTputList)
                break
            else:
                self.aspsValidConfigsList.append(thisValidConfigsList)
                self.aspsValidConfigsEnergyList.append(thisValidConfigsEnergyList)
                self.aspsValidConfigsTputList.append(thisValidConfigsTputList)

        if Const.DEBUG_DETAILED: 
            for sid in range(Const.NUM_SERVERS):
                print("\nList of {} valid configuration sorted by power usage for server {}".format(len(self.aspsValidConfigsList[sid]), sid))
                for cfg in self.aspsValidConfigsList[sid]:
                    idx = self.aspsValidConfigsList[sid].index(cfg)
                    print(cfg, configsResultDictList[sid][cfg], configsEnergyDictList[sid][cfg])

        self.lbThread.allServersConfigList = self.aspsValidConfigsList
        self.lbThread.configTputInfo = self.aspsValidConfigsTputList
        self.lbThread.setLbAlgorithm("ratio")
        self.lbThread.configTputInfoAvailable = True
        
        hlp.save_obj(self.aspsValidConfigsList, "aspsValidConfigsList")
        hlp.save_obj(self.aspsValidConfigsEnergyList, "aspsValidConfigsEnergyList")
        hlp.save_obj(self.aspsValidConfigsTputList, "aspsValidConfigsTputList")
        
        self.slLearning.interrupt()