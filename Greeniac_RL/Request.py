# -*- coding: utf-8 -*-
"""
Created on Mon Dec 24 10:51:38 2018

@author: sambit
"""
from Const import Const
import numpy as np

class Request(object):
    def __init__(self, env, reqId = 0):
        self.env = env
        self.reset(reqId)
        
    def reset(self, reqId):
        self.id = reqId
        self.timeCreated = self.env.now
        self.responseLatency = -1
        self.serviceTime = -1      #time taken to service the request by cpu core
        self.reqSize = 512    #size of request
        self.sid = -1    #server id of the server which processes this request
        self.cid = -1    #core id of the cpu which processes this request
        self.taskSize = np.random.exponential(Const.SERVICE_TIME)   # Normalized task size proposrtional to number of instructions executed
