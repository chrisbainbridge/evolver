#!/usr/bin/python

import random

number = [2,4,8,10]
model = ['beer','sine','sigmoid']
topology = ['1d','2d','3d','full']
quanta = [4,8,16,0]

factors = {'number' : number, 'model' : model, 'topology' : topology, 'quanta' : quanta }

print 'number\tmodel\ttopology\tquanta\tfitness'
for n in number:
    for m in model:
        for t in topology:
            for q in quanta:
                print '%d\t%s\t%s\t\t%d\t%f'%(n,m,t,q,random.gauss(1000,100))
