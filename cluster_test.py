#!/usr/bin/python

from unittest import TestCase
from logging import debug, critical
import sys
import time
import testoob
import transaction

import ev_test
from test_common import *
import cluster
import db

def run(gen):
    hosts = ('bw64node01','bw64node02','bw64node03','bw64node04')
    h = cluster.startZeoClients(hosts, gen)
    assert len(h) == len(hosts)
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
        debug('n=%d',n)
        hosts = list(set(cluster.HOSTS) - set([cluster.MASTER]))
        hosts = hosts[:n]
        debug('%d hosts : %s', len(hosts), hosts)
        assert len(hosts) == n
        for x in g:
            dbset(x, 'score', None)
        dbset(g, 'updateRate', 0)
        dbset(g, 'updateInfo', ('reset', time.time(), 0))
        h = cluster.startZeoClients(hosts, gn)
        assert len(h) == len(hosts)
        starttime = time.time()
        dbset(g, 'pause', 0)
        debug('unpaused clients')
        while g.leftToEval():
            time.sleep(1)
            db.sync()
        endtime = time.time()
        runtime = endtime - starttime
        e = len(g)
        debug('%d evals in %d seconds', e, runtime)
        eh = e*(60*60)/runtime
        f.write('%d\t%d\n'%(n, eh))
        f.flush()
        cluster.stopZeoClients(hosts)
    f.close()

class TestClusterElite(TestCase):
    def setUp(self):
        ev_test.g = 'test_clusterElite'
    def test_1_delete(self):
        ev_test.delete()
    def test_2_create(self):
        ev_test.args = '--nodetype sigmoid --elite'
        ev_test.create()
    def test_3_run(self):
        run(ev_test.g)

class TestClusterSteadyState(TestCase):
    def setUp(self):
        ev_test.g = 'test_clusterSS'
    def test_1_delete(self):
        ev_test.delete()
    def test_2_create(self):
        ev_test.args = '--nodetype sigmoid --steadystate'
        ev_test.create()
    def test_3_run(self):
        run(ev_test.g)

class TestClusterRate(TestCase):
    def setUp(self):
        ev_test.g = 'test_clusterRate'
    def test_1_delete(self):
        ev_test.delete()
    def test_2_create(self):
        ev_test.args = '-p 50 -t 30 -g 2 --topology full --update sync'\
        '--nodetype sine --nodes 5 --sim bpg --fitness movement'
        ev_test.create()
    def test_3_run(self):
        # run for a few gens to get a more typical workload
        run(ev_test.g)
        ev_test.main('ev.py -r %s -g 50'%ev_test.g)
    def test_4_run(self):
        # now run the main rate test
        runRateTest(ev_test.g)

if __name__ == "__main__":
    setup_logging()
    if not cluster.isZeoServerRunning():
        critical('Can\'t contact ZEO server %s, skipping tests...', cluster.ZEOSERVER)
        sys.exit(0)
    hosts = ('bw64node02','bw64node03')
    h = cluster.startZeoClients(hosts)
    cluster.stopZeoClients(h)
    if len(h) != len(hosts):
        critical('Can\'t start ZEO clients %s, skipping tests...', hosts)
        sys.exit(0)
    test_main()
