#!/usr/bin/python
"""design.py
    --pb            Use pole balancer sim (default: bpg)
    --start x       Start from gen x
    -p              Pretend; change files but not database
    --server x      Write ev calls to server
design.py 600 to just generate results.txt"""

import sys, re, os, logging, getopt
from logging import debug, error
import random
from persistent.list import PersistentList
import transaction
import db
from data import Run

logging.getLogger().setLevel(logging.DEBUG)

D = '../data/'

def main():

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'p', ['pb', 'start=', 'server='])
        if not opts:
            print __doc__
            sys.exit(1)
    except getopt.GetoptError, e:
        error(e)
        sys.exit(1)

    sim = 'bpg'
    prefix = 'b'
    start = 0
    pretend = 0
    server = None
    for o, a in opts:
        if o == '--pb':
            sim = 'pb'
            prefix = 'p'
        elif o == '--start':
            start = int(a)
        elif o == '-p':
            pretend = 1
        elif o == '--server':
            server = a

    if server:
        r = db.connect()
        if 'runs' not in r.keys():
            r['runs'] = PersistentList()
    f = open(D+'des.txt','r')
    ss = f.readlines()
    f.close()
    i = 0
    models = ['beer', 'ekeberg', 'if', 'logical', 'sigmoid', 'sine', 'srm' ]
    qs = [0,2,4,8,16,32,64]
    tops = ['1dr1', '2dr1', 'full', 'nk1', 'nk2', 'nk3']
    neuronsl = [16, 4, 9]
    timings = ['async', 'sync']
    muts = ['gauss', 'uniform']
    mps = [0.01, 0.05]
    genpops = [50, 100]
    failed = 0
    skipped = 0
    f = open(D+'results-%s.txt'%sim,'w')
    f.write('run model q top neurons timing mut mp genpop curg score\n')
    # do first levels replicate 10 times
    base = ['1 '*8+'\n' for y in range(0,10)]
    fx = open(D+'des-filtered.txt','w')
    fx.write('model q top neurons timing mut mp genpop\n')


    for s in base + ss[1:]:
        model = models[int(s[0])-1]
        q = qs[int(s[2])-1]
        top_extra = {'full':'full', '1dr1':'1d --k 1', '2dr1':'2d --k 1',
                'nk1':'nk --k 1',  'nk2':'nk --k 2', 'nk3':'nk --k 3'}

        tk = tops[int(s[4])-1]
        top = top_extra[tk]
        neurons = neuronsl[int(s[6])-1]
        timing = timings[int(s[8])-1]
        mut = muts[int(s[10])-1]
        mp = mps[int(s[12])-1]
        genpop = genpops[int(s[14])-1]

        # skip invalid or bad data points
        if top[:2] == '2d' and neurons == 4 or model == 'logical' and (tk=='full' and\
            neurons!=4 or tk=='2dr1' or q>8 or q==0):
            skipped += 1
            continue

        fx.write(s)
        times = 1
        # force replicates for logical since so many of its rows are filtered out
        if model == 'logical':
            times = 2
        count = 0
        while count<times:
            run = '%s%.3d'%(prefix,i)
            for g in range(0,genpop):
                s = "%s %s %.2d %s %.2d %s %s %.2f %.3d %d X\n"%(run,model,q,tk,neurons,timing,mut,mp,genpop,g)
                f.write(s)

            if i >= start:
                if not server and not pretend:
                    os.system('../src/ev -r %s -e'%(run))
                s = 'ev -r %s -p %d -g %d -t 30 --sim %s --model %s --neurons %s '\
                '-q %d --top %s --timing %s --mut %s --mp %s --fitness meanxv'%(run,
                        genpop, genpop, sim, model, neurons, q, top, timing, mut, mp)
                debug(s)
                e = 0
                if not pretend:
                    if server:
                        r['runs'].append(Run(run, s))
                    else:
                        e = os.system('../src/'+s)
                if e:
                    error('%s', s)
                    failed += 1
            i += 1
            count += 1
    if server and not pretend:
        transaction.commit()

    debug('%d OK, %d FAILED, %d SKIPPED', i, failed, skipped)

if __name__=='__main__':
    main()
