import sys
import logging
import node
import bpg
import sim

def setup_logging(rootlogger):
    level = logging.INFO
    if '-d' in sys.argv:
        level = logging.DEBUG
        sys.argv.remove('-d')

    rootlogger.setLevel(level)
    for m in 'sim', 'glwidget', 'bpg', 'neural', 'qtapp':
        l = logging.getLogger(m)
        l.setLevel(level)
    logging.basicConfig()

new_node_fn = node.Sigmoid 
new_node_args = { 'bias_domain' : (-5,5),
                  'weight_domain' : (-7,7),
                  'quanta': None }
new_network_args = { 'num_nodes' : 5,
                     'num_inputs' : 2,
                     'num_outputs' : 3,
                     'new_node_fn': new_node_fn,
                     'new_node_args' : new_node_args,
                     'topology' : '1d',
                     'update_style' : 'async',
                     'nb_dist' : 1 }
new_individual_fn = bpg.BodyPartGraph
new_individual_args = { 'network_args' : new_network_args }
new_sim_fn = sim.BpgSim 
new_sim_args = { 'max_simsecs' : 1 }
