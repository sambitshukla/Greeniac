#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 13:13:47 2018

@author: sambit
"""

# List of cores in each server        
class CoreList:
    __slots__ = ('env', 'coreList', 'sid', 'numCores', 'activeCoreCount')
    def __init__(self, env, sid):
        self.env = env
        self.coreList = []
        self.sid = sid
        self.numCores = 0
        self.activeCoreCount = 0
        
    def addtoList(self, core):
        self.coreList.append(core)
        self.numCores += 1

    def clearList(self):
        self.coreList[:] = []
        self.numCores = 0
        
    def getNumActiveCores(self):
        self.activeCoreCount = 0
        for core in self.coreList:
            if (core.active == 1):
                self.activeCoreCount += 1
        return self.activeCoreCount
        
    def getCore(self, index):
        return self.coreList[index]
                
    def getCoreByName(self, cpuName):
        for core in self.coreList:
            if (core.cpuName == cpuName):
                return core
