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

import bpg
import gc
import memprof
sampler = memprof.Sampler()

from persistent import Persistent
from persistent.list import PersistentList
from ZODB.POSException import ConflictError
from ZEO.zrpc.error import DisconnectedError
import transaction

import logging
logging.basicConfig()
log = logging.getLogger('evolve')
log.setLevel(logging.INFO)

log.debug('recursion limit is %d, setting to 4000', sys.getrecursionlimit())
sys.setrecursionlimit(4000)

conn = None # zeo database connection
db = None # zeo database
master = 0
statlog = None

def garbage_collect():
    """Garbage collect leaks"""
    if globals().has_key('gc'):
        x = gc.collect()
        log.debug('GC: %d objects unreachable', x)
#    sampler.run()
#    print 'top 100 counts of references by object type'
#    print_top_100()
#    print 'uncollectable objects', gc.garbage
    #print 'garbage collector knows about these objects', gc.get_objects()

class Generation(PersistentList):

    def __init__(self, size, new_individual_fn=None, new_individual_args=None, new_sim_fn=None, new_sim_args=None):
        """Create an initial generation

        size -- number of solutions
        """
        # hack because UserList methods treat __init__ like its own
        if type(size) is not int:
            PersistentList.__init__(self, size)
            return
        PersistentList.__init__(self)
        log.debug('Generation.__init__')
        self.gen_num = 0
        self.new_individual_fn = new_individual_fn
        self.new_individual_args = new_individual_args
        self.new_sim_fn = new_sim_fn
        self.new_sim_args = new_sim_args
        #(new_s_fn, new_s_args) = new_sim
        for _ in range(size):
            log.debug('.')
            # Generate a random BodyPartGraph
            #net = apply(self.createNetwork, network_params)
            x = new_individual_fn(**dict(new_individual_args)) 
            x.score = None
            #e.solution.createRandom(network_params)
            self.append(x)
            # commit subtransaction
            transaction.savepoint()
##             log.debug('created network #%d (type=%s, node_type=%s, ' +
##                   'num_nodes=%d, quanta=%s, domains(bias=%s, values=%s, ' +
##                   'weight=%s)', i, str(type(net)), str(type(net._network[0])),
##                   len(net._network), str(net.quanta),
##                   str(net.bias_domain), str(net.value_domain),
##                   str(net.weight_domain))
        #self.generation._generation[0].solution.toDotFile('bpg.dot')
        #self.new_Sim = new_Sim
        #self.max_simsecs = max_simsecs
        self.random_state = random.getstate()

    def recordStats(self):
        "Record statistics"
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
        log.debug('elitistUpdate()')
        # 10% seems to be good for bpgs
        num_elites = max(int(round(len(self.prev_gen)/100.0*50)), 1)
        #num_elites = 0 # FORCE NON-ELITIST GA
        log.debug('%d elites',num_elites)
        print '%d elites'%num_elites

        # copy the elites into next generation
        self.prev_gen.sort(lambda x,y: cmp(y.score, x.score))
        for x in self.prev_gen[:num_elites]:
            y = copy.deepcopy(x)
            #y.mutate(0.0) # aging damage (0.15)
            if hasattr(y, 'sanityCheck'):
                y.sanityCheck()
            self.append(y)
            transaction.savepoint()
        log.debug('elites = %s'%self)

        # we now have some elites. copy them and mutate to generate children.
        mutations = []
        for j in range(num_elites, len(self.prev_gen)):
            p = self.prev_gen[j%num_elites]
            child = copy.deepcopy(p)
            if hasattr(child, 'sanityCheck'):
                child.sanityCheck()
            # FIXME: mutation prob. should be set on command line
            #child.mutate(0.02) # 0.10
            m = 0
            while m == 0:
                m = child.mutate(0.01) # 0.10
            mutations.append(m)
            if hasattr(child, 'sanityCheck'):
                child.sanityCheck()
            self.append(child)
            transaction.savepoint()
        print 'mutations',mutations

    def randomUpdate(self):
        "Random search, top 1 survives but "
        log.debug('randomUpdate()')

        num_elites = max(int(round(len(self.prev_gen)/100.0*10)), 1)
        # copy unchanged into next generation
