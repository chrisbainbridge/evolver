from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction
import socket
import cluster

conn = None
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
    global conn, serverName
    if not server:
        serverName, port = getDefaultServer(), 12345
    elif ':' in server:
        serverName, port = server.split(':')
        port = int(port)
    else:
        serverName, port = server, 12345
    MB = 1024**2
    storage = ClientStorage((serverName, port), cache_size=16*MB)
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
