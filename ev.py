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
     --nodes x    (1d, randomk, full) - Total number of nodes 
                      (2d, 3d) - length of a dimension
                      number x includes network inputs and outputs
                      (default 10)
     --dom_bias x,y   Domain for bias is [x,y] (default [0,1])
     --dom_value x,y  Domain for signal values (default [-5,5])
     --dom_weight x,y Domain for weight values (default [-7,7])
     --nb_dist x      Max distance of a nodes neighbour in any dimension (default 1)
                      Note: neighbourhoods are squares not crosses

===== Unlock =====

 -u                   Release all locks in specified run

===== List =====

 -l                   List networks and their scores in evolution run

===== Plot graphs =====

 --plotnets f.type    Plot all of the control networks in bpg 
 --plotbpg f.type     Plot to file. Type can be dot, ps, png, etc.
     --toponly         Only draw topology - no weights or bi-connects
     --unroll          Unroll bpg before converting to dot file

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
import asyncore
import thread
import transaction
import logging
import gc

from ZODB.FileStorage import FileStorage
from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping

import evolve
import bpg
import sim
import network
# ignore checker for these
import node

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

# guard stuff that should only be run once with this..
# ie. when main is called twice by a test harness
once_only = 1

def cleanup():
    log.debug('ev.py cleanup')
    transaction.get().abort()
    if evolve.conn:
        evolve.conn.close()
    if evolve.db:
        evolve.db.close()

def main():
    log.debug('sys.argv = %s', sys.argv)
    # parse command line
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'cdr:ebg:hi:k:ln:p:q:sz:t:uvm', ['qt=','topology=','update=','node_type=','nodes=','dom_bias=','dom_value=','dom_weight=','nodes_per_input=','network=','plotbpg=','plotnets=','unroll','nb_dist=','toponly','movie=','sim=','statlog='])
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
    server_addr = 'localhost'
    client = 0
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
        elif o == '-i':
            g_index = int(a)
        elif o == '--plotbpg':
            plotbpg = a
        elif o == '--plotnets':
            plotnets = a
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
            evolve.master = 1
        elif o == '--statlog':
            evolve.statlog = a
        else:
            log.critical('unhandled option %s',o)
            return 1

    if record and not qtopts:
        qtopts = '-geometry 640x480'

    # check options
    if gui + client + create_initial_population > 1 :
        log.critical('gui, client, create_initial are mutually exclustive modes')
        return 1
    if g_index != None and not runsim and not plotbpg and not plotnets:
        log.critical('What do you want me to do with that individual?')
        return 1
        
    # before we do anything, fork if necessary
    if client and background:
        import daemon
        daemon.createDaemon()
        # record pid so it can be used by monitoring programs
        open('/tmp/client.pid', 'w').write('%d'%(os.getpid()))

    # connect to db
    if socket.gethostname() == server_addr:
        link = ('localhost',12345)
    else:
        link = (server_addr,12345)
    storage = ClientStorage(link)
    evolve.db = DB(storage)
    evolve.conn = evolve.db.open()
    root = evolve.conn.root()

    # The asyncore loop thread processes invalidate messages when we
    # call transaction.get.begin() or transaction.get.commit().  If we
    # explicitly call conn.sync() we will also process all of the
    # invalidate messages.
    global once_only
    if once_only:
        log.debug('Starting asyncore thread')
        thread.start_new_thread(asyncore.loop,())
        once_only = 0

    if unlock:
        log.debug('release all locks')
        root[g].next_gen_lock = 0
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

        new_node_fns = { 'sigmoid' : node.Sigmoid }
        new_node_fn = new_node_fns[node_type]
        new_node_args = PersistentMapping(
                { 'bias_domain': dom_bias,
                  'weight_domain' : dom_weight,
                  'quanta': quanta })
        new_network_args = PersistentMapping(
                { 'num_nodes' : num_nodes,
                  'num_inputs' : num_inputs,
                  'num_outputs' : num_outputs,
                  'new_node_fn': new_node_fn,
                  'new_node_args' : new_node_args,
                  'topology' : topology,
                  'update_style' : update_style,
                  'nb_dist' : nb_dist })
        if simulation == 'bpg':
            new_individual_fn = bpg.BodyPartGraph
            new_individual_args = PersistentMapping(
                    { 'network_args' : new_network_args })
            new_sim_fn = sim.BpgSim
        elif simulation == 'pb':
            new_individual_fn = network.Network
            new_individual_args = new_network_args
            new_sim_fn = sim.PoleBalanceSim
        new_sim_args = PersistentMapping ({ 'max_simsecs' : max_simsecs })

        root[g] = evolve.Generation(popsize, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)

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
                    print 'Generation: ',k #,i
        else:
            # print list of individuals in a generation
            print 'Num\t| Score'
            for i in range(len(root[g])):
                print '%d\t| %s'%(i, str(root[g][i].score))
            print 'Generation: name=%s gen=%d final_gen_num=%d'%(g,
                                                          root[g].gen_num,
                                                          root[g].final_gen_num)
    if change_generations or create_initial_population:
        root[g].final_gen_num = root[g].gen_num + evolve_for_generations
        transaction.commit()

    if client:
        log.debug('client mode')
        # look for jobs
        if g:
            runs = [g]
        else:
            runs = [k for (k, i) in root.iteritems() if isinstance(i, evolve.Generation)]
        # run evolution
        for r in runs:
            if root[r].gen_num <= root[r].final_gen_num:
                log.debug('client evaluating %s',r)
                root[g].runClientLoop()
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

        s = root[g].new_sim_fn(secs)
        s.add(root[g][i])
        # restore saved random state - ensures simulation reproducibility
        #random.setstate(root[g].random_state)
        # set up tracing
        if tracefile:
            #siglog = trace.SignalLog()
            #siglog.fd = open(tracefile, 'w')
            #s.siglog = siglog
            #trace.writeHeader()
            s.doSignalLog(tracefile)
        import psyco
        psyco.full()
        if gui:
            log.info('Launching GUI')
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
    gc.enable()
    #gc.set_debug(gc.DEBUG_LEAK)
    random.seed()
    setup_logging()
    r = main()
    cleanup()
    sys.exit(r)