#        for x in self.prev_gen[:num_elites]:
#            y = copy.deepcopy(x)
#            if hasattr(y, 'sanityCheck'):
#                y.sanityCheck()
#            self.append(y)
#            transaction.savepoint()

        # copy unchanged elite or its child unless they were both beaten by a random
        randoms_copied = []
        for j in range(num_elites, num_elites*2):
            if self.prev_gen[j-num_elites].score > self.prev_gen[j].score:
                p = self.prev_gen[j-num_elites]
            else:
                p = self.prev_gen[j]
            # did it get beaten by a random?
            bestk = None
            for k in range(num_elites**2, len(self.prev_gen)):
                if k not in randoms_copied and self.prev_gen[k].score > p.score:
                    p = self.prev_gen[k]
                    bestk = k
            if bestk != None:
                randoms_copied.append(k)
            child = copy.deepcopy(p)
            #child.mutate(0.02)
            self.append(child)
            transaction.savepoint()

        # children of elites
        for j in range(num_elites):
            child = copy.deepcopy(self.prev_gen[j])
            child.mutate(0.02)
            self.append(child)
            transaction.savepoint()

        # the rest random search
        for j in range(num_elites*2, len(self.prev_gen)):
            p = self.prev_gen[j]
            child = copy.deepcopy(p)
            child.mutate(0.02)
            self.append(child)
            transaction.savepoint()

    def update(self):
        log.debug('update()')
        # we only need this lock if we have several masters
        self.next_gen_lock = (socket.gethostname(), time.time())
        transaction.commit()
        log.debug('hah, we got the lock. Evolving generation %d', self.gen_num)
        self.sanityCheck()

        transaction.begin()
        self.prev_gen = self[:]
        del self[:]

        print 'top 5 of new gen scores are:'
        for i in range(len(self.prev_gen)):
            print self.prev_gen[i].score
        # update function must copy from self.prev_gen to self
        self.elitistUpdate()
        #self.randomUpdate()
        self.sanityCheck()
        # reset everything
        for x in self:
            x.score = None
        self.next_gen_lock = None

        # set next random seed
        self.random_state = random.getstate()

        # hoorah another generation done
        self.gen_num += 1
        transaction.commit()

    def evaluate(self, x):
        """Evaluate performance of individual(s) x in sim"""

        if type(x) is int:
            x = self[x]
        # get lock on this individual
        transaction.begin()
        x.in_progress = (socket.gethostname(), time.time())
        x.score = None
        transaction.commit()
        # random seed the same for each evaluation
        log.debug('evaluating individual %d', self.index(x))
        #random.setstate(self.random_state)
        random.seed()
        # do sim
        sim = self.new_sim_fn(**dict(self.new_sim_args))
        sim.add(x)
        sim.run()
        # record score, clear lock, cleanup
        x.score = sim.score
        del x.in_progress
        transaction.commit()
        self.sort(lambda x,y: cmp(y.score, x.score))
        transaction.commit()
        garbage_collect()

    def runClientLoop(self):
        """Evolve client.

        Make sure everything in the current generation is evaluated,
        then create the next generation, and finally appends it to
        self.generations which is persistent
        (root['runs']['run_name'].generations)."""

        log.info('Starting evolve client, generation %d of %d', self.gen_num, self.final_gen_num)

        while 1:
            try:
                # start new transaction
                if conn:
                    conn.sync()
                transaction.begin()

                # find ready individuals
                ready = []
                all_done = 1
                for x in self:
                    if x.score == None:
                        all_done = 0
                        #if not hasattr(x, 'in_progress'):
                        ready.append(x)
#                    if hasattr(x, 'in_progress'):
#                        try:
#                            held_time = int(time.time() - x.in_progress[1])
#                        except:
#                            pass
#                            import pdb
#                            pdb.set_trace()
#                        if held_time > 300: # 5 min timeout on evaluate call
#                            self.evaluate(x)

                if ready:
                    # evaluate a random individual
                    #x = random.choice(ready)
                    x = ready[0]
                    self.evaluate(x)

                elif all_done and master:
                    # finalise this generation
                    #self.sort(lambda x,y: cmp(y.score, x.score))
                    #transaction.commit()
                    self.recordStats()
                    if self.gen_num < self.final_gen_num:
                        # make next generation
                        self.update()
                    else:
                        # final generation is done, so exit
                        break

# THIS CODE ALLOWS ANY NODE TO COMPLETE IF THE MASTER FAILS.. STILL NEEDED?
##                elif not master and self.next_gen_lock:
##                     held_time = int(time.time() - self.next_gen_lock[1])
##                     log.debug('lock held by %s, waited for %d seconds...',self.next_gen_lock[0],held_time)
##                     # make sure this is definately enough time for createNextGeneration to complete
##                     # if host has failed, time out after 10 mins
##                     time.sleep(60)
## #                     if held_time > 1200:
## #                         self.createNextGeneration()
## #                     else:
## #                         # wait a bit
## #                         time.sleep(60)

                elif all_done and not master and self.gen_num == self.final_gen_num:
                    # all individuals in final generation are done, so exit
                    break

                else:
                    # the master must be busy.. wait a bit
                    time.sleep(15)

            except ConflictError:
                # Someone beat us to a lock or update
                pass

            except DisconnectedError:
                log.debug('we lost connection to the server, sleeping..')
                # do i need to reestablish connection here??
                time.sleep(60)

        log.debug('leaving evolve()')
