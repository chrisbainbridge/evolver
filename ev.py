#!/usr/bin/env python

"""Front end to the evolution and simulation engine.

===== Options for all invocations =====

 -z server_addr       ZEO DB server (default localhost)
 -r name              Select evolutionary run with given name
 -i x                 Select individual with index x
 -d                   debug

===== Client mode =====

 -c                   Client - Do evals (port always 8090)
     -b                 Run client in background
 -m                   Master - Do evolution and logging
     --statlog x        Record evolution stats to file x

===== Erase =====

 -e                   Delete this run

===== Create initial population =====

 -p x                 Create initial population of size x
     -q x             Use discrete neural nets with x quanta states
     -t x             Run simulation for x seconds (default 30)
     -g x             Generations to evolve for (default 100)
     --topology x     Specify topology of [full,1d,2d,3d,randomk]
       -k x           Specify k inputs for randomk topology
     --update x       Update style [sync,async]
     --node_type x    Type of node [sigmoid,logical]
     --states x       Number of states per cell [logical only]
     --nodes x    (1d, randomk, full) - Total number of nodes 
                      (2d, 3d) - length of a dimension
                      number x includes network inputs and outputs
                      (default 10)
     --dom_bias x,y   Domain for bias is [x,y] (default [0,1])
     --dom_value x,y  Domain for signal values (default [-5,5])
     --dom_weight x,y Domain for weight values (default [-7,7])
     --nb_dist x      Max distance of a nodes neighbour in any dimension (default 1)
                      Note: neighbourhoods are squares not crosses
     --fitness x      Specify fitness function [bpgsim only], can be:
                        cumulative-z : average z value of all body parts summed over time
                        mean-distance : average Euclidean distance of all body parts
 --ga-elite           Use an elitist GA
 --ga-steady-state    Use a steady state parallel GA
 --mutation-rate x    Specify mutation probability
 --gauss-noise x      Specify standard deviation of Gaussian noise applied to sensors and motors

===== Unlock =====

 -u                   Release all locks in specified run

===== List =====

 -l                   List networks and their scores in evolution run

===== Plot graphs =====

 --plotnets f.type    Plot all of the control networks in bpg 
 --plotbpg f.type     Plot to file. Type can be dot, ps, png, etc.
     --toponly         Only draw topology - no weights or bi-connects
     --unroll          Unroll bpg before converting to dot file
 --plotfitness f.pdf  Plot min/mean/max fitness graph for specified generation

===== Sim =====

 -s                   Run a simulation
 -v                   Visualise with graphical user interface
     --qt 'qt options'  Pass string onto QT options (eg. -geometry 640x480)
     --movie file.avi   Record movie to file.avi
 -n file              Record neuron state traces to file

===== Select simulation and fitness function =====

 --sim x              Select simulator [pb, bpg]"""

import os
import sys
import socket
import time
import random
import cPickle
import getopt
import transaction
import logging
import re

from ZODB.FileStorage import FileStorage
from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping

import bpg
import db
import evolve
import network
import node # ignore checker error about this import
import sim
import daemon
import cluster

# stuff that isn't needed on cluster hosts
if not cluster.isHost():
    import Gnuplot

log = logging.getLogger('ev')

def setup_logging():
    level = logging.INFO
    if '-d' in sys.argv:
        level = logging.DEBUG
        sys.argv.remove('-d')
    for m in 'bpg', 'ev', 'evolve', 'sim', 'glwidget', 'neural', 'qtapp':
        l = logging.getLogger(m)
        l.setLevel(level)
    logging.basicConfig()
    logging.getLogger('evolve').setLevel(logging.DEBUG)

def cleanup():
    log.debug('ev.py cleanup')
    transaction.get().abort()
    if db.conn:
        db.conn.close()

