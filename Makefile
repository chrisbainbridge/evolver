EV_SRC = bpg.py ev.py evolve.py network.py node.py sim.py daemon.py 
VIS_SRC = glwidget.py qtapp.py
SRC = $(EV_SRC) $(VIS_SRC)
TEST = bpg_test.py evolve_test.py node_test.py network_test.py sim_test.py ev_test.py plot_test.py cluster_test.py

.PHONY: clean test checker pop run popd

test: $(SRC) $(TEST)
	rm -f test/*
	-for t in $(TEST); do echo $$t; $$t --color-mode=always -v; done 2>&1 | tee test.txt

checker:
	pychecker *.py

%.ps: %.dot
	@dot -Tps -o$@ $<

popd:
	ev.py -r x -e

pop:
	ev.py -r x -p 5 -t 30 -g 100 --top full --timing sync --model sigmoid --neurons 10 --sim bpg --fitness meandistance --steadystate

pbpop:
	ev.py -r p -p 5 -t 30 -g 200 --top full --timing sync --model sigmoid --neurons 5 --sim pb --steadystate --mutate 0.05

popz:
	ev.py -r z -p 10 -t 30 -g 100 --top full --timing sync --model beer --neurons 5 --sim bpg --fitness movement --steadystate

run:
	ev.py -r x -u
	rm -f pymemprof.log
	ev.py -r x -c -m

clean:
	rm -f *.pyc r.out tmp.r divx2pass.log
	rm -rf types/* test/* *~ test.txt doc

memprof:
	rm -rf types/*
	memprof.py
	plot-all.py
	gwenview types/*.png

uml:
	happydoc --dia $(EV_SRC)
	dia doc/dia.dia

ulimit:
	ulimit -s 65536
