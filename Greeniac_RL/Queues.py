# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 11:03:14 2018

@author: sambit
"""
from Const import Const

class Queue(object):
    "Generic request queue per server from which Cores pick requests"
#    __slots__ = ('env', 'maxQlen', 'reqQueue', 'qLen', 'qId', 'sid')
    def __init__(self, env):
        self.env = env
        self.maxQlen = Const.DEF_QSIZE
        self.reqQueue = []
        self.qLen = 0
        self.qId = 0
        self.sid = -1
        
    def enqueueRequest(self, request):
        self.qLen = len(self.reqQueue)
        if self.qLen == self.maxQlen:
            if Const.DEBUG_QUEUE: print ("ALERT!! :: Max Qlength {} reached for Queue type {} on server {}. Dropping packet {}".format(self.qLen, self.qId, self.sid, request.id))
        else: 
            self.reqQueue.append(request)
            self.qLen += 1
        
    def dequeueRequest(self):
        self.qLen = len(self.reqQueue)
        if self.qLen == 0:
            if Const.DEBUG_QUEUE: print ("ALERT!! :: Empty Queue for Queue type {} on server {}".format(self.qId, self.sid))
            return None
        else:
            request = self.reqQueue.pop(0)
            self.qLen -= 1
            return request
        
    def getCurrentQlen(self):
        self.qLen = len(self.reqQueue)
        return self.qLen
        
    def clearQueue(self):
        if Const.DEBUG_QUEUE: print("Dropping {} packets from Queue {} of server {}".format(len(self.reqQueue), self.qId, self.sid))
        self.reqQueue[:] = []
        self.qLen = 0
        

        
class ServerReqQ(Queue):
    __slots__ = ('env', 'qId', 'sid')
    "Server Receive Queue"
    def __init__(self, env, sid):
        Queue.__init__(self, env)
        self.qId = 1
        self.sid = sid    #server associated with the queue: sid
        if Const.DEBUG_INIT: print("ServerReqQ for Server {} initialized".format(self.sid))
        
class ServerRespQ(Queue):
    __slots__ = ('env', 'qId', 'sid')
    "Server Response Queue"
    def __init__(self, env, sid):
        Queue.__init__(self, env)
        self.qId = 2
        self.sid = sid    # server associated with the queue
        if Const.DEBUG_INIT: print("ServerRespQ for Server {} initialized".format(self.sid))
        
class CSReqQ(Queue):
    __slots__ = ('env', 'qId')
    "Centralized Scheduler Response Queue"
    def __init__(self, env):
        Queue.__init__(self, env)
        self.qId = 3
        if Const.DEBUG_INIT: print("CSReqQ initialized")

class CSRespQ(Queue):
    __slots__ = ('env', 'qId')
    "Centralized Scheduler Response Queue"
    def __init__(self, env):
        Queue.__init__(self, env)
        self.qId = 4
        if Const.DEBUG_INIT: print("CSRespQ initialized")


