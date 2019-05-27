import random
import mckp
import operator
import sys
import helper as hlp
from Const import Const

class CLAgent(object):
    def __init__(self, env, clLoadBegin, clLoadEnd, maxPower, maxTput, loadBinSize, aspsValidConfigsList, aspsValidConfigsEnergyList, \
                 aspsValidConfigsTputList, allServerQTable, tailLatSLO, samplingEpoch, numServers):
        self.env = env
        self.clLoadBegin = clLoadBegin
        self.clLoadEnd = clLoadEnd
        self.loadBinSize = loadBinSize
        self.aspsValidConfigsList = aspsValidConfigsList
        self.aspsValidConfigsEnergyList = aspsValidConfigsEnergyList
        self.aspsValidConfigsTputList = aspsValidConfigsTputList
        self.maxTput = maxTput
        self.maxPower = maxPower
        self.allServerQTable = allServerQTable
        self.tailLatSLO = tailLatSLO
        self.samplingEpoch = samplingEpoch
        self.numServers = numServers
        self.cqTable = {}

        self.LEARNING_FACTOR = 0.9
        self.DISCOUNT_FACTOR = 0.2
        self.SAFE_LIMIT = 0.8
        self.SLACK_LIMIT = 0.2
        self.EXPLORATION_PROBABILITY = 0.995
        self.HIPSTER_REWARD_FUNCTION = False
        self.DEBUG = 1
        
#        self.aspsValidConfigsEnergyList = [float(x)/self.samplingEpoch for x in self.aspsValidConfigsEnergyList]
#        self.aspsValidConfigsTputList = [float(x)/self.samplingEpoch for x in self.aspsValidConfigsTputList]

        defaultClusterCfgList = [0, ()]*self.numServers
        defaultClusterCfgList[0] = 1
        defaultClusterCfgList[1] = tuple(self.aspsValidConfigsList[0][0])   #TODO: Find least energy configuration for heterogenous cluster
        if Const.DEBUG_CLAGENT: print("Setting Default config to {}".format(defaultClusterCfgList))
        for cLoad in hlp.frange(self.loadBinSize, self.clLoadEnd + 1, self.loadBinSize):
            thisMABActionValueDict = {}
            if cLoad < self.clLoadBegin:
                thisMABActionValueDict[tuple(defaultClusterCfgList)] = [1.0, 10]  #[a, b], b = number of samples, positive reward value a set to lowest power config for loads < slLoadBegin
            self.cqTable[cLoad] = thisMABActionValueDict
            if Const.DEBUG_CLAGENT: print("Setting Default config for {} to {}".format(cLoad, thisMABActionValueDict))

        #one-time knapsack Logic for all load ranges in cluster
        self.mckpSolver = mckp.MCKProblem(self.env, self.clLoadEnd, self.loadBinSize, \
            self.aspsValidConfigsList, self.aspsValidConfigsEnergyList, self.aspsValidConfigsTputList)
        self.mckpSolver.solveMCKP()
    

    def getInitConfig(self, cLoad):
        nextAction = [0, []]*self.numServers  # select max config as default        
        nextAction = self.mckpSolver.traceConfigs(cLoad, nextAction)
        self.expectedLoad = cLoad
        self.prevAction = nextAction
        if Const.DEBUG_CLAGENT: print("The Init Config for Avg Load = {}, is {}".format(cLoad, nextAction))
        return nextAction

        
    def getCQTable(self):
        return self.cqTable


    def updateReward(self, reward):
        updatedReward = reward
        prevActionTuple = hlp.getActionTuple(self.prevAction)
        if prevActionTuple not in self.cqTable[self.prevLoadBin]:
            self.cqTable[self.prevLoadBin][prevActionTuple] = [updatedReward, 1]
        #TODO: Avoid Learning rate. Use sample average.
        else:
            #NewEstimate = OldEstimate + StepSize [Target - OldEstimate]
