from ZEO.ClientStorage import ClientStorage
from ZODB.FileStorage import FileStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction
import socket
import os
import cluster

conn = None

def connect(server=None, zodb=None):
    global conn
    close() # close any existing connection
    if zodb:
        conn = DB(FileStorage(os.path.expanduser(zodb))).open()
    else:
        if not server:
            server = cluster.ZEOSERVER
        s = server
        p = 12345
        if ':' in server:
            s, p = server.split(':')
            p = int(p)
        MB = 1024**2
        storage = ClientStorage((s,p), cache_size=16*MB)
        db = DB(storage)
        conn = db.open()
    root = conn.root()
    return root

def reconnect():
    # I dont think this actually works... errors about re-using a connection
    transaction.abort()
    conn.close()
    connect()

def sync():
    conn.sync()

def close():
    global conn
    if conn:
        transaction.abort()
        conn.close()
        conn.db().close()
        conn = None
