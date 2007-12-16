#!/usr/bin/env python

"""Front end to the evolution and simulation engine.

===== Options for all invocations =====

 -z server_addr       ZEO DB server (default localhost)
 -r name              Select evolutionary run with given name
 -i x                 Select individual with index x
 -d                   debug
 --seed x             Set random seed, x is upto 32 bit hex

===== Client mode =====

 -c                   Client - Do evals (port always 8090)
     -b                 Run client in background
 -m                   Master - Do evolution and logging
 --cluster            Start all cluster clients

===== Erase =====

 -e                   Delete this run
 --blank              Set all scores to None to force re-eval

===== Create initial population =====

 -p x                 Create initial population of size x
     -q x             Use discrete model with x states
     -t x             Run simulation for x seconds (default 30)
     -g x             Final generation, prefix +- for relative (default 99)
     --model x        Type of node [sigmoid,logical,beer,if,ekeberg,sine,srm]
     --neurons x      Total number of nodes, including inputs and outputs (default 10)
     --top x          Neural network topology [full,1d,2d,nk]
     --timing x       Neuron timing style [sync,async]
     --uniform        Use a single set of neuron parameters for the whole network
                        (eg. like the global update fn in a cellular automata)
     --bias x,y       Domain for bias is [x,y] (default [0,1])
     --weight x,y     Domain for weight values (default [-7,7])
     --k x            For 1d,2d : neighbourhood radius (square for 2d)
                      For nk : degree of connectivity k
     --fitness x      Fitness function [bpgsim only], can be:
                        cumulativez : average z value of all body parts summed over time
                        meandistance : average Euclidean distance of all body parts
                        movement : sum of distances from previous frame
                        walk : movement and meandistance combined
                        meanxv : mean velocity on X-axis
 --ga                 Genetic algorithm [elite,rank,tournament,steadystate]
 --mp x               Mutation probability
 --mut                Mutation type [gauss,uniform]
 --noise x            Standard deviation of Gaussian noise applied to sensors and motors

===== Unlock =====

 -u                   Release all locks in specified run

===== List =====

 -l                   List networks and their scores in evolution run

===== Plot graphs =====

 --plotnets f.type    Plot all of the control networks in bpg
 --plotbpg f.type     Plot to file. Type can be dot, ps, png, etc.
     --toponly        Only draw topology - no weights or bi-connects
     --unroll         Unroll bpg before converting to dot file
 --pf f.pdf           Plot min/mean/max fitness graph for specified generation
 --plotpi             Plot mutations vs prob. of child.fitness > parent fitness
 --plotfc             Plot mutations vs observed fitness change

===== Sim =====

 -s                   Run a simulation
 -v                   Visualise with graphical user interface
   --qt 'qt options'  Pass string onto QT options (eg. -geometry 640x480)
   --movie file.avi   Record movie to file.avi
 --ps fname           Record signal traces. f can be *.[txt/trace/eps]
   --nostrip          Don't strip flat signals from the trace
 --sim x              Select simulator [pb, bpg]
 --lqr                Use LQR controller for pb sim
 """

# For some reason, this has to be the very first thing that we do, otherwise the
# call To ClientStorage in db.py will either silently exit the process, or the
# process will become suspended waiting on some interrupt. Presumably merely
# importing ZODB and/or the persistent classes does something (eg. records the
# fact that we have a controlling terminal) that causes problems later on.
# This could be related to the version bump from zodb-3.6.0 to 3.7.2 (no time to
# investigate further atm).
import sys
background = 0
if '-b' in sys.argv:
    # before we do anything, fork if necessary
    print 'backgrounding...'
    import daemon, os
    daemon.createDaemon()
    # record pid so it can be used by monitoring programs
    f = open('/tmp/client.pid', 'w')
    f.write('%d\n'%(os.getpid()))
    f.close()
    background = 1
    sys.argv.remove('-b')

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
import cluster
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

