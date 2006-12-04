EV_SRC = bpg.py ev.py evolve.py network.py node.py sim.py daemon.py 
VIS_SRC = glwidget.py qtgui.py qtapp.py qtgui.py
SRC = $(EV_SRC) $(VIS_SRC)
TEST = bpg_test.py evolve_test.py network_test.py sim_test.py ev_test.py plot_test.py cluster_test.py

.PHONY: clean test checker pop run popd

qtgui.py: qtgui.ui
	pyuic -p0 qtgui.ui -o qtgui.py

test: $(SRC) $(TEST)
	-for t in $(TEST); do echo $$t; $$t -v; done

checker:
	pychecker *.py

%.ps: %.dot
	@dot -Tps -o$@ $<

popd:
	rm -f evo.stats
	ev.py -r x -e

pop:
	ev.py -r x -p 5 -t 30 -g 100 --topology full --update sync --nodetype sigmoid --nodes 20 --sim bpg --fitness mean-distance --steadystate

run:
	ev.py -r x -u
	rm -f pymemprof.log evo.stats
	ev.py -r x -c -m --statlog evo.stats

viewstats:
	kghostview stats.eps

clean:
	rm -f *.pyc 
	rm -f qtgui.py 
	rm -rf types/* test/* *~
	rm -f divx2pass.log
	rm -rf doc

memprof:
	rm -rf types/*
	memprof.py
	plot-all.py
	gwenview types/*.png

uml:
	happydoc --dia $(EV_SRC)
	dia doc/dia.dia
