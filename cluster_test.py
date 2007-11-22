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

def runRateTest(gn, single=0):
    # run test with 1,2,4,8,16,32,62 client nodes. The actual hosts are
    # hardcoded as cluster.HOSTS but cluster.MASTER is removed.
    f = open('test/rate.txt', 'w')
    f.write('pcs\teh\n')
    r = db.connect()
    g = r[gn]
    nh = [4,8,15,30,45,59]
    nh.reverse()
    if single:
        nh = [1]
    for n in nh:
        dbset(g, 'pause', 1)
        debug('n=%d',n)
        hosts = list(set(cluster.HOSTS) - set([cluster.MASTER]))
        hosts = hosts[:n]
        if single:
            hosts = 'localhost',
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
            time.sleep(10)
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

class Cluster:
    def test_0_delete(self):
        ev_test.delete(self.g)
    def test_1_create(self):
        ev_test.create(self.g, self.args)
    def test_2_run(self):
        run(self.g)

class Elite(Cluster, TestCase):
    g = 'test_cluster_elite'
    args = '--nodetype sigmoid --elite'

class SteadyState(Cluster, TestCase):
    g = 'test_cluster_ss'
    args = '--nodetype sigmoid --steadystate'

class TestClusterRate(Cluster, TestCase):
    g = 'test_cluster_rate'
    args = '-p 50 -t 30 -g 2 --topology full --update sync --nodetype sine --nodes 5 --sim bpg --fitness movement'
    def test_3_run(self):
        # this test will run after 5 gens of evolution, hopefully weeded out the
        # very bad individuals and so giving more realisitc results
        ev_test.main('ev.py -r %s -g 10'%self.g)
        runRateTest(self.g)

class SingleRate(Cluster, TestCase):
    g = 'test_single_rate'
    args = '-p 20 -t 30 -g 2 --topology full --update sync --nodetype sine --nodes 5 --sim bpg --fitness meandistance'
    def test_2_run(self):
        ev_test.main('ev.py -r %s -g 10'%self.g)
        runRateTest(self.g, single=1)

if __name__ == "__main__":
    setup_logging()
    single = 0
    if '-s' in sys.argv:
        cluster.ZEOSERVER='localhost'
        cluster.MASTER = 'localhost'
        single = 1
        sys.argv.remove('-s')
    if not cluster.isZeoServerRunning():
        critical('Can\'t contact ZEO server %s, skipping tests...', cluster.ZEOSERVER)
        sys.exit(0)
    if cluster.getHostname() == 'bob':
        critical('Not running on cluster, skipping tests...')
        sys.exit(0)
    test_main()
