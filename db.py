from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction
import thread
import threading
import asyncore
import socket
import cluster

conn = None
once_only = 1 # don't run stuff twice when main is called in test harness
serverName = None

def getDefaultServer():
    global serverName
    if cluster.isHost():
        serverName = cluster.ZEOSERVER
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', 12345))
            s.close()
            serverName = 'localhost'
        except:
            serverName = cluster.ZEOSERVER
    return serverName

def connect(server = None):
    global conn, once_only, serverName
    if ':' in server:
        serverName, port = server.split(':')
        port = int(port)
    else:
        serverName, port = server, 12345
    if not serverName:
        serverName = getDefaultServer()
    MB = 1024**2
    storage = ClientStorage((serverName, port), cache_size=16*MB)
    db = DB(storage)
    conn = db.open()
    root = conn.root()
    if once_only:
        thread.start_new_thread(asyncore.loop,())
        once_only = 0
    return root

def reconnect():
    # I dont think this actually works... errors about re-using a connection
    transaction.abort()
    conn.close()
    connect()

def sync():
    conn.sync()

def e():
    return threading.enumerate()
