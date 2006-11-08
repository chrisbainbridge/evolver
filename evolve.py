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

import db

from persistent import Persistent
from persistent.list import PersistentList
from ZODB.POSException import ConflictError
from ZEO.zrpc.error import DisconnectedError
import transaction

import logging
logging.basicConfig()
log = logging.getLogger('evolve')
log.setLevel(logging.ERROR)

log.debug('recursion limit is %d, setting to 4000', sys.getrecursionlimit())
sys.setrecursionlimit(4000)

statlog = None

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
            self.append(x)
            transaction.savepoint()
        self.random_state = random.getstate()
        self.prev_gen = []
        self.setUpdateInfo()
        self.fitnessList = PersistentList()
        self.ga = ga
        self.numberOfEvaluations = 0
        self.mutationRate = mutationRate

    def recordStats(self):
        "Record statistics"
        fitnessValues = [x.score for x in self if x.score != None]
        m = matrix([fitnessValues])
        if len(self.fitnessList) > self.gen_num:
            self.fitnessList = self.fitnessList[:self.gen_num]
        self.fitnessList.append((m.min(), m.mean(), m.max()))
        transaction.commit()
        if statlog:
            if not os.path.exists(statlog):
                f = open(statlog, 'w')
                f.write('# GENERATION MIN AVG MAX\n\n')
            else:
                f = open(statlog, 'a')
            total = 0.0
            for ev in self:
                total += ev.score
            maximum = self[0].score
            minimum = self[-1].score
            average = total / len(self)
            s = '%d %f %f %f\n'%(self.gen_num, minimum, average, maximum)
            f.write(s)
            f.close()

    def sanityCheck(self):
        log.debug('sanity check generation')
        for x in self:
            if hasattr(x, 'sanityCheck'):
                x.sanityCheck()

    def elitistUpdate(self):
        """Elitist GA.

        Copies top % into next gen, then mutates copies
        of them to make the rest of the generation"""
        # update function must copy from self.prev_gen to self
        log.debug('elitistUpdate()')
        # 10% seems to be good for bpgs
        num_elites = max(int(round(len(self.prev_gen)/100.0*50)), 1)
        #num_elites = 0 # FORCE NON-ELITIST GA
        log.debug('%d elites',num_elites)

        # copy the elites into next generation
        self.prev_gen.sort(lambda x,y: cmp(y.score, x.score))
        count = 1
        for x in self.prev_gen[:num_elites]:
            y = copy.deepcopy(x)
            #y.mutate(0.0) # aging damage (0.15)
            self.append(y)
            transaction.savepoint()
            log.info('.' * count)
            count += 1
        log.debug('elites = %s'%self)

        # we now have some elites. copy them and mutate to generate children.
        mutations = []
        for j in range(num_elites, len(self.prev_gen)):
            p = self.prev_gen[j%num_elites]
            child = copy.deepcopy(p)
            # FIXME: mutation prob. should be set on command line
#            m = 0
#            while m == 0:
#                m = child.mutate(0.01) # 0.10
            m = child.mutate(self.mutationRate)
            mutations.append(m)
            self.append(child)
            transaction.savepoint()
            log.info('.' * count)
            count += 1
        log.debug('child mutations = %s', str(mutations))

    def setUpdateInfo(self, updating=0):
        self.updateInfo = (socket.gethostname(), time.time(), updating)

    def update(self):
        log.debug('update()')
        log.info('Making new generation %d (evals took %d seconds)', self.gen_num + 1, time.time() - self.updateInfo[1])
        self.setUpdateInfo(1)
        transaction.commit()

        transaction.begin()
        for bg in self.prev_gen:
            bg.destroy()
        self.prev_gen = self[:]
        del self[:]

        s = 'top %d of new gen scores are:'%len(self.prev_gen)
        for i in range(len(self.prev_gen)):
           s += str(self.prev_gen[i].score) + ' '
        log.debug(s)
        if self.ga == 'elite':
            self.elitistUpdate()
        elif self.ga == 'steady-state':
            bad
        # reset everything
        for x in self:
            x.score = None

        # set next random seed
        self.random_state = random.getstate()
        self.gen_num += 1
        self.setUpdateInfo(0)
        transaction.commit()
        log.info('New generation created in %d seconds', time.time() - self.updateInfo[1])
        transaction.commit()

    def evaluate(self, x):
        """Evaluate performance of individual(s) x in sim"""

        if type(x) is int:
            x = self[x]
        # set random seed the same for each evaluation
        try:
            log.debug('evaluating individual %d', self.index(x))
        except:
            log.debug('evaluating individual %s', x)
        currentRandomState = random.getstate()
        random.setstate(self.random_state)
        # do sim
        sim = self.new_sim_fn(**dict(self.new_sim_args))
        sim.add(x)
        sim.run()
        random.setstate(currentRandomState)
        x.score = sim.score

    def runClientLoop(self, master=1, client=1):
        """Evolve client.

        Make sure everything in the current generation is evaluated,
        then create the next generation, and finally appends it to
        self.generations which is persistent
        (root['runs']['run_name'].generations)."""

        log.info('runClientLoop, generation %d of %d', self.gen_num, self.final_gen_num)

        while 1:
            try:
                db.sync()
                if self.ga == 'steady-state' and client:
                    log.debug('steady state update')
                    if self.numberOfEvaluations == self.final_gen_num:
                        break
                    # pick randomly, 
                    x = random.choice(self)
                    log.info('client evaluating %d', self.index(x))
                    y = copy.deepcopy(x)
                    m = 0
                    while m == 0:
                        # mutate changes x, but its ok cos we abort below
                        m = y.mutate(self.mutationRate)
                    self.evaluate(y)
                    log.debug('steady state eval done')
                    # did we beat anything?
                    while 1:
                        try:
                            # loop syncing db and trying to overwrite an entry
                            log.debug('db.sync')
                            db.sync()
                            self.numberOfEvaluations += 1
                        
                          
                            none = [z for z in range(len(self)) if self[z].score == None]
                            #z for z in self if z.score == None]
                            lower = [z for z in range(len(self)) if self[z].score != None and self[z].score <= y.score]
                            #z for z in self if z.score != None and z.score <= y.score]
                            if none or lower:
                                self.gen_num += 1
                                if none:
#                                    r = random.choice(none)
                                    i = random.choice(none)
                                else:
                                    # maybe we should just replace the lowest?
                                    #r = random.choice(lower)
                                    i = random.choice(lower)
                                #i = self.index(r)
                                log.debug('overwrite %d', i)
                                self[i] = y
#                    self.recordStats()
                                log.debug('trying commit')
                                transaction.commit()
                                log.debug('commit ok')
                            break
                        except ConflictError:
                            pass

                elif self.ga == 'elite':
                    ready = [ x for x in self if x.score == None ]
                    if client and ready:
                        x = random.choice(ready)
                        log.info('client evaluating %d', self.index(x))
                        score = self.evaluate(x)
                        transaction.commit()
                    elif master and not ready:
                        # finalise this generation
                        self.recordStats()
                        if self.gen_num < self.final_gen_num:
                            # make next generation
                            self.update()
                        else:
                            log.info('final generation is done, so exit')
                            break
                    elif self.gen_num == self.final_gen_num:
                        log.info('all individuals done in final generation, exiting')
                        break
                    else:
                        log.debug('nothing to do, sleeping...')
                        time.sleep(15)
            except ConflictError:
                # Someone beat us to a lock or update
                pass
            except DisconnectedError:
                log.debug('we lost connection to the server, sleeping..')
                # do i need to reestablish connection here??
                time.sleep(60)
        log.debug('leaving evolve()')
