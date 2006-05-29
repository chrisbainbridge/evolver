#!/usr/bin/env python

from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import transaction

def main():
    server_addr = 'localhost'
    storage = ClientStorage((server_addr,12345))
    db = DB(storage)
    db.pack()

if __name__=='__main__':
    main()
