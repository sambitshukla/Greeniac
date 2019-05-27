import pickle
import operator
import numpy as np
import pprint

from Const import Const


#--------------------------------------
# Helper Functions For Simulation Flows
#--------------------------------------
def printMaxValuedServerConfigs(sid, sqTable, aspsValidConfigsList, aspsValidConfigsTputList):
    pprint.pprint(sqTable)
    print("")
    optCfgDict = getOptServerCfgDict(sid, aspsValidConfigsList, sqTable)
    for cfg in aspsValidConfigsList[sid]:
        idx = aspsValidConfigsList[sid].index(cfg)
        print(cfg, optCfgDict[cfg], aspsValidConfigsTputList[sid][idx])
    

# Determines the list of load ranges for which each config is the most rewarded action. Returns dict[cfg -> load_bin list]
def getOptServerCfgDict(sid, aspsValidConfigsList, sqTable):
    dict1 = {}
    for cfg in aspsValidConfigsList[sid]:
        dict1[cfg] = []
        
    for loadBin in sqTable.keys():
        nextAction = []
        print("For bin = {}, actions are".format(loadBin))
        rareActions = []
        for k,v in sqTable[loadBin].items():
            print(k, [round(a, 3) for a in v])
            if (v[0] < 2) and (v[2] > (0.5*Const.TAIL_LATENCY_SLO)):   #number of times this config sampled
                rareActions.append(k)

        for key in rareActions:
            sqTable[loadBin].pop(key)
            print("Config {} removed".format(key))

        if not bool(sqTable[loadBin]): continue
        val = max(sqTable[loadBin].values(), key=operator.itemgetter(1))
        for k, v in sqTable[loadBin].items():
            if (v == val) and (v[1] > 0):   #(v[2] < Const.TAIL_LATENCY_SLO)
                nextAction = k
                break
        if bool(nextAction):
            dict1[nextAction].append(loadBin)
    return dict1


#For each cfg determine the max throughput achieved and max energy used for the list of corresponding learnt load_bins
def getLearntConfigs(configsList, energyList, allServerQTable):
    aspsTmpValidConfigsTputList = []
    aspsTmpValidConfigsEnergyList = []
    print("allServerQTable = ", allServerQTable)
    
    for sid in range(Const.NUM_SERVERS):
        tmpValidConfigsTputList = []
        tmpValidConfigsEnergyList = []
        optCfgDict = getOptServerCfgDict(sid, configsList, allServerQTable[sid])
        if Const.DEBUG_DETAILED:
            pprint.pprint(optCfgDict)
        
        prevTputMax = 0
        tputMax = 0
        energyMax = 0
        for idx in range(len(configsList[sid])):
            cfg = configsList[sid][idx]
            if not optCfgDict[cfg]:
                tputMax = prevTputMax
                energyMax = energyList[sid][idx]
            else:
                tputMax = max(optCfgDict[cfg])
                prevTputMax = tputMax
                energyMax = allServerQTable[sid][tputMax][cfg][3]
            tmpValidConfigsTputList.append(tputMax)
            tmpValidConfigsEnergyList.append(energyMax)
            
        for idx in range(len(configsList[sid])):
            print("{} {:.1f} {:.3f}".format(configsList[sid][idx], tmpValidConfigsTputList[idx], tmpValidConfigsEnergyList[idx]))

        aspsTmpValidConfigsTputList.append(tmpValidConfigsTputList)
        aspsTmpValidConfigsEnergyList.append(tmpValidConfigsEnergyList)
        
    return aspsTmpValidConfigsTputList, aspsTmpValidConfigsEnergyList


def testArrivalRatePattern(reqGenThread, pattern, params):
    # test various arrival rate patterns
    # RRrate [maxrate, minrate, step]
    if pattern == "RRrate":
        maxRate = params[0]
        minRate = params[1]
        step = params[2]
        rate = reqGenThread.arrivalRate
        rate += step
        if rate > maxRate:
            rate = minRate + (rate % maxRate)
        reqGenThread.setArrivalRate(rate)
        print("Request rate being updated to ", rate, maxRate, minRate, step)





        