def main():
    log.debug(' '.join(sys.argv))
    # parse command line
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'cdr:ebg:hi:k:ln:p:q:sz:t:uvm', ['qt=','topology=','update=','node_type=','nodes=','dom_bias=','dom_value=','dom_weight=','ga-elite', 'ga-steady-state','mutation-rate=','gauss-noise=','nodes_per_input=','network=','plotbpg=','plotfitness=','plotnets=','unroll','nb_dist=','toponly','movie=','sim=','states=','statlog=', 'fitness='])
        log.debug('opts %s', opts)
        log.debug('args %s', args)
        # print help for no args
        if not opts:
            print __doc__
            return 1
    except getopt.GetoptError, e:
        print e
        return 1
    # defaults
    gui = 0
    record = 0
    max_simsecs = 30
    avifile = ''
    qtopts = ''
    change_generations = 0
    evolve_for_generations = 100
    popsize = 0
    tracefile = None
    topology = 'full'
    update_style = 'sync'
    node_type = 'sigmoid'
    num_nodes = 10
    simulation = 'bpg'
    #discrete = 0
    quanta = None
    server_addr = db.getDefaultServer()
    plotfitness = None

    client = 0
    master = 0
    g = None
    create_initial_population = 0
    background = 0
    delete = 0
    unlock = 0
    k = None
    # default domains
    dom_bias = (-5,5)
    dom_weight = (-7,7)
    #nodes_per_input = 1
    nb_dist = 1
    plotbpg = None
    plotnets = None
    unroll = 0
    list_gen = 0
    toponly = 0
    g_index = None
    runsim = 0
    fitnessFunctionName = None 
    ga = 'elite'
    mutationRate = 0.01
    gaussNoise = 0.01
    for o, a in opts:
        log.debug('parsing %s,%s',o,a)
        if o == '-c':
            client = 1
        elif o == '-e':
            delete = 1
        elif o == '-r':
            g = a
        elif o == '-b':
            background = 1
        elif o == '-g':
            change_generations = 1
            evolve_for_generations = int(a)
        elif o in ('-h'):
            print __doc__
            return
        elif o == '-p':
            create_initial_population = 1
            popsize = int(a)
        elif o == '-l':
            list_gen = 1
        elif o == '-n':
            tracefile = a
        elif o == '-q':
            quanta = int(a)
        elif o == '--movie':
            record = 1
            avifile = a
        elif o == '-z':
            server_addr = a
        elif o == '-t':
            max_simsecs = float(a)
        elif o == '-u':
            unlock = 1
        elif o == '-v':
            gui = 1
            runsim = 1
        elif o == '--qt':
            qtopts = a
        elif o == '--topology':
            topology = a
        elif o == '-k':
            k = int(a)
        elif o == '--update':
            update_style = a
        elif o == '--node_type':
            node_type = a
        elif o == '--nodes':
            num_nodes = int(a)
        elif o == '--dom_bias':
            # a is of form 'x,y'
            dom_bias = eval(a)
        elif o == '--value_bias':
            # FIXME: THIS IS NOT BEING USED
            dom_value = eval(a)
            fixme
        elif o == '--dom_weight':
            dom_weight = eval(a)
        elif o == '--nodes_per_input':
            # FIXME: THIS IS NOT BEING USED
            nodes_per_input = int(a)
            fixme
        elif o == '--ga-elite':
            ga = 'elite'
        elif o == '--ga-steady-state':
            ga = 'steady-state'
        elif o == '--mutation-rate':
            mutationRate = float(a)
        elif o == '--gauss-noise':
            gaussNoise = float(a)
        elif o == '-i':
            g_index = int(a)
        elif o == '--plotbpg':
            plotbpg = a
        elif o == '--plotnets':
            plotnets = a
        elif o == '--plotfitness':
            plotfitness = a
        elif o == '--unroll':
            unroll = 1
        elif o == '--nb_dist':
            nb_dist = int(a)
        elif o == '--toponly':
            toponly = 1
        elif o == '-s':
            runsim = 1
        elif o == '--sim':
            assert a in ('bpg', 'pb')
            simulation = a
        elif o == '-m':
            master = 1
        elif o == '--statlog':
            evolve.statlog = a
        elif o == '--states':
            numberOfStates = int(a)
        elif o == '--fitness':
            fitnessFunctionName = a
        else:
            log.critical('unhandled option %s',o)
            return 1

    if record and not qtopts:
        qtopts = '-geometry 640x480'

    # check options
    if gui + (client | master) + create_initial_population > 1 :
        log.critical('gui, client/master, create_initial are mutually exclustive modes')
        return 1
    if g_index != None and not runsim and not plotbpg and not plotnets:
        log.critical('What do you want me to do with that individual?')
        return 1
        
    # before we do anything, fork if necessary
    if (master or client) and background:
        daemon.createDaemon()
        # record pid so it can be used by monitoring programs
        f = open('/tmp/client.pid', 'w')
        f.write('%d\n'%(os.getpid()))
        f.close()

    log.debug('zodb server is %s', server_addr)
    root = db.connect(server_addr)

    if unlock:
        log.debug('release all locks')
        for x in root[g]:
            if hasattr(x, 'in_progress'):
                del x.in_progress
        transaction.commit()

    if create_initial_population:
        log.debug('creating Generation')
        if g in root:
            log.critical('Generation %s already exists!', g)
            return 1

        if simulation == 'pb':
            num_inputs = 1
            num_outputs = 1
        elif simulation == 'bpg':
            # FIXME: this should be random from a definable range?
            num_inputs = 2
            num_outputs = 2
            # (WHAT ABOUT PARAMS NOT PRESENT HERE ???)
            # k
        if topology == '2d':
            num_nodes = num_nodes**2
        elif topology == '3d':
            num_nodes = num_nodes**3

        new_node_arg_class_map = { 'sigmoid' : node.SigmoidNode,
                         'logical': node.LogicalNode}
        new_node_class = new_node_arg_class_map[node_type]
        if new_node_class == node.SigmoidNode:
            new_node_args = PersistentMapping(
                    { 'bias_domain': dom_bias,
                      'weight_domain' : dom_weight,
                      'quanta': quanta })
        elif new_node_class == node.LogicalNode:
            new_node_args = PersistentMapping(
                    { 'numberOfStates': numberOfStates })
        new_network_args = PersistentMapping(
                { 'num_nodes' : num_nodes,
                  'num_inputs' : num_inputs,
                  'num_outputs' : num_outputs,
                  'new_node_class': new_node_class,
                  'new_node_args' : new_node_args,
                  'topology' : topology,
                  'update_style' : update_style,
                  'nb_dist' : nb_dist })
        new_sim_args = PersistentMapping ({ 'max_simsecs' : max_simsecs ,
                                            'gaussNoise' : gaussNoise})
        if simulation == 'bpg':
            new_individual_fn = bpg.BodyPartGraph
            new_individual_args = PersistentMapping(
                    { 'network_args' : new_network_args })
            new_sim_fn = sim.BpgSim
            if not fitnessFunctionName:
                log.critical('must specify --fitness for new population')
                return 1

            new_sim_args['fitnessName'] = fitnessFunctionName
        elif simulation == 'pb':
            new_individual_fn = network.Network
            new_individual_args = new_network_args
            new_sim_fn = sim.PoleBalanceSim

        root[g] = evolve.Generation(popsize, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args, ga, mutationRate)

        log.debug('committing all subtransactions')
        transaction.commit()
        log.debug('commit done, end of create_initial_population')

    elif g and g not in root:
        log.debug('Generation %s not in db %s', g, root.keys())
        return

    if delete:
        if not g:
            log.critical('which generation?')
            return 1
        del(root[g])
        transaction.commit()

    if plotfitness:
        if not g:
            log.critical('which generation?')
            return 1
        gp = Gnuplot.Gnuplot()
        gp('set style data line')
        gp('set terminal pdf')
        gp('set output "%s"'%plotfitness)
        d = root[g].fitnessList
        d0 = Gnuplot.Data([x[0] for x in d], title='min')
        d1 = Gnuplot.Data([x[1] for x in d], title='mean')
        d2 = Gnuplot.Data([x[2] for x in d], title='max')
        gp.xlabel('Generation')
        gp.ylabel('Fitness')
        gp.plot(d0, d1, d2)
    
    if plotbpg or plotnets:
        if not g:
            log.critical('which generation?')
            return 1
        b = root[g][g_index]
        if isinstance(b, bpg.BodyPartGraph):
            if unroll:
                b = b.unroll()
                b.connectInputNodes()
            if plotbpg:
                b.plotBpg(plotbpg, toponly)
            if plotnets:
                b.plotNetworks(plotnets, toponly)
        elif isinstance(b, network.Network):
            if plotnets:
                b.plot(plotnets, toponly)

    if list_gen:
        if not g:
            # print list of generations
            for (k,i) in root.iteritems():
                if isinstance(i, evolve.Generation):
                    print 'Generation: %s [ga=%s gen=%d/%d max=%s]'%(k, i.ga, i.gen_num, i.final_gen_num, i[0].score) #,i
        else:
            # print list of individuals in a generation
            print 'Num\t| Score'
            for i in range(len(root[g])):
                print '%d\t| %s'%(i, str(root[g][i].score))
            print 'Generation: name=%s ga=%s gen=%d final_gen_num=%d'%(g, root[g].ga,
                                                          root[g].gen_num,
                                                          root[g].final_gen_num)
            if root[g].updateInfo[2]:
                print 'Generation is currently being updated on %s, update running for %d seconds'%(root[g].updateInfo[0], time.time() - root[g].updateInfo[1])
    if change_generations or create_initial_population:
        root[g].final_gen_num = root[g].gen_num + evolve_for_generations
        transaction.commit()

    if client or master:
        log.debug('master/client mode')
        # look for jobs
        if g:
            runs = [g]
        else:
            runs = [k for (k, i) in root.iteritems() if isinstance(i, evolve.Generation)]
        # run evolution
        for r in runs:
            if root[r].gen_num <= root[r].final_gen_num:
                if client:
                    s = 'client'
                if master:
                    s = 'master'
                log.info('%s mode on run %s', s, r)
                root[r].runClientLoop(master, client)
            else:
                log.debug('run %s is done (%d/%d)', r, root[r].gen_num,
                          root[r].final_gen_num)
        log.info('client exiting')

    elif runsim:
        # run a single simulation from current generation
        try:
            i = g_index
        except:
            # let user select individual
            for i in range(len(root[g])):
                print i, root[g][i].score
            print 'select i:'
            i = int(sys.stdin.readline().strip())
        # create and set up simulator
        if type(max_simsecs) in [int, float]:
            secs = max_simsecs
        else:
            secs = root[g].new_sim_args['max_simsecs']
        if fitnessFunctionName is None:
            fitnessFunctionName = root[g].new_sim_args['fitnessName']

        s = root[g].new_sim_fn(secs, fitnessFunctionName)
        s.add(root[g][i])
        # restore saved random state - ensures simulation reproducibility
        #random.setstate(root[g].random_state)
        # set up tracing
        if tracefile:
            s.initSignalLog(tracefile)
#        import psyco
#        psyco.full()
        if gui:
            log.debug('Launching GUI')
            # start the qt app
            from qtapp import MyApp
            myapp = MyApp([sys.argv[0]]+qtopts.split(), s)
            myapp.setRecord(record, avifile)
            err = myapp.exec_loop()
            log.info('Final score was %f', s.score)
            return err 
        else:
            log.info('Running simulation')
            # run sim without gui
            s.run()
            log.info('Final score was %f', s.score)
    return 0

if __name__=='__main__':
    random.seed()
    setup_logging()
    r = main()
    cleanup()
    sys.exit(r)
