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

def getDefaultServer():
    if cluster.isHost():
        server = cluster.ZEOSERVER
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', 12345))
            s.close()
            server = 'localhost'
        except:
            server = cluster.ZEOSERVER
    return server

def connect(server=None, zodb=None):
    global conn
    if zodb:
        conn = DB(FileStorage(os.path.expanduser(zodb))).open()
    else:
        if not server:
            s, p = getDefaultServer(), 12345
        elif ':' in server:
            s, p = server.split(':')
            p = int(p)
        else:
            s, p = server, 12345
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
