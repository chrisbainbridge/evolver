#!/usr/bin/python

import random

number = [4,9]
model = ['beer','sine','sigmoid','ekeberg','x']
topology = ['1d','2d','full']
quanta = [10,100,1000,0]
ga = ['ss','gen']

factors = {'number' : number, 'model' : model, 'topology' : topology, 'quanta' : quanta }

def main():
    print 'number\tmodel\ttopology\tquanta\tfitness'
    for g in ga:
        for n in number:
            for m in model:
                for t in topology:
                    for q in quanta:
                        print '%s\t%d\t%s\t%s\t\t%d\t%f'%(g,n,m,t,q,random.gauss(1000,100))

if __name__ == '__main__':
    main()
