import random
import operator
import sys


from Const import Const
import helper as hlp

class SLAgent(object):
#    __slots__ = ('env', 'sid', 'iPID', 'slLoadBegin', 'slLoadEnd', 'configList', 'maxTput', 'minPower', 'maxPower', 'rlStartTime', 'qTable', 'prevAction', 'prevActionID', \
#                 'tailLatSLO', 'loadBinSize', 'LEARNING_FACTOR', 'DISCOUNT_FACTOR', 'SAFE_LIMIT', 'SLACK_LIMIT', 'EXPLORATION_PROBABILITY', \
#                 'HIPSTER_REWARD_FUNCTION', 'DEBUG', 'prevLoad', 'prevLoadBin', 'prevTailLat', 'prevPower', 'nextAction', 'nextActionID')
    def __init__(self, env, sid, slLoadBegin, slLoadEnd, loadBinSize, thisServerValidConfigsList,\
                 tailLatSLO, minPower, maxPower, maxTput, iPID = 0):
        self.env = env
        self.sid = sid
        self.iPID = iPID
        self.slLoadBegin = slLoadBegin
        self.slLoadEnd = slLoadEnd
        self.configList = thisServerValidConfigsList
        self.maxTput = maxTput
        self.maxPower = maxPower
        self.minPower = minPower
        self.rlStartTime = self.env.now
        self.qTable = {}
        self.prevAction = thisServerValidConfigsList[0]
        self.prevActionID = 0
        self.tailLatSLO = tailLatSLO
        self.loadBinSize = loadBinSize
        
        self.LEARNING_FACTOR = 0.9
        self.DISCOUNT_FACTOR = 0.2
        self.SAFE_LIMIT = 0.8
        self.SLACK_LIMIT = 0.2
        self.EXPLORATION_PROBABILITY = 0.995
        self.HIPSTER_REWARD_FUNCTION = False
        self.DEBUG = 1
        
        for sLoad in hlp.frange(self.loadBinSize, (self.slLoadEnd + 0.1), self.loadBinSize):
            thisMABActionValueDict = {}
            if sLoad < self.slLoadBegin:
                thisMABActionValueDict[self.configList[0]] = [10, 1, self.SLACK_LIMIT*tailLatSLO, self.minPower]  # positive value set to lowest power config for loads < slLoadBegin
#                thisMABActionValueDict[self.configList[0]] = 1  # positive value set to lowest power config for loads < slLoadBegin
#            else:
#                thisMABActionValueDict[self.configList[0]] = -1000  # initialize lowest conf reward to -inf, initialize all load/state values in dict
            self.qTable[sLoad] = thisMABActionValueDict


    def determineLoadBin(self, processedLoad):
        sLoad = 0
        if (processedLoad % self.loadBinSize) > (self.loadBinSize / 2.0):
            sLoad = processedLoad - (processedLoad % self.loadBinSize) + self.loadBinSize
        else:
            sLoad = processedLoad - (processedLoad % self.loadBinSize)
#        sLoad = processedLoad - (processedLoad % self.loadBinSize) + self.loadBinSize
        if Const.DEBUG_SLAGENT: print("The Load bin for {} is {}".format(processedLoad, sLoad))
        return sLoad


    def updateReward(self, reward, tailLat, power):
#        if self.prevAction not in self.qTable[self.prevLoadBin]:
#            self.qTable[self.prevLoadBin][self.prevAction] = reward
#        updatedReward = self.qTable[self.prevLoadBin][self.prevAction] + (self.LEARNING_FACTOR * (reward - self.qTable[self.prevLoadBin][self.prevAction]))
#        self.qTable[self.prevLoadBin][self.prevAction] = updatedReward
        updatedReward = reward
        if self.prevAction not in self.qTable[self.prevLoadBin]:
            self.qTable[self.prevLoadBin][self.prevAction] = [1, updatedReward, tailLat, power]
        else:
            #NewEstimate = OldEstimate + StepSize [Target - OldEstimate]
            prevSampleCount = self.qTable[self.prevLoadBin][self.prevAction][0]
            prevReward = self.qTable[self.prevLoadBin][self.prevAction][1]
            prevTailLat = self.qTable[self.prevLoadBin][self.prevAction][2]
            prevPower = self.qTable[self.prevLoadBin][self.prevAction][3]
