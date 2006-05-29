from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction

conn = None

def connect():
    server_addr = 'localhost'
    storage = ClientStorage((server_addr,12345))
    db = DB(storage)
    global conn
    conn = db.open()
    root = conn.root()
    conn.sync()
    import thread
    import asyncore
    thread.start_new_thread(asyncore.loop,())
    return root
