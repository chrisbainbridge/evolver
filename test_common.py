import sys
import logging
import testoob
import node
import bpg
import sim

def setup_logging():
    rootlogger = logging.getLogger()
    level = logging.ERROR
    if '-d' in sys.argv:
        level = logging.DEBUG
        sys.argv.remove('-d')

    rootlogger.setLevel(level)
    for m in 'sim', 'glwidget', 'bpg', 'neural', 'qtapp':
        l = logging.getLogger(m)
        l.setLevel(level)
    logging.basicConfig()

new_node_args_sigmoid = { 'weightDomain' : (-7,7),
                          'quanta': None }
new_node_args_logical = {'numberOfStates':2}
new_network_args = { 'num_nodes' : 5,
                     'num_inputs' : 2,
                     'num_outputs' : 3,
                     'new_node_class': node.SigmoidNode,
                     'new_node_args' : new_node_args_sigmoid,
                     'topology' : '1d',
                     'update_style' : 'async',
                     'radius' : 1 }
new_individual_fn = bpg.BodyPartGraph
new_individual_args = { 'network_args' : new_network_args }
new_sim_fn = sim.BpgSim 
new_sim_args = { 'max_simsecs' : 10,
                 'gaussNoise' : 0.01 }

interactive = 0

def test_main():
    if '-i' in sys.argv:
        global interactive
        interactive = 1
        sys.argv.remove('-i')
    setup_logging()
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