#--------------------------------------
# Helper Functions For Server Configs
#--------------------------------------
def generateAllConfigs(cfgList, sid, coreCountMatrix, cpuNameList):
    for cName in cpuNameList:
        cnameIdx = cpuNameList.index(cName)
        prevCfgListLen = len(cfgList)
        for cpuCount in range(coreCountMatrix[sid][cnameIdx]):
            for tempIdx in range(prevCfgListLen + 1):
                for freq in Const.CPU_FREQ_PROFILES[cName]:
                    tempList = []
                    if (tempIdx != 0): tempList.extend(cfgList[tempIdx - 1])
                    tempList.append(cName)
                    tempList.append(cpuCount + 1)
                    tempList.append(freq)
                    cfgList.append(tempList)

                    
def genSortPwrConfigs(pwrDict, cfgList):
    for cfg in cfgList:
        totalPwr = 0
        for idx in range(0, len(cfg), 3):
            cName = cfg[idx]
            numCores = cfg[idx + 1]
            freq = cfg[idx + 2]
            statPwr = numCores * Const.CPU_POWER_PROFILES[cName][0]
            dynIdx = Const.CPU_FREQ_PROFILES[cName].index(freq)
            dynPwr = numCores * Const.CPU_POWER_PROFILES[cName][dynIdx + 1]
            totalPwr += statPwr + dynPwr
        pwrDict[tuple(cfg)] = totalPwr
    pwrSortedConfigs = sorted(pwrDict, key=pwrDict.get)
    return pwrSortedConfigs





        
#--------------------------------------
# Utility Functions
#--------------------------------------
def listAllCores(serverList):
    # Lists all CPU cores in the system
    print("\nFollowing is the list of all cores in the system")
    for i in range(Const.NUM_SERVERS):
        server = serverList.getServer(i)
        coreList = server.getCoreList()
        for core in range(coreList.coreList):
            print("Core {} of server {} running at frequency {} in server {}".format(core.cid, core.sid, core.currFreq, server.sid))
    print("\n")

   
def displayPctStat(respLatencyList):
    # Calculate tail latency
    pct50 = np.percentile(np.array(respLatencyList), 50)
    pct75 = np.percentile(np.array(respLatencyList), 75)
    pct90 = np.percentile(np.array(respLatencyList), 90)
    pct95 = np.percentile(np.array(respLatencyList), 95)
    pct99 = np.percentile(np.array(respLatencyList), 99)
    if Const.DEBUG: print("""Tail percentile statistics for {} packets in last {} secs :\n50 pct = {:.3f}\n75pct = {:.3f}\n90pct = {:.3f}\n95pct = {:.3f}\n99pct = {:.3f}""".format(len(respLatencyList), Const.SAMPLING_EPOCH, pct50, pct75, pct90, pct95, pct99))


