#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 13:24:35 2018

@author: sambit
"""
from Const import Const
import simpy


class TaskScheduler(object):
#    __slots__ = ('env', 'sid', 'serverReqQ', 'coreList', 'mostRecentCoreId', 'idling', 'action', 'wakeupCore')
    def __init__(self, env, serverReqQ, coreList, sid):
        self.env = env
        self.sid = sid
        self.serverReqQ = serverReqQ
        self.coreList = coreList
        self.mostRecentCoreId = 0
        self.idling = 1
        self.schedAlgo = "rr"
        self.action = self.env.process(self.run())
        
        
    def getNextScheduleCore(self, availCores):
        # TODO: Implement SCHEDULING POLICY HERE
        noSchedCore = True
        nextCoreId = -1
        if Const.DEBUG_TSCHED: print("schedAlgo is ", self.schedAlgo)
        
        # single core only
        if self.schedAlgo == "fixed":
            nextCoreId = 0

        # FCFS with priority for small core
        elif self.schedAlgo == "fcfs-small":
            for coreId in availCores:
                if (self.coreList.getCore(coreId).cpuName == Const.ATOM_STR):
                    nextCoreId = coreId
                    break
                else:
                    nextCoreId = coreId
            if nextCoreId != -1:
                noSchedCore = False
            if Const.DEBUG_TSCHED:
                print("Next core Id is ", nextCoreId)
            
        # FCFS with priority for big core
        elif self.schedAlgo == "fcfs-big":
            for coreId in availCores:
                if (self.coreList.getCore(coreId).cpuName != Const.ATOM_STR):
                    nextCoreId = coreId
                    break
                else:
                    nextCoreId = coreId
            if nextCoreId != -1:
                noSchedCore = False
            if Const.DEBUG_TSCHED:
                print("Next core Id is ", nextCoreId)
            
        # round-robin core scheduling
        elif self.schedAlgo == "rr":
            if (self.mostRecentCoreId >= availCores[-1]):
                nextCoreId = availCores[0]
                noSchedCore = False
            else:
                for cid in availCores:
                    if cid > self.mostRecentCoreId:
#                        nextCoreId = availCores[cid]
                        nextCoreId = cid
                        noSchedCore = False
                        break

        if noSchedCore:
            return None
        self.mostRecentCoreId = nextCoreId
        return self.coreList.getCore(self.mostRecentCoreId)


    def getSchedReadyCores(self):
        availCores = []
        for core in self.coreList.coreList:
            if core.active == 0: continue
            if Const.CUSTOM_CORE_TASK_SCHEDULING and (core.cid not in Const.CORE_MASK_LIST): continue
            if (core.idling == 1) or (len(core.taskQ) < Const.MAX_TASKQ_LEN):
                availCores.append(core.cid)
        return availCores
                
    def run(self):
        if Const.DEBUG_INIT: print("Task Scheduler thread started for server {}".format(self.sid))
        while True:
            try:
                yield self.env.timeout(Const.LONG_SLEEP_TIME)
            except simpy.Interrupt:
                # Enqueue req to active cores as per scheduling algorithm as long as queue is not empty or all active core task queues are full
                self.idling = 0
                if Const.DEBUG_TSCHED: print("Task scheduler of Server {} interrupted".format(self.sid))
                
                while (self.serverReqQ.getCurrentQlen() > 0):
                    schedReadyCores = self.getSchedReadyCores()
                    if Const.DEBUG_TSCHED: print("Cores ready for scheduling are ", schedReadyCores)
                    if (len(schedReadyCores) == 0): break
                
                    self.wakeupCore = self.getNextScheduleCore(schedReadyCores)
                    if (self.wakeupCore == None): break
                    if Const.DEBUG_TSCHED: print("Next core to wake up is ", self.wakeupCore.cid)
                    
                    req = self.serverReqQ.dequeueRequest()
                    self.wakeupCore.enqueueTask(req)
                    if Const.DEBUG_TSCHED: print("Task scheduler of Server {} pushed req {} to core {} queue of length {}".format(self.sid, req.id, self.wakeupCore.cid, len(self.wakeupCore.taskQ)))
                    
                    if (self.wakeupCore.idling == 1):
                        if Const.DEBUG_TSCHED: print("Task scheduler of Server {} interrupting core {} of server {}".format(self.sid, self.wakeupCore.cid, self.wakeupCore.sid))
                        self.wakeupCore.idling = 0
                        self.wakeupCore.action.interrupt()
                
                self.idling = 1
                if Const.DEBUG_TSCHED: print("Task scheduler of Server {} going to sleep".format(self.sid))                
                