from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction
import thread
import asyncore
import re
import socket

CLUSTER_MASTER = 'bw64node01.inf.ed.ac.uk'
CLUSTER_REGEXP = r'bw240n\d\d.inf.ed.ac.uk'

conn = None
once_only = 1 # don't run stuff twice when main is called in test harness

def connect(server_addr = None):
    if not server_addr:
        server_addr = getDefaultServer()
    MB = 1024**2
    storage = ClientStorage((server_addr, 12345), cache_size=16*MB)
    db = DB(storage)
    global conn, once_only
    conn = db.open()
    root = conn.root()
    conn.sync()
    if once_only:
        thread.start_new_thread(asyncore.loop,())
        once_only = 0
    return root

def sync():
    if conn:
        conn.sync()

def getDefaultServer():
    if re.match(CLUSTER_REGEXP,  socket.gethostname()):
        server_addr = CLUSTER_MASTER
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', 12345))
            s.close()
            server_addr = 'localhost'
        except:
            server_addr = CLUSTER_MASTER
    return server_addr
