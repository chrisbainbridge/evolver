#!/usr/bin/python

import re

p=458
f=open('mkruns.bpg')
cmds=f.readlines()
for s in cmds:
    m=re.match(r'(ev -r [pb])(\d\d\d)(.*)',s)
    r=m.group(1)+str(p)+' -f b'+str(p)+m.group(3)
    print r
    p+=1
