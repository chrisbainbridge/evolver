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

===== Erase =====

 -e                   Delete this run
 --blank              Set all scores to None to force re-eval

===== Create initial population =====

 -p x                 Create initial population of size x
     -q x             Use discrete neural nets with x quanta states
     -t x             Run simulation for x seconds (default 30)
     -g x             Generations to evolve for (default 100)
     --topology x     Specify topology of [full,1d,2d,3d,randomk]
       -k x           Specify k inputs for randomk topology
     --update x       Update style [sync,async]
     --nodetype x     Type of node [sigmoid,logical,beer,sine]
     --states x       Number of states per cell [logical only]
     --nodes x       (1d, randomk, full) - Total number of nodes
                      (2d, 3d) - length of a dimension
                      number x includes network inputs and outputs
                      (default 10)
     --dombias x,y   Domain for bias is [x,y] (default [0,1])
     --domvalue x,y  Domain for signal values (default [-5,5])
     --domweight x,y Domain for weight values (default [-7,7])
     --radius x      Max distance of a nodes neighbour in any dimension (default 1)
                        Note: neighbourhoods are squares not crosses
     --fitness x     Specify fitness function [bpgsim only], can be:
                       cumulativez : average z value of all body parts summed over time
                       meandistance : average Euclidean distance of all body parts
 --elite             Use an elitist GA
 --steadystate       Use a steady state parallel GA
 --mutate x          Specify mutation probability
 --noise x           Specify standard deviation of Gaussian noise applied to sensors and motors
 --mutgauss          Use gaussian mutations instead of uniform

===== Unlock =====

 -u                   Release all locks in specified run

===== List =====

 -l                   List networks and their scores in evolution run

===== Plot graphs =====

 --plotnets f.type    Plot all of the control networks in bpg
 --plotbpg f.type     Plot to file. Type can be dot, ps, png, etc.
     --toponly         Only draw topology - no weights or bi-connects
     --unroll          Unroll bpg before converting to dot file
 --pf f.pdf  Plot min/mean/max fitness graph for specified generation
 --plotpi        Plot mutations vs prob. of child.fitness > parent fitness
 --plotfc        Plot mutations vs observed fitness change