def main():
    log.debug(' '.join(sys.argv))
    # parse command line
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'cdr:eg:hi:lp:q:sz:t:uvm',
                ['blank', 'qt=', 'top=', 'timing=', 'model=', 'neurons=',
                    'bias=', 'weight=', 'lqr', 'ga=', 'mp=', 'mut=', 'noise=',
                    'network=', 'nostrip', 'plotbpg=', 'pf=', 'plotnets=',
                    'ps=', 'unroll', 'k=', 'toponly', 'movie=', 'sim=', 'seed=',
                    'fitness=', 'plotpi=', 'plotfc=', 'cluster', 'uniform'])
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
    model = 'sigmoid'
    num_nodes = 10
    simulation = 'bpg'
    quanta = 0
    server_addr = db.getDefaultServer()
    plotfitness = None
    plotpi = None
    plotfc = None
    client = 0
    master = 0
    g = None
    create_initial_population = 0
    delete = 0
    unlock = 0
    k = None
    bias = None
    weight = None
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
    rank = 0
    tournament = 0
    max_simsecs = 30
    mutationRate = 0.05
    genabs = 1
    numberOfGenerations = None
    noise = 0.005
    strip = 1
    lqr = 0
    blank = 0
    mut = 'uniform'
    uniform = 0
    seed = random.randint(0,0xFFFFFFFF)
    for o, a in opts:
        log.debug('parsing %s %s',o,a)
        if o == '-c':
            client = 1
        elif o == '-e':
            delete = 1
        elif o == '-r':
            g = a
        elif o == '-g':
            if a[0] in '+-':
                genabs = 0
            numberOfGenerations = int(a)-1
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
        elif o == '--top':
            topology = a
        elif o == '--timing':
            update_style = a
        elif o == '--model':
            model = a
        elif o == '--neurons':
            num_nodes = int(a)
        elif o == '--bias':
            # a is of form 'x,y'
            bias = eval(a)
        elif o == '--weight':
            weight = eval(a)
        elif o == '--ga':
            ga = a
        elif o == '--lqr':
            lqr = 1
        elif o == '--mp':
            mutationRate = float(a)
        elif o == '--mut':
            mut = a
        elif o == '--uniform':
            uniform = 1
        elif o == '--noise':
            noise = float(a)
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
        elif o == '--ps':
            tracefile = a
        elif o == '--unroll':
            unroll = 1
        elif o == '--k':
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
        elif o == '--fitness':
            assert a in ['meandistance', 'cumulativez', 'movement', 'walk', 'after', 'meanxv']
            fitnessFunctionName = a
        elif o == '--blank':
            blank = 1
        elif  o == '--cluster':
            print 'Starting all cluster clients...'
            cluster.startZeoClients()
        elif o == '--seed':
            seed = int(a,16)
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

    if create_initial_population or client or master or runsim:
        log.info('Random seed: %.8x', seed)
        random.seed(seed)

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
            # FIXME: this should be evolved or user specified
            num_inputs = min(3,num_nodes)
            num_outputs = min(3,num_nodes)

        new_node_arg_class_map = {
                'sigmoid' : node.SigmoidNode,
                'logical': node.LogicalNode,
                'beer' : node.BeerNode,
                'if' : node.IfNode,
                'srm' : node.SrmNode,
                'ekeberg' : node.EkebergNode,
                'sine' : node.SineNode }
        new_node_class = new_node_arg_class_map[model]

        new_node_args = { 'quanta' : quanta }
        if bias:
            assert new_node_class is node.BeerNode
            new_node_args['biasDomain'] = bias
        if weight:
            assert issubclass(new_node_class, node.WeightNode)
            new_node_args['weightDomain'] = weight

        new_network_args = {
                'num_nodes' : num_nodes,
                'num_inputs' : num_inputs,
                'num_outputs' : num_outputs,
                'new_node_class': new_node_class,
                'new_node_args' : new_node_args,
                'topology' : topology,
                'update_style' : update_style,
                'radius' : radius,
                'uniform' : uniform}

        new_sim_args = { 'max_simsecs' : max_simsecs,
                         'noise_sd' : noise}
        if simulation == 'bpg':
            new_individual_fn = bpg.BodyPartGraph
            new_individual_args = { 'network_args' : new_network_args }
            new_sim_fn = sim.BpgSim
            new_sim_args['fitnessName'] = fitnessFunctionName
        elif simulation == 'pb':
            new_individual_fn = network.Network
            new_individual_args = new_network_args
            new_sim_fn = sim.PoleBalanceSim

        root[g] = evolve.Generation(popsize, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args, ga, mutationRate, mut, numberOfGenerations)
        if simulation == 'pb':
            for x in root[g]:
                x.weights = [random.randrange(-7,7) for i in range(4)]

        log.debug('committing all subtransactions')
        transaction.commit()
        log.debug('commit done, end of create_initial_population')

    elif not create_initial_population and not runsim and (numberOfGenerations or mutationRate or max_simsecs):
        if numberOfGenerations != None:
            if genabs:
                root[g].final_gen_num = numberOfGenerations
            else:
                root[g].final_gen_num += numberOfGenerations
        if mutationRate:
            root[g].mutationRate = mutationRate
        if max_simsecs:
            root[g].new_sim_args['max_simsecs'] = max_simsecs
        transaction.commit()

    elif g and g not in root and not delete:
        log.error('Generation %s not in db %s', g, root.keys())
        return

    if not g and (delete or blank or plotfitness or plotpi or plotfc or plotbpg or plotnets):
        log.critical('which generation?')
        return 1

    if delete and root.has_key(g):
        del(root[g])
        transaction.commit()

    if blank:
        for x in root[g]:
            x.score = None
        transaction.commit()

    if plotfitness or plotpi or plotfc:
        if plotfitness:
            plot_generation_vs_fitness(root[g], plotfitness, g)
        elif plotpi:
            plot_mutation_vs_prob_improvement(root[g], plotpi, g)
        elif plotfc:
            plot_mutation_vs_fitness_change(root[g], plotfc, g)

    if plotbpg or plotnets:
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
                    fn = 'default'
                    if 'fitnessName' in i.new_sim_args.keys():
                        fn = i.new_sim_args['fitnessName']
                    rate = 0
                    if hasattr(i, 'updateRate'):
                        rate = i.updateRate
                    m = i.getMaxIndividual()
                    sm = ''
                    if m != None:
                        sm = '%.2f'%m
                    print 'Generation: %s [ga=%s gen=%d/%d max=%s fitness=%s evh=%d]'%(k,
                            i.ga, i.gen_num, i.final_gen_num,
                            sm, fn, rate)
        else:
            # print list of individuals in a generation
            print 'Num\tScore\tP.score\tMutations'
            for i in range(len(root[g])):
                b = root[g][i]
                pf = b.parentFitness
                if pf == None:
                    s_pf = 'X'
                else:
                    s_pf = ' %.2f'%pf
                if b.score == None:
                    s_f = {0:'X', 1:'X*%d'%b.busy.i, 2:'X*>2'}[b.busy.i]
                else:
                    s_f = '%.2f'%b.score
                s_m = 'X'
                if b.mutations != None:
                    s_m = '%d'%b.mutations
                print '%d\t%s\t%s\t%s'%(i, s_f, s_pf, s_m)
            fn = 'default'
            if 'fitnessName' in root[g].new_sim_args.keys():
                fn = root[g].new_sim_args['fitnessName']
            rate = 0
            if hasattr(root[g], 'updateRate'):
                rate = root[g].updateRate
            print 'Generation: name=%s ga=%s gen=%d/%d fitness=%s evh=%d'%(g,
                    root[g].ga, root[g].gen_num, root[g].final_gen_num, fn,
                    rate)
            if root[g].updateInfo.updating:
                print 'Update started on %s %d seconds ago'%(root[g].updateInfo.host,
                                root[g].updateInfo.elapsed)

    if client or master:
        h = {(1,0):'Master', (0,1):'Client', (1,1):'Master && Client'}
        mode = h[master,client]
        log.info('%s running on %s', mode, cluster.getHostname())
        while 1:

            # find all generations that aren't finished
            db.sync()
            if g:
                runs = [g]
            else:
                runs = [k for (k, i) in root.iteritems() if isinstance(i, evolve.Generation)]
            done = []
            done += [r for r in runs if root[r].ga == 'steadystate' and
                    len(root[r].scores) == root[r].final_gen_num ]
            done += [r for r in runs if root[r].ga != 'steadystate' and
                    len(root[r].scores) == root[r].final_gen_num+1]
            log.debug('done: %s / %s', done, runs)

            # if everything we can do is done, exit
            if not set(runs) - set(done):
                break

            ready = []
            if master:
                ready += [r for r in runs if root[r].ga == 'steadystate' and
                        len(root[r].scores) < root[r].final_gen_num ]
                ready += [r for r in runs if root[r].ga != 'steadystate' and not
                        root[r].leftToEval() and len(root[r].scores) <
                        root[r].final_gen_num+1]
            if client:
                ready += [r for r in runs if root[r].ga == 'steadystate' and
                        len(root[r].scores) < root[r].final_gen_num ]
                ready += [r for r in runs if root[r].ga != 'steadystate' and
                        root[r].leftToEval()]

            log.debug('ready %s', ready)
            if ready:
                r = random.choice(ready)
                log.info('run %s (%d/%d) / %s ', r, root[r].gen_num,
                        root[r].final_gen_num, mode)
                root[r].runClientInnerLoop(master, client)
            else:
                log.info('Nothing to do, sleeping for 5s...')
                time.sleep(5)

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
        if noise == None:
            noise = root[g].new_sim_args['noise_sd']
        if root[g].new_sim_fn == sim.BpgSim:
            if not fitnessFunctionName:
                fitnessFunctionName = root[g].new_sim_args['fitnessName']
            s = root[g].new_sim_fn(secs, fitnessFunctionName, noise)
        elif root[g].new_sim_fn == sim.PoleBalanceSim:
            s = root[g].new_sim_fn(secs, noise_sd=noise)
        if lqr:
            s.setUseLqr(quanta)
        else:
            s.add(root[g][i])
        # set up tracing
        plotTrace = 0
        if tracefile:
            (traceBase, traceExt) = os.path.splitext(tracefile)
            if traceExt in ['.trace', '.txt']:
                fname = tracefile
            elif traceExt in ['.eps', '.pdf']:
                fname = '%s.trace'%traceBase
                plotTrace = 1
            elif traceBase == '-':
                fname = 'tmp.trace'
                plotTrace = 1
                traceExt = '.pdf'
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
            assert traceExt in ['.eps','.pdf']
            if strip:
                stripTraceFile(fname)
            if root[g].new_individual_args.has_key('new_node_args'):
                q = root[g].new_individual_args['new_node_args']['quanta']
            else:
                q = root[g].new_individual_args['network_args']['new_node_args']['quanta']
            plots = plotSignals(fname, q, traceExt)
            if not plots:
                log.critical('failed to generate trace - bad sim?')
                return 1
            if tracefile == '-':
                for f in plots:
                    cmd = 'kpdf %s'%f
                    log.info(cmd)
                    os.system(cmd)
        s.destroy()

def cleanup():
    log.debug('ev.py cleanup')
    transaction.get().abort()
    if db.conn:
        db.conn.close()

if __name__=='__main__':
    setup_logging()
    r = main()
    cleanup()
    sys.exit(r)
