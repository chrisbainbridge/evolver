Introduction
============

This is the source code for the genetic algorithm evolutionary robotics system
used for the experiments in the PhD thesis ["Digital control networks for
virtual creatures"](https://www.era.lib.ed.ac.uk/handle/1842/4812). It can be
run on a single Linux PC or a cluster (either local processing of a complete
experimental run, or distributed processing of a run via a shared ZEO server).

Install
=======

Run time dependencies:

```
$ apt-get install cython python-pyode python-qt4 python-zodb
$ pip install cgkit1
```

Testing and graph plotting dependencies (not required for basic usage, but
useful for development and analysis of experiment results):

```
$ apt-get install graphviz gnuplot python-cheetah texlive-font-utils
$ pip install testoob
```

These dependencies are for Debian Jessie. Other distributions may differ.

Quick start
===========

```
# Create an evolutionary run (population size 20, 10 generations)
$ ev -f test.db -p 30 -g 30 --model sigmoid --fitness walk

# Run evolution
$ ev -f test.db -m -c

# List results
$ ev -f test.db -l
Num	Score	P.score	Mutations
0	2025.15	 2011.31	0
1	1934.47	 1937.14	0
|...
29	-1.00	 1937.14	5
Generation: name=test.db ga=elite gen=9/9 fitness=walk evh=864

# Run simulation of result 0
$ ev -f test.db -i 0 -s
INFO:ev:Random seed: ec84baf8
INFO:ev:Running simulation
INFO:ev:Final score was 2015.727087

# Run 3D OpenGL visual simulator with result 0
$ ev -f test.db -i 0 -v
```

Commands and options
====================

The `ev` command is the front end for creating GA runs, running the
simulations, creating graphs and videos, varying parameters of GA and neural
network aetc.

Run `ev` without any parameters to show all supported options.

Examples
========

Biped walker:

![biped walker](http://i.imgur.com/F9hz25G.jpg)

Cube walker:

![cube walker](http://i.imgur.com/uISdsLn.jpg)
