#!/usr/bin/python

from unittest import TestCase
import logging
import sys
import time
import testoob
import transaction

import ev
import ev_test
from test_common import *
import cluster
import db

def run(gen):
    hosts = ('bw64node01','bw64node02','bw64node03','bw64node04')
    cluster.startZeoClients(hosts, gen)
    r = db.connect()
    g = r[gen]
    while g.gen_num < g.final_gen_num or g.leftToEval():
        time.sleep(5)
        db.sync()
    cluster.stopZeoClients(hosts)

def dbset(g, k, v):
    db.sync()
    c = 0
    while 1:
        try:
            setattr(g, k, v)
            transaction.commit()
            break
        except:
           c += 1
           if c > 10:
                raise

def runRateTest(gn):
    # run test with 1,2,4,8,16,32,62 client nodes
    # 2 nodes are already used - zeoserver and master
    f = open('test/rate.txt', 'w')
    f.write('pcs\teh\n')
    r = db.connect()
    g = r[gn]
    nh = [4,8,15,30,45,59]
    nh.reverse()
    for n in nh:
        dbset(g, 'pause', 1)
        print 'n=%d'%n
        hosts = list(set(cluster.HOSTS) - set([cluster.MASTER]))
        hosts = hosts[:n]
        print '%d hosts : %s'%(len(hosts), hosts)
        assert len(hosts) == n
        for x in g:
            dbset(x, 'score', None)
        dbset(g, 'updateRate', 0)
        dbset(g, 'updateInfo', ('reset', time.time(), 0))
        cluster.startZeoClients(hosts, gn)
        starttime = time.time()
        dbset(g, 'pause', 0)
        print 'unpaused clients'
        while g.leftToEval():
            time.sleep(1)
            db.sync()
        endtime = time.time()
        runtime = endtime - starttime
        e = len(g)
        print '%d evals in %d seconds'%(e, runtime)
        eh = e*(60*60)/runtime
        f.write('%d\t%d\n'%(n, eh))
        f.flush()
        cluster.stopZeoClients(hosts)
    f.close()

class TestClusterElite(TestCase):
    def test_0_startZeoServer(self):
        cluster.startZeoServer()
    def test_1_delete(self):
        ev_test.delete('test_clusterElite')
    def test_2_create(self):
        ev_test.create('test_clusterElite', '--nodetype sigmoid --ga-elite')
    def test_3_run(self):
        run('test_clusterElite')

class TestClusterSteadyState(TestCase):
    def test_0_startZeoServer(self):
        cluster.startZeoServer()
    def test_1_delete(self):
        ev_test.delete('test_clusterSS')
    def test_2_create(self):
        ev_test.create('test_clusterSS', '--nodetype sigmoid --ga-steady-state')
    def test_3_run(self):
        run('test_clusterSS')

class TestClusterRate(TestCase):
    def test_0_startZeoServer(self):
        cluster.startZeoServer()
    def test_1_delete(self):
        ev_test.main('ev.py -r test_clusterRate -e')
    def test_2_create(self):
        ev_test.main('ev.py -r test_clusterRate -p 50 -t 30 -g 2 --topology full'\
                ' --update sync --nodetype sine --nodes 5 --sim bpg --fitness movement')
    def test_3_run(self):
        # run for a few gens to get a more typical workload
        run('test_clusterRate')
        ev_test.main('ev.py -r test_clusterRate -g 50')
    def test_4_run(self):
        runRateTest('test_clusterRate')

if __name__ == "__main__":
    setup_logging()
    if not cluster.isZeoServerRunning():
        print 'Can\'t contact ZEO server, skipping tests...'
        sys.exit(0)
    test_main()
