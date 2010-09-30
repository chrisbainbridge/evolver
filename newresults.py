#!/usr/bin/python

import db,os
from pdb import set_trace

sim = 'bpg'
D = os.path.expanduser('~/phd-data/new/%s/'%sim)

print 'run model q top neurons timing mut mp genpop curg score'

def do(i):
    f = sim[0]+str(i).zfill(3)
    r = db.connect(zodb=D+f)
    g = r[f]
#    print f,len(g.scores), 'generations'
    run = f
    model = 'taga'
    if sim=='pb': network_args = g.new_individual_args
    if sim=='bpg': network_args = g.new_individual_args['network_args']
    q = str(network_args['new_node_args']['quanta']).zfill(2)
    if q=='00': q='fp'
    top = network_args['topology']
    neurons = str(network_args['num_nodes']).zfill(2)
    timing = network_args['update_style']
    mut = g.mut
    mp = str(g.mutationRate)
    genpop = str(len(g)).zfill(3)
    for x in (run,model,q,top,neurons,timing,mut,mp,genpop):
#        print x
        assert type(x) is str
    s = ' '.join((run,model,q,top,neurons,timing,mut,mp,genpop))
#    print s
    for curg in range(0,len(g.scores)):
        score = g.scores[curg].max
        print s,curg,'%.2f'%score
    db.close()

if __name__=='__main__':
    for i in range(458,534):
        do(i)

