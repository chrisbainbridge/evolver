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
import db

import cluster
import rand

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

class Counter(Persistent):
    def __init__(self):
        Persistent.__init__(self)
        self.i = 0

class Score:
    def __init__(self, min, mean, max):
        self.min = min
        self.mean = mean
        self.max = max
    def __str__(self):
        return '(%.2f %.2f %.2f)'%(self.min,self.mean,self.max)

class UpdateInfo(Persistent):
    def __init__(self):
        Persistent.__init__(self)
        self.host = socket.gethostname()
        self.time = time.time()
        self.updating = 0
    def update(self, v):
        self.updating = v
        self.time = time.time()
    def elapsed(self):
        return time.time() - self.time
    elapsed = property(elapsed)

class Generation(PersistentList):

    # cons sig must be ok when called with only self,size args due to
    # assumptions of UserList.__getslice__

    def __init__(self, sizeOrList, new_individual_fn=None, new_individual_args=None, new_sim_fn=None, new_sim_args=None, ga='elite', mutationRate=0.01, mut='uniform', final_gen=0):
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
            x.mutations = None
            x.createdInGeneration = 0
            x.busy = Counter()
            self.append(x)
            transaction.savepoint()
        self.prev_gen = []
        self.updateInfo = UpdateInfo()
        self.scores = PersistentList()
        assert ga in ('steadystate','elite','rank','tournament')
        self.ga = ga
        assert 0 < mutationRate < 1
        self.mutationRate = mutationRate
        self.hostData = PersistentMapping()
        for hostname in cluster.HOSTNAMES:
            self.hostData[hostname] = HostData()
        self.mutationStats = PersistentList() # (parentFitness, mutations, childFitness)
        self.statList = PersistentList()
        assert mut in ('gauss','uniform')
        self.mut = mut
        self.updateTime = time.time()
        self.updateRate = 0
        self.pause = 0
        self.final_gen_num = final_gen

    def recordStats(self):
        log.debug('record statistics')
        assert len(self.scores) in [self.gen_num, self.gen_num+1]
        if len(self.scores) == self.gen_num+1:
            log.debug('we already did this generation?, bailing out')
            return
        assert len(self.scores) == self.gen_num
        f = [x.score for x in self if x.score != None and x.score != -1]
        if not f:
            self.scores.append(Score(0,0,0))
        else:
            self.scores.append(Score(min(f), sum(f)/len(self), max(f)))

        for bg in self.statList:
            assert isinstance(bg.parentFitness, float) or isinstance(bg.parentFitness, int)
            assert isinstance(bg.mutations, int)
            assert isinstance(bg.score, float) or isinstance(bg.score, int)
            ms = (bg.parentFitness, bg.mutations, bg.score)
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
        i = 0
        while 1:
            child.mutate(self.mutationRate)
            if child.mutations:
                break
            log.warn('identical child, mutation rate too low, trying again')
            i += 1
            if i > 100:
                log.critical('mutation failure limit exceeded, exiting')
                sys.exit(1)
        self.statList.append(child)
        log.debug('mutateChild created %d mutations', child.mutations)

    def elitistUpdate(self):
        """Elitist GA.

        Copies top % into next gen, then mutates copies
        of them to make the rest of the generation"""
        log.debug('elitistUpdate()')
        # 20% seems to be good for bpgs
        num_elites = max(int(round(len(self.prev_gen)*0.2)), 1)
        log.debug('%d elites',num_elites)

        # copy the elites into next generation
        count = 1
        for x in self.prev_gen[:num_elites]:
            y = copy.deepcopy(x)
            y.parentFitness = x.score
            y.mutations = 0
            self.append(y)
            transaction.savepoint()
            log.info('.' * count)
            count += 1
        log.debug('elites = %s'%self)

        # we now have some elites. copy them and mutate to generate children.
        for j in range(num_elites, len(self.prev_gen)):
            p = self.prev_gen[j%num_elites]
            child = copy.deepcopy(p)
            self.mutateChild(child)
            assert p.score != None
            child.parentFitness = p.score
            self.append(child)
            transaction.savepoint()
            log.info('.' * count)
            count += 1

    def rankUpdate(self):
        log.debug('rankUpdate()')
        # construct cumulative rank vector
        rankv = []
        cum = 0.0
        n = len(self.prev_gen)
        for i in range(1, n+1):
            p = 2*float(n+1-i)/(n*(n+1))
            cum += p
            rankv.append(cum)
        for x in range(n):
            r = random.random()
            for z in range(n):
                if r <= rankv[z]:
                    p = self.prev_gen[z]
                    break
            y = copy.deepcopy(p)
            self.mutateChild(y)
            y.parentFitness = p.score
            self.append(y)
            transaction.savepoint()
            log.info('.' * (x+1))

    def tournamentUpdate(self):
        log.debug('tournamentUpdate()')
        n = len(self.prev_gen)
        for x in range(n):
            a = random.choice(self.prev_gen)
            b = random.choice(self.prev_gen)
            p = b
            if a.score > b.score:
                p = a
            y = copy.deepcopy(p)
            self.mutateChild(y)
            y.parentFitness = p.score
            self.append(y)
            transaction.savepoint()
            log.info('.' * (x+1))

    def update(self):
        log.debug('update()')
        log.info('Making new generation %d (evals took %d seconds)', self.gen_num + 1, self.updateInfo.elapsed)

        if not self.updateInfo.updating:
            self.updateInfo.update(1)
            transaction.commit()

        self.recordStats()

        if self.gen_num == self.final_gen_num:
            # the end
            log.info('the end')
            self.sort(lambda x,y: cmp(y.score, x.score))
        else:

            for bg in self.prev_gen:
                bg.destroy()
            self.prev_gen = self[:]
            self.prev_gen.sort(lambda x,y: cmp(y.score, x.score))
            del self[:]

            s = 'top %d of new gen scores are:'%len(self.prev_gen)
            s += ' '.join(['%1.2f'%x.score for x in self.prev_gen])
            log.debug(s)

            f = {'elite': self.elitistUpdate, 'rank': self.rankUpdate,
                    'tournament': self.tournamentUpdate}
            f[self.ga]()

            t = time.time()
            # evals per hour
            self.updateRate = len(self) * 60.0 * 60.0 / (t - self.updateTime)
            self.updateTime = t
            # reset everything
            for x in self:
                x.score = None
                x.busy.i = 0
            self.gen_num += 1

        log.info('New generation created took %d seconds', self.updateInfo.elapsed)
        self.updateInfo.update(0)
        transaction.commit()
        log.info('Commit took %d seconds', self.updateInfo.elapsed)

    def runSim(self, x, quick=0):
        "Evaluate performance of individual(s) x in sim"

        sim = self.new_sim_fn(quick=quick, **dict(self.new_sim_args))
        sim.add(x)
        sim.run()
        sim.destroy()
        return sim.score

    def evaluate(self, x):
        # This function used to do multiple evals and take the min, so robust
        # against physics explosions. But now that physics and motors are more
        # stable, such measures are hopefully not necessary. Taking the mean of
        # multiple trials has the advantage of normally distributed results
        # (central limit theorem).
        #
        # It might be better to use one or more quickStep evals here, to get
        # more robust agents (that work under more than one physics
        # environment), and to speed evaluations for agents with many body
        # parts.
        log.debug('evaluate')
        if type(x) is int:
            x = self[x]
        x.score = self.runSim(x, 0)

    def steadyStateClientInnerLoop(self):
        log.debug('steadyStateClientLoop')
        if self.gen_num == self.final_gen_num:
            log.debug('final gen, steadystate done')
            return

        mydata = self.hostData[cluster.getHostname()]
        if mydata.newIndividual:
            transaction.abort()
            time.sleep(15)
            return

        # make sure all initial instances are evaluated first
        init = [z for z in self if z.score == None]
        if init:
            x = random.choice(init)
            log.info('eval %d (post-create, no parent)', self.index(x))
            self.evaluate(x)
            transaction.commit()
            return

        x = random.choice(self)
        log.info('eval %d', self.index(x))
        y = copy.deepcopy(x)
        self.mutateChild(y)
        self.evaluate(y)
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
                self.recordStats()
                self.gen_num += 1
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

    def generationalInnerLoop(self, master, slave):
        ready = self.leftToEval()
        if slave and ready:
            notbusy = [x for x in ready if not x.busy.i]
            if notbusy:
                x = random.choice(notbusy)
                x.busy.i += 1
            else:
                busy = [x for x in ready if x.busy.i]
                min_busy = busy[0].busy.i
                for x in busy[1:]:
                    min_busy = min(x.busy.i, min_busy)
                mins = [x for x in busy if x.busy.i == min_busy]
                x = random.choice(mins)
                if x.busy.i < 2:
                    x.busy.i += 1
            transaction.commit()
            log.info('eval %d', self.index(x))
            a = time.time()
            self.evaluate(x)
            b = time.time()
            transaction.commit()
            log.info('took %d secs', round(b-a))
        elif master and not ready:
            self.update()
        else:
            log.debug('nothing to do, returning...')

    def getMaxIndividual(self):
        l = [(x.score, x) for x in self if x.score!=None]
        l.sort(lambda (asc,ax),(bsc,bx):cmp(asc,bsc), reverse=1)
        if l:
            return l[0][0]

    def runClientLoop(self, master=1, slave=1):
        if self.ga == 'steadystate':
            end = self.final_gen_num
        else:
            end = self.final_gen_num+1
        while len(self.scores) < end:
            log.debug('runClientLoop %d/%d', len(self.scores), end)
            self.runClientInnerLoop(master, slave)

    def runClientInnerLoop(self, master=1, slave=1):
        # need to set this here because it can vary between runs
        rand.mut = self.mut
        try:
            transaction.begin()
            if self.pause:
                time.sleep(5)
                return
            log.debug('runClientInnerLoop')
            if self.ga == 'steadystate':
                if slave:
                    self.steadyStateClientInnerLoop()
                if master:
                    self.steadyStateMasterInnerLoop()
            else:
                self.generationalInnerLoop(master, slave)
        except ConflictError:
            transaction.abort()
            log.debug('commit conflict')
        log.debug('/runClientInnerLoop')
        return 0
