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

class TestCluster(TestCase):
    def test_0_startZeoServer(self):
        cluster.startZeoServer()
    def test_1_delete(self):
        ev_test.delete('test_cluster')
    def test_2_create(self):
        ev_test.create('test_cluster', '--node_type sigmoid')
    def test_3_run(self):
        hosts = ('bw64node01','bw64node02','bw64node03','bw64node04')
        cluster.startZeoClients(hosts, 'test_cluster')
        r = db.connect()
        g = r['test_cluster']
        while g.gen_num < g.final_gen_num and g.leftToEval():
            time.sleep(5)
            db.sync()
        cluster.stopZeoClients(hosts)

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