#            prevPower = power
#            prevTailLat = tailLat
            
            updatedSampleCount = prevSampleCount + 1
            updatedReward = prevReward + ((1.0 / updatedSampleCount) * (reward - prevReward))
            updatedTailLat = prevTailLat + ((1.0 / updatedSampleCount) * (tailLat - prevTailLat))
            updatedPower = prevPower + ((1.0 / updatedSampleCount) * (power - prevPower))
            self.qTable[self.prevLoadBin][self.prevAction] = [updatedSampleCount, updatedReward, updatedTailLat, updatedPower]

        if Const.DEBUG_SLAGENT: print("Updated Reward = {:.3f} for State = {} Action = {}".format(updatedReward, self.prevLoadBin, self.prevAction))


    def calculateReward(self, tailLat, power, processedLoad):
        self.prevLoad = processedLoad
        self.prevLoadBin = self.determineLoadBin(processedLoad)
        if self.prevLoadBin not in self.qTable:
            if Const.DEBUG_SLAGENT: print("load = {} not in qTable keys {}".format(self.prevLoadBin, self.qTable.keys()))
            self.qTable[self.prevLoadBin] = {}
        self.prevTailLat = tailLat
        self.prevPower = power
        
        tailLatReward = float(self.prevTailLat) / self.tailLatSLO
        if (self.prevTailLat > (self.SAFE_LIMIT*self.tailLatSLO)) and (self.prevTailLat < self.tailLatSLO):
            tailLatReward = tailLatReward - random.uniform(0, 1)
          
        if (self.HIPSTER_REWARD_FUNCTION):
            powerReward = float(self.maxPower) / float(self.prevPower)
        else:
            powerReward = float(self.maxPower - self.prevPower)*2 / float(self.maxPower)
            
        if (self.HIPSTER_REWARD_FUNCTION):
            if (self.prevTailLat < self.tailLatSLO):
                reward = powerReward + tailLatReward + 1
            else:
                reward = powerReward - tailLatReward - 1
                tailLatReward = -tailLatReward
        else:
            if (self.prevTailLat < self.tailLatSLO):
                reward = powerReward + tailLatReward + 1
            else:
                reward = powerReward - tailLatReward - (10 * (tailLatReward - 1))
                tailLatReward = -tailLatReward
            
        if Const.DEBUG_SLAGENT: print("Tail Reward = {:.3f}, Power Reward = {:.3f}, Total Reward = {:.3f}".format(tailLatReward, powerReward, reward))
        if Const.DEBUG_SLAGENT: print("Reward for Load = {}, power = {:.3f}, tail latency = {:.3f} is {:.3f}".format(self.prevLoad, self.prevPower, self.prevTailLat, reward))
        return reward


    def getSLHeuristicAction(self):
        nextAction = []
        nextActionID = self.prevActionID
        if (self.prevTailLat > (self.SAFE_LIMIT*self.tailLatSLO)):
            if (self.prevActionID < (len(self.configList) - 1)):
                nextActionID = self.prevActionID + 1
        elif (self.prevTailLat < (self.SLACK_LIMIT*self.tailLatSLO)):
            if (self.prevActionID > 0):
                nextActionID = self.prevActionID - 1
        
        nextAction = self.configList[nextActionID]
        if Const.DEBUG_SLAGENT: print("The next action for latency = {:.3f}, has ID = {}, is {}".format(self.prevTailLat, nextActionID, nextAction))
        return nextActionID

            
    def getPolicyAction(self):
        nextAction = []
        nextActionID = self.prevActionID
        if random.random() > self.EXPLORATION_PROBABILITY:
            nextAction = random.choice(self.configList)
            nextActionID = self.configList.index(nextAction)
            if self.DEBUG: print("Random index {} config {} chosen".format(nextActionID, nextAction))
        else:
            #nextAction = max(self.qTable[self.prevLoad], self.qTable[self.prevLoad].get)
            val = max(self.qTable[self.prevLoad].values(), key=operator.itemgetter(1))
            for k, v in self.qTable[self.prevLoad].items():
                if v == val:
                    nextAction = k
                    break
            if (nextAction == []):
                if Const.DEBUG_SLAGENT: print("ALERT !!!! No Most weighted config found")
                sys.exit("ALERT !!!! No Most weighted config found")
                
            nextActionID = self.configList.index(nextAction)
            if Const.DEBUG_SLAGENT: print("Most weighted index {} config {} chosen".format(nextActionID, nextAction))
        return nextActionID


    def getQTable(self):
        return self.qTable


    def getNextAction(self, tailLat, power, processedLoad, reqLoad, isLearning):
        #reward = self.calculateReward(tailLat, power, processedLoad)
        reward = self.calculateReward(tailLat, power, reqLoad)
        self.updateReward(reward, tailLat, power)

        if (isLearning):
            self.nextActionID = self.getSLHeuristicAction()
        else:
            self.nextActionID = self.getPolicyAction()
            
        self.nextAction = self.configList[self.nextActionID]
        self.prevActionID = self.nextActionID
        self.prevAction = self.nextAction
        return self.nextAction