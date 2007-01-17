"""Evolution related classes.

Classes: Evaluation, Generation, Evolver

These classes work together to carry out genetic algorithm
evolutionary runs, and provide a place to store the results."""

import copy
import socket
import random
import time
import sys
import os
from numpy import matrix

import cluster

from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from ZODB.POSException import ConflictError, POSKeyError
from ZEO.zrpc.error import DisconnectedError
import transaction

import logging
logging.basicConfig()
log = logging.getLogger('evolve')
log.setLevel(logging.ERROR)

log.debug('recursion limit is %d, setting to 4000', sys.getrecursionlimit())
sys.setrecursionlimit(4000)

class HostData(Persistent):
    def __init__(self):
        Persistent.__init__(self)
        self.newIndividual = None

class Generation(PersistentList):

    # cons sig must be ok when called with only self,size args due to
    # assumptions of UserList.__getslice__ 

    def __init__(self, sizeOrList, new_individual_fn=None, new_individual_args=None, new_sim_fn=None, new_sim_args=None, ga='elite', mutationRate=0.01):
        """Create an initial generation

        size -- number of solutions
        """
        # hack because UserList methods like __getslice_ treat __init__ like its own
        if type(sizeOrList) is list:
            PersistentList.__init__(self, sizeOrList)
            return
        PersistentList.__init__(self)
        log.debug('Generation.__init__')
        self.gen_num = 0
        self.new_individual_fn = new_individual_fn
        self.new_individual_args = new_individual_args
        self.new_sim_fn = new_sim_fn
        self.new_sim_args = new_sim_args
        for i in range(sizeOrList):
            log.debug('.'*(i+1))
            # Generate new individual
            x = new_individual_fn(**dict(new_individual_args))
            x.score = None
            x.parentFitness = None
            x.numberOfMutations = None
            x.createdInGeneration = 0
            self.append(x)
            transaction.savepoint()
        self.prev_gen = []
        self.setUpdateInfo()
        self.fitnessList = PersistentList()
        self.ga = ga
        self.mutationRate = mutationRate
        self.hostData = PersistentMapping()
        for hostname in cluster.HOSTNAMES:
            self.hostData[hostname] = HostData()
        self.mutationStats = PersistentList() # (parentFitness, mutations, childFitness)
        self.statList = PersistentList()

    def setFinalGeneration(self, extraGenerations):
        "Set final generation number, relative to current one"
        self.final_gen_num = self.gen_num + extraGenerations

    def recordStats(self):
        "Record statistics"
        fitnessValues = [x.score for x in self if x.score != None]
        m = matrix([fitnessValues])
        if len(self.fitnessList) > self.gen_num:
            self.fitnessList = self.fitnessList[:self.gen_num]
        self.fitnessList.append((m.min(), m.mean(), m.max()))
        for bg in self.statList:
            assert isinstance(bg.parentFitness, float) or isinstance(bg.parentFitness, int)
            assert isinstance(bg.numberOfMutations, int)
            assert isinstance(bg.score, float) or isinstance(bg.score, int)
            ms = (bg.parentFitness, bg.numberOfMutations, bg.score)
            self.mutationStats.append(ms)
        del self.statList[:]

    def sanityCheck(self):
        log.debug('sanity check generation')
        for x in self:
            if hasattr(x, 'sanityCheck'):
                x.sanityCheck()

    def mutateChild(self, child):
        "Always generates a mutated child (m>0)"
        # don't save identical children. shortcut by forcing m>0.
        while 1:
            m = child.mutate(self.mutationRate)
            if not m:
                log.warn('child is identical to parent, mutation rate is too low')
            else:
                break
        child.numberOfMutations = m
        self.statList.append(child)
        log.debug('mutateChild created %d mutations', m)
        return m

    def elitistUpdate(self):
        """Elitist GA.

        Copies top % into next gen, then mutates copies
        of them to make the rest of the generation"""
        # update function must copy from self.prev_gen to self
        log.debug('elitistUpdate()')
        # 10% seems to be good for bpgs
        num_elites = max(int(round(len(self.prev_gen)/100.0*50)), 1)
        log.debug('%d elites',num_elites)

        # copy the elites into next generation
        self.prev_gen.sort(lambda x,y: cmp(y.score, x.score))
        count = 1
        for x in self.prev_gen[:num_elites]:
            y = copy.deepcopy(x)
            y.parentFitness = x.score
            y.numberOfMutations = 0
            self.append(y)
            transaction.savepoint()
            log.info('.' * count)
            count += 1
        log.debug('elites = %s'%self)

        # we now have some elites. copy them and mutate to generate children.
        for j in range(num_elites, len(self.prev_gen)):
            p = self.prev_gen[j%num_elites]
            child = copy.deepcopy(p)
            m = self.mutateChild(child)
            assert p.score != None
            child.parentFitness = p.score
            self.append(child)
            transaction.savepoint()
            log.info('.' * count)
            count += 1

    def setUpdateInfo(self, updating=0):
        self.updateInfo = (socket.gethostname(), time.time(), updating)

    def update(self):
        log.debug('update()')
        log.info('Making new generation %d (evals took %d seconds)', self.gen_num + 1, time.time() - self.updateInfo[1])

        self.setUpdateInfo(1)
        transaction.commit()

        transaction.begin()
        self.recordStats()

        for bg in self.prev_gen:
            bg.destroy()
        self.prev_gen = self[:]
        del self[:]

        s = 'top %d of new gen scores are:'%len(self.prev_gen)
        for i in range(len(self.prev_gen)):
           s += str(self.prev_gen[i].score) + ' '
        log.debug(s)
        self.elitistUpdate()
        # reset everything
        for x in self:
            x.score = None

        self.gen_num += 1
        self.setUpdateInfo(0)
        transaction.commit()
        log.info('New generation created in %d seconds', time.time() - self.updateInfo[1])

    def runSim(self, x):
        "Evaluate performance of individual(s) x in sim"

        sim = self.new_sim_fn(**dict(self.new_sim_args))
        sim.add(x)
        sim.run()
        return sim.score

    def evaluate(self, x):
        log.debug('evaluate')
        if type(x) is int:
            x = self[x]
        if x.numberOfMutations == 0 and x.parentFitness != None:
            log.debug('child same as parent, skip eval, fitness = %f', x.parentFitness)
            x.score = x.parentFitness
            return
        s0 = self.runSim(x)
        if s0 == -1:
            x.score = -1
            return
        s1 = self.runSim(x)
        x.score = matrix([s0, s1]).mean()

    def steadyStateClientInnerLoop(self):
        log.debug('steadyStateClientLoop')

        mydata = self.hostData[cluster.getHostname()]
        if mydata.newIndividual:
            transaction.abort()
            time.sleep(15)
            return

        # make sure all initial instances are evaluated first
        init = [z for z in self if z.score == None]
        if init:
            log.debug('doing post-create eval (no parent)')
            x = random.choice(init)
            self.evaluate(x)
            transaction.commit()
            return

        x = random.choice(self)
        y = copy.deepcopy(x)
        m = self.mutateChild(y)
        self.evaluate(y)
        log.debug('steady state eval done, score %f', y.score)
        assert x.score != None
        y.parentFitness = x.score
        log.debug('parent score=%f child score=%f', y.parentFitness, y.score)
        mydata.newIndividual = y
        transaction.commit()

    def steadyStateMasterInnerLoop(self):
        log.debug('steadyStateMasterLoop')
        l = [ x for x in self.hostData.values() if x.newIndividual ]
        if not l:
            log.debug('no newIndividuals')
            transaction.abort()
        else:
            for hd in l:
                empty = [z for z in self if z.score == None]
                lower = [z for z in self if z.score != None and z.score <= hd.newIndividual.score]
                if empty or lower:
                    if empty:
                        i = random.choice(empty)
                    else:
                        i = lower[0]
                        for l in lower[1:]:
                            if l.score < i.score:
                                i = l
                    log.debug('overwrite lowest %s', i)
                    hd.newIndividual.createdInGeneration = self.gen_num + 1
                    self[self.index(i)] = hd.newIndividual
                else:
                    log.debug('newIndividual is too low, throw it away')
                hd.newIndividual = None
                self.gen_num += 1
                self.recordStats()
            # force re-eval if older than threshold (stops freak evals being immortal)
            for x in self:
                if x.createdInGeneration < self.gen_num - 3*len(self):
                    x.score = None
                    x.createdInGeneration = self.gen_num
            transaction.commit()
            log.debug('commit ok')
        time.sleep(5)

    def leftToEval(self):
        return [ x for x in self if x.score == None ]

    def eliteInnerLoop(self, master, slave):
        ready = self.leftToEval()
        if slave and ready:
            x = random.choice(ready)
            self.evaluate(x)
            transaction.commit()
        elif master and not ready:
            self.update()
        else:
            log.debug('nothing to do, sleeping...')
            time.sleep(15)

    def getMaxIndividual(self):
        l = [(x.score, x) for x in self]
        l.sort()
        l.reverse()
        return l[0][0]

    def runClientLoop(self, master=1, slave=1):
        """Evolve client.

        Make sure everything in the current generation is evaluated,
        then create the next generation, and finally appends it to
        self.generations which is persistent
        (root['runs']['run_name'].generations)."""

        while 1:
            try:
                transaction.begin()
                log.debug('runClientLoop: %d/%d', self.gen_num, self.final_gen_num)
                if self.gen_num == self.final_gen_num \
                        and (self.ga == 'steady-state' or self.ga == 'elite' and ((master and not slave) or slave)) \
                        and not self.leftToEval() :
                    log.info('all individuals done in final generation, exiting')
                    transaction.abort()
                    return
                if self.ga == 'steady-state':
                    if slave:
                        self.steadyStateClientInnerLoop()
                    if master:
                        self.steadyStateMasterInnerLoop()
                elif self.ga == 'elite':
                    self.eliteInnerLoop(master, slave)
                else:
                    log.info('nothing for us to do')
            except ConflictError:
                transaction.abort()
                time.sleep(5)
                log.debug('commit conflict')
            except POSKeyError:
                log.critical('poskeyerror - this should not happen')
                raise
            except DisconnectedError:
                log.debug('we lost connection to the server, sleeping..')
                # FIXME: do i need to manually reestablish connection here??
                time.sleep(60)
        log.debug('/runClientLoop')
