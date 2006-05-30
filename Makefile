export COVERAGE_FILE=test/coverage

SRC = glwidget.py bpg.py daemon.py ev.py evolve.py qtgui.py network.py node.py qtapp.py sim.py trace.py qtgui.py
TEST = bpg_test.py evolve_test.py network_test.py sim_test.py ev_test.py

.PHONY: clean test checker pop run popd

qtgui.py: qtgui.ui
	pyuic -p0 qtgui.ui -o qtgui.py

test: $(SRC) $(TEST)
	coverage.py -e
	-for t in $(TEST); do coverage.py -x $$t -v --color-mode; done
	coverage.py -r $(SRC)

tags:
	exuberant-ctags -e -R

checker:
	pychecker *.py

%.ps: %.dot
	@dot -Tps -o$@ $<

%.ps: %.py
	enscript -E -C -2r -T4 --highlight-bar-gray=0.87 --mark-wrapped-lines=arrow -fCourier6.6 -o $@ $<

popd:
	rm -f evo.stats
	ev.py -r x -e

pop:
	ev.py -r x -p 20 -t 20 -g 20 --topology full --update async --node_type sigmoid --nodes 10 --sim bpg

run:
	ev.py -r x -u
	rm -f pymemprof.log evo.stats
	ev.py -r x -c -m --statlog evo.stats

viewstats:
	kghostview stats.eps

clean:
	rm -rf types/* test/* *.pyc qtgui.py *~

memprof:
	rm -rf types/*
	memprof.py
	plot-all.py
	gwenview types/*.png

uml:
	autodia.pl -l python -i "bpg.py evolve.py network.py sim.py"
	dia autodia.out.xml
	# happydoc can also generate uml ... may be better