def save_obj(obj, name):
    with open('obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


def getActionTuple(clusterCfgList):
    for i in range(len(clusterCfgList)):
        if isinstance(clusterCfgList[i], list):
            clusterCfgList[i] = tuple(clusterCfgList[i])
    return tuple(clusterCfgList)


def getActionFromTuple(cfgAction):
    action = list(cfgAction)
    for i in range(len(action)):
        if isinstance(action[i], tuple):
            action[i] = list(action[i])
    return action


def cfg2str(clusterCfgList):
    cStr = ""
    numServers = len(clusterCfgList)/2
    for sid in range(numServers):
        if (clusterCfgList[sid*2 + 1] == 0):
            cStr += ":"


def frange(start, stop=None, step=None):
    if stop == None:
        stop = start + 0.0
        start = 0.0
    if step == None:
        step = 1.0
    while start < stop:
        yield start
        start += step





        
#--------------------------------------
# Helper Functions For RL agent
#--------------------------------------
def getMaxClusterCfg(aspsTmpValidConfigsList):
    maxClusterCfg = []
    for sid in range (len(aspsTmpValidConfigsList)):
        maxClusterCfg.extend([1, aspsTmpValidConfigsList[sid][-1]])
    return maxClusterCfg
#    return [1, aspsTmpValidConfigsList[0][-1], 1, aspsTmpValidConfigsList[1][-1], 1, aspsTmpValidConfigsList[2][-1], 1, aspsTmpValidConfigsList[3][-1]]


def determineLoadBin(measuredLoad, loadBinSize):
    cLoad = 0
    if (measuredLoad % loadBinSize) > (loadBinSize / 2.0):
        cLoad = measuredLoad - (measuredLoad % loadBinSize) + loadBinSize
    else:
        cLoad = measuredLoad - (measuredLoad % loadBinSize)
#        cLoad = measuredLoad - (measuredLoad % loadBinSize) + loadBinSize
    print("The Load bin for {} is {}".format(measuredLoad, cLoad))
    return cLoad


def getBestClusterCfg(epochReqCount, clusterCQTable, loadBinSize):
    nextAction = []
    prevLoadBin = determineLoadBin(epochReqCount, loadBinSize)
    if prevLoadBin not in clusterCQTable:
        print("No cluster config found for bin ", prevLoadBin)
        return nextAction
    
    val = max(clusterCQTable[prevLoadBin].values(), key=operator.itemgetter(1))
    for k, v in clusterCQTable[prevLoadBin].items():
        if v == val:
            nextAction = k
            break
    if (nextAction == []):
        print("ALERT !!!! No Most weighted config found")
        
    print("Most weighted config {} chosen".format(nextAction))
    nextAction = getActionFromTuple(nextAction)
    print("Converted Config List = {}".format(nextAction))
    return nextAction





        
#-----------------------------------------
# Helper Functions For non-Greeniac Flows
#-----------------------------------------
def getEquiDistClusterCfg(cLoad, optCfgDict, loadBinSize, numServers):
    print("Identifying Config for Equi-Dist in cluster")
    clusterCfgList = [0, []]*numServers
    eachServerLoad = float(cLoad) / numServers
    eachServerLoadBin = eachServerLoad - (eachServerLoad % loadBinSize) + loadBinSize
    print("Identifying Config for Equi-Dist in cluster", eachServerLoadBin, optCfgDict.items())

    allLoads = []
    for k,v in optCfgDict.items(): allLoads.extend(v)
    minServerLoad = min(allLoads)
    if (eachServerLoadBin < minServerLoad):
        eachServerLoadBin = minServerLoad

    cfgList = [k for k, v in optCfgDict.items() if eachServerLoadBin in v]
    if not bool(cfgList):
        print("No Config found for bin ", eachServerLoadBin)
        return []
    
    cfg = cfgList[0]
    print("Found Config for Equal Distribution in cluster ", cfg)
    for sid in range(4):
        clusterCfgList[sid*2] = 1
        clusterCfgList[(sid*2)+1] = list(cfg)
    return clusterCfgList


def getBinPackClusterCfg(cLoad, optCfgDict, numServers):
    clusterCfgList = [0, []]*numServers
    #TODO: Fix to support heterogenous clusters
    allLoads = []
    for k,v in optCfgDict.items(): allLoads.extend(v)
    maxServerLoad = max(allLoads)
    minServerLoad = min(allLoads)
    
    print("Identifying Config for BinPacking in server")
    if cLoad > maxServerLoad * len(clusterCfgList)/2:
        cLoad = maxServerLoad
    for sid in range(len(clusterCfgList)/2):
        nextServerLoad = 0
        if cLoad <= 0:
            break
        if cLoad < maxServerLoad:
            nextServerLoad = cLoad 
            cLoad = 0
        else:
            cLoad -= maxServerLoad
            nextServerLoad = maxServerLoad
            
        if nextServerLoad < minServerLoad:
            nextServerLoad = minServerLoad
            
        cfg = [k for k, v in optCfgDict.items() if nextServerLoad in v][0]
        print("Found Config for BinPacking in server ", sid, cfg)
        clusterCfgList[sid*2] = 1
        clusterCfgList[(sid*2)+1] = list(cfg)
    print("Cluster Config for load {} for BinPacking is {}".format(cLoad, clusterCfgList))
    return clusterCfgList





        
#--------------------------------------
# Helper Functions For Load Balancer
#--------------------------------------
def getLoadRatio(clusterCfgList, configTputInfo, cfgList, numServers):
    ratio = [1]*numServers
    tputs = [1]*numServers
    for sid in range(int(len(clusterCfgList)/2)):
        if clusterCfgList[sid*2] == 0:
            tputs[sid] = 0
        else:
            cfgId = cfgList[sid].index(tuple(clusterCfgList[(sid*2) + 1]))
            tputs[sid] = configTputInfo[sid][cfgId]
    aggrTput = sum(tputs)
    print("Throughputs for config {} are {}".format(clusterCfgList, tputs))
    if (aggrTput == 0):
        tputs = [0]*len(tputs)
    else:
        tputs[:] = [float(x)/aggrTput for x in tputs]
    print("Normalized throughputs are {}".format(tputs))
    
    total = 0
    for sid in range(len(tputs)):
        total += tputs[sid]
        ratio[sid] = total
    
    print("Final LB ratios are {}".format(ratio))
    if (ratio[-1] != 0):
        ratio[-1] = 1
    print("Final LB ratios are {}".format(ratio))
    return ratio