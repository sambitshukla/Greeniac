# -*- coding: utf-8 -*-
"""
Created on Mon Sep 17 19:06:10 2018

@author: sambit
"""
import itertools
import numpy as np

#cost = [3, 4, 14, 18, 3, 4, 14, 18, 3, 4, 14, 18, 3, 4, 14, 18]  #energy = minimize sum of energy
#weight = [2, 4, 5, 7, 2, 4, 5, 7, 2, 4, 5, 7, 2, 4, 5, 7]  #size = N, thruput, sum of thruput should be less than aggr req rate
##weight = [7, 10, 14, 20, 7, 10, 14, 20, 7, 10, 14, 20, 7, 10, 14, 20]  #thruput, sum of thruput should be less than aggr req rate
#group =  [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]  #serverID
#maxAggrReqRate = 14    #aggr req rate

INF = 1000000

class MCKProblem(object):
    def __init__(self, env, maxAggrReqRate, loadBinSize, aspsValidConfigsList, aspsValidConfigsEnergyList, aspsValidConfigsTputList):
        self.env = env
        self.maxAggrReqRate = maxAggrReqRate
        self.allConfigsList = aspsValidConfigsList
        self.cqTable = {}
        self.cost = list(itertools.chain.from_iterable(aspsValidConfigsEnergyList))
        self.weight = list(itertools.chain.from_iterable(aspsValidConfigsTputList))
        self.configs = list(itertools.chain.from_iterable(self.allConfigsList))
        self.group = []
        self.loadBinSize = loadBinSize
        self.costMatrix = []
        self.solution = []
        self.numConfigs = len(self.configs)
        
        self.weight = [round(float(x)/self.loadBinSize) for x in self.weight]
        self.maxAggrReqRate = round(self.maxAggrReqRate/self.loadBinSize)
        
        for sid in range(len(self.allConfigsList)):
            self.group.extend([sid]*len(self.allConfigsList[sid]))
        self.costMatrix = [[] for i in range(self.numConfigs)]
        self.solution = [[] for i in range(self.numConfigs)]

        
    def getMaxConfigList(self, nextConfig):
        for i in range(int((len(nextConfig))/2)):
            nextConfig[i*2] = 1
            nextConfig[(i*2) + 1] = self.allConfigsList[i][-1]
        return nextConfig
        
        
    def groupMin(self, groupid, w, n):
        min = INF;
        for i in range(n):
            if (self.group[i] == groupid):
                if (self.costMatrix[i][w] < min):
                    min = self.costMatrix[i][w]
        return min   
    
    
    def traceConfigs(self, cLoad, optConfigList):
        j = int(cLoad/self.loadBinSize)
        i = self.numConfigs-1
        
        if (j >= self.maxAggrReqRate):
            return self.getMaxConfigList(optConfigList)
        
        while (i >= 0):
#            print("i = {}, j = {}".format(len(self.solution), len(self.solution[0])))
            if self.solution[i][j] == True:
#                print("Server {}, Config {} - {} included".format(self.group[i], i, self.configs[i]))
                optConfigList[(self.group[i] * 2)] = 1
                optConfigList[(self.group[i] * 2) + 1] = self.configs[i]
                wt = self.weight[i]
                j = int(round(j - wt))  #TODO: Ceil or Floor instead of round
                if j <= 0:
                    break
                
                currGroup = self.group[i]
                while i >= 0 and (currGroup == self.group[i]):
                    i -= 1
            else:
                i -= 1
        return optConfigList
        
    def solveMCKP(self):
        print("Max Weight = {}".format(self.maxAggrReqRate))
        for i in range(self.numConfigs):
            self.costMatrix[i] = [INF]*(int(self.maxAggrReqRate) + 1)
            self.solution[i] = [False]*(int(self.maxAggrReqRate) + 1)
            self.costMatrix[i][0] = 0
        print("Max Weight = {}, row len = {}".format(self.maxAggrReqRate, len(self.solution[0])))

        
#        print("\nValue matrix is")
#        for i in range(len(self.costMatrix)):
#            print("{:2.0f} {:2.0f} ".format(self.cost[i], self.weight[i]), self.costMatrix[i])
#        
#        print("\nSolution matrix is")
#        for i in range(len(self.solution)):
#            print("{:2.0f} {:2.0f} ".format(self.cost[i], self.weight[i]), self.solution[i])
#        
        
        for n in range(self.numConfigs):
            for w in range(1, int(self.maxAggrReqRate) + 1):
                if self.group[n] == 0:
                    if self.weight[n] < w:
                        self.solution[n][w] = False
                        self.costMatrix[n][w] = INF
                    else:
                        opt1 = self.costMatrix[n-1][w]
                        opt2 = self.cost[n]
                        if opt1 < opt2:
                            self.costMatrix[n][w] = opt1
                            self.solution[n][w] = False
                        else:
                            self.costMatrix[n][w] = opt2
                            self.solution[n][w] = True
                else:
                    opt1 = self.costMatrix[n-1][w]
                    opt2 = self.cost[n] + self.groupMin(self.group[n]-1, int(round(w-self.weight[n])), n)   # Check if ceil or floor to be taken instead of rounding
                    if opt1 <= opt2:
                        self.costMatrix[n][w] = opt1
                        self.solution[n][w] = False
                    else:
                        self.costMatrix[n][w] = opt2
                        self.solution[n][w] = True
                        
        
                        
         
#        print("\nValue matrix is")
#        for i in range(len(self.costMatrix)):
#            print("{:2.0f} {:2.0f} ".format(self.cost[i], self.weight[i]), self.costMatrix[i])
#        
#        print("\nSolution matrix is")
#        for i in range(len(self.solution)):
#            print("{:2.0f} {:2.0f} ".format(self.cost[i], self.weight[i]), self.solution[i])
#

        print("\nCost    Weight    Group    Config")
        for i in range(len(self.costMatrix)):
            print("{:2.0f}   {:2.0f}   {}   {} ".format(self.cost[i], self.weight[i], self.group[i], self.configs[i]))

#        print("\nValue partial matrix is")
#        for i in range(len(self.costMatrix)):
#           print(round(self.cost[i],2), self.weight[i], [round(c/100, 1) for c in self.costMatrix[i]][0:36])

