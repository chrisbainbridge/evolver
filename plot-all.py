#!/usr/bin/env python

import Gnuplot
import os

def main():
    os.chdir("types")
    types = [t for t in os.listdir(".") if not t.startswith(".")]

    g = Gnuplot.Gnuplot()
    for t in types:
        g('set terminal png')
        g('set output "%s.png"' % t)
        g('plot "%s"' % t)

if __name__=='__main__':
    main()
