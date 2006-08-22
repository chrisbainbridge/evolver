from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction
import thread
import asyncore

conn = None
once_only = 1 # don't run stuff twice when main is called in test harness

def connect(server_addr = 'localhost'):
    MB = 1024**2
    storage = ClientStorage((server_addr, 12345), cache_size=16*MB)
    db = DB(storage)
    global conn
    conn = db.open()
    root = conn.root()
    conn.sync()
    if not once_only:
        thread.start_new_thread(asyncore.loop,())
    return root

def sync():
    if conn:
        conn.sync()
