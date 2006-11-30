#!/usr/bin/python

from unittest import TestCase
import logging
import sys
import time
import testoob

import ev
import ev_test
from test_common import *
import cluster
import db

rl = logging.getLogger()

def run(gen):
    hosts = ('bw64node01','bw64node02','bw64node03','bw64node04')
    cluster.startZeoClients(hosts, gen)
    r = db.connect()
    g = r[gen]
    while g.gen_num < g.final_gen_num and g.leftToEval():
        time.sleep(5)
        db.sync()
    cluster.stopZeoClients(hosts)

class TestClusterElite(TestCase):
    def test_0_startZeoServer(self):
        cluster.startZeoServer()
    def test_1_delete(self):
        ev_test.delete('test_clusterElite')
    def test_2_create(self):
        ev_test.create('test_clusterElite', '--node_type sigmoid --ga-elite')
    def test_3_run(self):
        run('test_clusterElite')

class TestClusterSteadyState(TestCase):
    def test_0_startZeoServer(self):
        cluster.startZeoServer()
    def test_1_delete(self):
        ev_test.delete('test_clusterSS')
    def test_2_create(self):
        ev_test.create('test_clusterSS', '--node_type sigmoid --ga-steady-state')
    def test_3_run(self):
        run('test_clusterSS')

if __name__ == "__main__":
    if not cluster.isZeoServerRunning():
        print 'Can\'t contact ZEO server, skipping tests...'
        sys.exit(0)
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