#            updatedReward = self.cqTable[self.prevLoadBin][prevActionTuple] + (self.LEARNING_FACTOR * (reward - self.cqTable[self.prevLoadBin][prevActionTuple]))
#            self.cqTable[self.prevLoadBin][prevActionTuple] = updatedReward
            prevReward = self.cqTable[self.prevLoadBin][prevActionTuple][0]
            prevSampleCount = self.cqTable[self.prevLoadBin][prevActionTuple][1]
            updatedSampleCount = prevSampleCount + 1
            updatedReward = prevReward + ((1.0 / updatedSampleCount) * (reward - prevReward))
            self.cqTable[self.prevLoadBin][prevActionTuple] = [updatedReward, updatedSampleCount]
            
        if Const.DEBUG_CLAGENT: print("Updated Reward = {:.3f} for State = {} Action = {}".format(updatedReward, self.prevLoadBin, self.prevAction))


    def calculateReward(self, tailLat, power, measuredLoad):
        self.prevLoad = measuredLoad
        self.prevLoadBin = hlp.determineLoadBin(measuredLoad, self.loadBinSize)
        if self.prevLoadBin not in self.cqTable:
            if Const.DEBUG_CLAGENT: print("load = {} not in cqTable keys {}".format(self.prevLoadBin, self.cqTable.keys()))
            self.cqTable[self.prevLoadBin] = {}
        self.prevTailLat = tailLat
        self.prevPower = power
        
        tailLatReward = float(self.prevTailLat) / self.tailLatSLO
        if (self.prevTailLat > (self.SAFE_LIMIT*self.tailLatSLO)) and (self.prevTailLat < self.tailLatSLO):
            tailLatReward = tailLatReward - random.uniform(0, 1)
            
        if (self.HIPSTER_REWARD_FUNCTION):
            powerReward = float(self.maxPower) / float(self.prevPower)
        else:
            powerReward = float(self.maxPower - self.prevPower) / float(self.maxPower)

        if (self.HIPSTER_REWARD_FUNCTION):
            if (self.prevTailLat < self.tailLatSLO):
                reward = powerReward + tailLatReward + 1
            else:
                reward = powerReward - tailLatReward - 1
        else:
            if (self.prevTailLat < self.tailLatSLO):
                reward = powerReward + tailLatReward + 1
            else:
                reward = powerReward - tailLatReward - (10 * (tailLatReward - 1))

        if Const.DEBUG_CLAGENT: print("Tail Reward = {:.3f}, Power Reward = {:.3f}, Total Reward = {:.3f}".format(tailLatReward, powerReward, reward))
        if Const.DEBUG_CLAGENT: print("Reward for measured Load = {}, power = {:.3f}, tail latency = {:.3f} is {:.3f}".format(self.prevLoad, self.prevPower, self.prevTailLat, reward))
        return reward


    def getRandomConfig(self):
        clusterCfgList = [0, []]*self.numServers
        for sid in range(self.numServers):
            isActive = random.choice([0,1])
            clusterCfgList[sid*2] = isActive
            if not isActive: continue
            clusterCfgList[(sid*2)+1] = random.choice(self.aspsValidConfigsList[sid])
        return clusterCfgList
        

    def getMaxConfig(self):
        nextConfig = [0, []]*self.numServers
        for i in range(int((len(nextConfig))/2)):
            nextConfig[i*2] = 1
            nextConfig[(i*2) + 1] = self.aspsValidConfigsList[i][-1]
        return nextConfig
        
    
    def getPolicyAction(self):
        nextAction = []
        self.prevLoadBin = hlp.determineLoadBin(self.prevLoad, self.loadBinSize)
        
        if random.random() > self.EXPLORATION_PROBABILITY:
            nextAction = self.getRandomConfig()
            if Const.DEBUG_CLAGENT: print("Random config {} chosen".format(nextAction))
        else:
            if self.prevLoadBin not in self.cqTable:
                nextAction = self.getMaxConfig()
                return nextAction
                
            #nextAction = max(self.cqTable[self.prevLoadBin], self.cqTable[self.prevLoadBin].get)
            val = max(self.cqTable[self.prevLoadBin].values(), key=operator.itemgetter(1))
            for k, v in self.cqTable[self.prevLoadBin].items():
                if v == val:
                    nextAction = k
                    break
            if (nextAction == []):
                print("ALERT !!!! No Most weighted config found")
                nextAction = self.getMaxConfig()
                return nextAction
                
            if Const.DEBUG_CLAGENT: print("Most weighted config {} chosen".format(nextAction))
        nextAction = hlp.getActionFromTuple(nextAction)
        if Const.DEBUG_CLAGENT: print("Converted Config List = {}".format(nextAction))
        return nextAction


    def getNextAction(self, tailLat, power, measuredLoad, reqLoad, isLearning):
        self.reqLoad = reqLoad
        self.prevLoad = reqLoad

        if (isLearning):
#            reward = self.calculateReward(tailLat, power, measuredLoad)     #use reqs processed (Throughput) as Qtable index
            reward = self.calculateReward(tailLat, power, reqLoad)     #use reqs generated (Load) as Qtable index
            self.updateReward(reward)
            self.nextAction = self.getCLHeuristicAction()
        else:
            self.nextAction = self.getPolicyAction()

        self.prevAction = self.nextAction
        if Const.DEBUG_CLAGENT: print("Next action selected = {}".format(self.nextAction))
        return self.nextAction
    
    
    def getCLHeuristicAction(self):
        nextAction = [0, []]*self.numServers
        #TODO: Perform Gradient ascent
        nextAction = self.prevAction
        
        if Const.DEBUG_CLAGENT: print("The next action for tail latency = {:.3f} / {:.3f} and power = {:.3f} / {:.3f}, last Load = {} / {} - {} / {}, is {}".format( \
              self.prevTailLat, self.tailLatSLO, self.prevPower, self.maxPower, self.prevLoad, self.prevLoadBin, self.reqLoad, self.expectedLoad, nextAction))
        return nextAction