===== Sim =====

 -s                   Run a simulation
 -v                   Visualise with graphical user interface
     --qt 'qt options'  Pass string onto QT options (eg. -geometry 640x480)
     --movie file.avi   Record movie to file.avi
 --plotsignals fname  Record signal traces. f can be *.[txt/trace/eps]
   --nostrip          Don't strip flat signals from the trace
 --sim x              Select simulator [pb, bpg]
 --lqr                Use LQR controller for pb sim
 """

import os
import sys
import socket
import time
import random
import cPickle
import getopt
import transaction
import logging

import ZODB
from ZODB.FileStorage import FileStorage
from ZEO.ClientStorage import ClientStorage
from ZODB import DB

import bpg
import db
import evolve
import network
import node # ignore checker error about this import
import sim
import daemon
from plot import *

log = logging.getLogger('ev')

def setup_logging():
    level = logging.INFO
    if '-d' in sys.argv:
        level = logging.DEBUG
        sys.argv.remove('-d')
    for m in 'bpg', 'ev', 'evolve', 'sim', 'glwidget', 'neural', 'qtapp', 'plot':
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
        opts, args = getopt.getopt(sys.argv[1:], 'cdr:ebg:hi:k:lp:q:sz:t:uvm', ['blank','qt=','topology=','update=','nodetype=','nodes=','dombias=','domvalue=','domweight=','elite', 'lqr', 'steadystate','mutate=','mutgauss','noise=','nodes_per_input=','network=','nostrip','plotbpg=','pf=','plotnets=','plotsignals=','unroll','radius=','toponly','movie=','sim=','states=', 'fitness=', 'plotpi=', 'plotfc='])
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
    avifile = ''
    qtopts = ''
    popsize = 0
    tracefile = None
    topology = 'full'
    update_style = 'sync'
    nodetype = 'sigmoid'
    num_nodes = 10
    simulation = 'bpg'
    #discrete = 0
    quanta = None
    server_addr = db.getDefaultServer()
    plotfitness = None
    plotpi = None
    plotfc = None

    client = 0
    master = 0
    g = None
    create_initial_population = 0
    background = 0
    delete = 0
    unlock = 0
    k = None
    # default domains
    dombias = (-5,5)
    domweight = (-7,7)
    #nodes_per_input = 1
    radius = 1
    plotbpg = None
    plotnets = None
    unroll = 0
    list_gen = 0
    toponly = 0
    g_index = None
    runsim = 0
    fitnessFunctionName = None
    ga = 'elite'
    max_simsecs = 0
    mutationRate = 0
    numberOfGenerations = 0
    gaussNoise = None
    strip = 1
    lqr = 0
    blank = 0
    mutgauss = 0
    for o, a in opts:
        log.debug('parsing %s %s',o,a)
        if o == '-c':
            client = 1
        elif o == '-e':
            delete = 1
        elif o == '-r':
            g = a
        elif o == '-b':
            background = 1
        elif o == '-g':
            numberOfGenerations = int(a)
        elif o in ('-h'):
            print __doc__
            return
        elif o == '-p':
            create_initial_population = 1
            popsize = int(a)
        elif o == '-l':
            list_gen = 1
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
        elif o == '--nodetype':
            nodetype = a
        elif o == '--nodes':
            num_nodes = int(a)
        elif o == '--dombias':
            # a is of form 'x,y'
            dombias = eval(a)
        elif o == '--domvalue':
            # FIXME: THIS IS NOT BEING USED
            domvalue = eval(a)
            fixme
        elif o == '--domweight':
            domweight = eval(a)
        elif o == '--nodes_per_input':
            # FIXME: THIS IS NOT BEING USED
            nodes_per_input = int(a)
            fixme
        elif o == '--elite':
            ga = 'elite'
        elif o == '--lqr':
            lqr = 1
        elif o == '--steadystate':
            ga = 'steady-state'
        elif o == '--mutate':
            mutationRate = float(a)
        elif o == '--mutgauss':
            mutgauss = 1
        elif o == '--noise':
            gaussNoise = float(a)
        elif o == '--nostrip':
            strip = 0
        elif o == '-i':
            g_index = int(a)
        elif o == '--plotbpg':
            plotbpg = a
        elif o == '--plotnets':
            plotnets = a
        elif o == '--pf':
            plotfitness = a
        elif o == '--plotpi':
            plotpi = a
        elif o == '--plotfc':
            plotfc = a
        elif o == '--plotsignals':
            tracefile = a
        elif o == '--unroll':
            unroll = 1
        elif o == '--radius':
            radius = int(a)
        elif o == '--toponly':
            toponly = 1
        elif o == '-s':
            runsim = 1
        elif o == '--sim':
            assert a in ('bpg', 'pb')
            simulation = a
        elif o == '-m':
            master = 1
        elif o == '--states':
            numberOfStates = int(a)
        elif o == '--fitness':
            fitnessFunctionName = a
        elif o == '--blank':
            blank = 1
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

    log.debug('zeo server is %s', server_addr)
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

        new_node_arg_class_map = {
                'sigmoid' : node.SigmoidNode,
                'logical': node.LogicalNode,
                'beer' : node.BeerNode,
                'sine' : node.SineNode }
        new_node_class = new_node_arg_class_map[nodetype]

        new_node_args = {}
        if new_node_class in [node.SigmoidNode, node.BeerNode, node.SineNode]:
            new_node_args = {
                    'weightDomain' : domweight,
                    'quanta': quanta }
            if new_node_class is node.BeerNode:
                new_node_args['biasDomain'] = dombias
        elif new_node_class is node.LogicalNode:
            new_node_args = { 'numberOfStates': numberOfStates }

        new_network_args = {
                'num_nodes' : num_nodes,
                'num_inputs' : num_inputs,
                'num_outputs' : num_outputs,
                'new_node_class': new_node_class,
                'new_node_args' : new_node_args,
                'topology' : topology,
                'update_style' : update_style,
                'radius' : radius }

        # create defaults
        if not max_simsecs : max_simsecs = 30
        if not mutationRate: mutationRate = 0.05
        if not numberOfGenerations: numberOfGenerations = 100
        if gaussNoise == None: gaussNoise = 0.005

        new_sim_args = { 'max_simsecs' : max_simsecs,
                         'gaussNoise' : gaussNoise}
        if simulation == 'bpg':
            new_individual_fn = bpg.BodyPartGraph
            new_individual_args = { 'network_args' : new_network_args }
            new_sim_fn = sim.BpgSim
            new_sim_args['fitnessName'] = fitnessFunctionName
        elif simulation == 'pb':
            new_individual_fn = network.Network
            new_individual_args = new_network_args
            new_sim_fn = sim.PoleBalanceSim

        root[g] = evolve.Generation(popsize, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args, ga, mutationRate)

        root[g].setFinalGeneration(numberOfGenerations)
        root[g].mutgauss = mutgauss
        log.debug('committing all subtransactions')
        transaction.commit()
        log.debug('commit done, end of create_initial_population')

    elif not create_initial_population and not runsim and (numberOfGenerations or mutationRate or max_simsecs):
        if numberOfGenerations:
            root[g].setFinalGeneration(numberOfGenerations)
        if mutationRate:
            root[g].mutationRate = mutationRate
        if max_simsecs:
            root[g].new_sim_args['max_simsecs'] = max_simsecs
        transaction.commit()

    elif g and g not in root:
        log.debug('Generation %s not in db %s', g, root.keys())
        return

    if delete:
        if not g:
            log.critical('which generation?')
            return 1
        del(root[g])
        transaction.commit()

    if blank:
        if not g:
            log.critical('which generation?')
            return 1
        for x in root[g]:
            x.score = None
        transaction.commit()

    if plotfitness or plotpi or plotfc:
        if not g:
            log.critical('which generation?')
            return 1
        if plotfitness:
            plotGenerationVsFitness(root[g], plotfitness, g)
        elif plotpi:
            plotMutationVsProbImprovement(root[g], plotpi, g)
        elif plotfc:
            plotMutationVsFitnessChange(root[g], plotfc, g)

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
                plotBpg(b, plotbpg, toponly)
            if plotnets:
                plotNetworks(b, plotnets, toponly)
        elif isinstance(b, network.Network):
            if plotnets:
                plotNetwork(b, plotnets, toponly)

    if list_gen:
        if not g:
            # print list of generations
            l = root.items()
            l.sort()
            for (k,i) in l:
                if isinstance(i, evolve.Generation):
                    print 'Generation: %s [ga=%s gen=%d/%d max=%s]'%(k, i.ga,
                            i.gen_num, i.final_gen_num, i.getMaxIndividual())
        else:
            # print list of individuals in a generation
            print 'Num\tScore\tP.score\tMutations'
            for i in range(len(root[g])):
                b = root[g][i]
                f = b.score
                pf = b.parentFitness
                if pf == None:
                    s_pf = 'X'
                else:
                    s_pf = ' %.2f'%pf
                if f == None:
                    s_f = 'X'
                else:
                    s_f = '%.2f'%f
                s_m = 'X'
                if b.mutations != None:
                    s_m = '%d'%b.mutations
                print '%d\t%s\t%s\t%s'%(i, s_f, s_pf, s_m)
            print 'Generation: name=%s ga=%s gen=%d/%d'%(g, root[g].ga,
                                                          root[g].gen_num,
                                                          root[g].final_gen_num)
            if root[g].updateInfo[2]:
                print 'Generation is currently being updated on %s, update '\
                        'running for %d seconds'%(root[g].updateInfo[0],
                                time.time() - root[g].updateInfo[1])

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
        if background:
            os.unlink('/tmp/client.pid')

    elif runsim:
        i = g_index
        # create and set up simulator
        if max_simsecs:
            secs = max_simsecs
        else:
            secs = root[g].new_sim_args['max_simsecs']
        if gaussNoise == None:
            gaussNoise = root[g].new_sim_args['gaussNoise']
        if root[g].new_sim_fn == sim.BpgSim:
            if not fitnessFunctionName:
                fitnessFunctionName = root[g].new_sim_args['fitnessName']
            s = root[g].new_sim_fn(secs, fitnessFunctionName, gaussNoise)
        elif root[g].new_sim_fn == sim.PoleBalanceSim:
            s = root[g].new_sim_fn(secs, gaussNoise=gaussNoise)
        if lqr:
            s.setUseLqr()
        else:
            s.add(root[g][i])
        # set up tracing
        plotTrace = 0
        if tracefile:
            (traceBase, traceExt) = os.path.splitext(tracefile)
            if traceExt in ['.trace', '.txt']:
                fname = tracefile
            elif traceExt == '.eps':
                fname = '%s.trace'%traceBase
                plotTrace = 1
            else:
                fname = 'tmp.trace'
                plotTrace = 1
            s.initSignalLog(fname)
        if gui:
            log.debug('Launching GUI')
            # start the qt app
            from qtapp import MyApp
            myapp = MyApp([sys.argv[0]]+qtopts.split(), s)
            myapp.setRecord(record, avifile)
            myapp.exec_loop()
            log.info('Final score was %f', s.score)
        else:
            log.info('Running simulation')
            # run sim without gui
            s.run()
            log.info('Final score was %f', s.score)
        if plotTrace:
            assert traceExt == '.eps' or tracefile == '-'
            if strip:
                stripTraceFile(fname)
            if root[g].new_individual_args.has_key('new_node_args'):
                q = root[g].new_individual_args['new_node_args']['quanta']
            else:
                q = root[g].new_individual_args['network_args']['new_node_args']['quanta']
            epsFiles = plotSignals(fname, q)
            if not epsFiles:
                log.critical('failed to generate trace - bad sim?')
                return 1
            if tracefile == '-':
                for f in epsFiles:
                    cmd = 'kghostview %s'%f
                    log.info(cmd)
                    os.system(cmd)

    return 0

if __name__=='__main__':
    random.seed()
    setup_logging()
    r = main()
    cleanup()
    sys.exit(r)
