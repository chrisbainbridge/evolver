#!/usr/bin/python

import os, sys

def main():

    if len(sys.argv) != 2:
        print '%s infile.trace'%sys.argv[0]
        sys.exit(1)

    print 'reading %s'%sys.argv[1]
    f = open(sys.argv[1], 'r')
    s = f.readline()
    labels = s.split()[1:]
    hs = """
#set style data line
# eps
    set terminal postscript portrait noenhanced  solid defaultplex

#set out '%s.eps'
    """%(sys.argv[1])
#s += 'set multiplot\n'
    num_plots = len(labels)-1
#num_plots = 8
    print '%d plots'%num_plots
#y_size = 1.0/(num_plots)
#y_size = 1.0/30
    PLOTS_PER_PAGE = 20
    y_size = 1.0/PLOTS_PER_PAGE
    s += 'set yrange [0:1]\n'
#s += 'set yrange [-0.1:1.1]\n'
    s += 'set size 1,%f\n'%(y_size-0.015)
    s += 'set bmargin 0.05\n'
    s += 'set tmargin 0.05\n'
    s += 'set format x ""\n'
    s += 'set xlabel ""\n'
    s += 'set border 2\n'
    s += 'set key top outside\n'
    s += 'set noytics\n'
    s += 'set ytics nomirror 0, 1, 1\n'
    s += 'set noxtics\n'
    s += 'set style line 1 linetype 1 linewidth 3\n'
    header = s
    page = 0
    for x in range(1, num_plots+1, PLOTS_PER_PAGE):
        print 'x=%d'%x
        basename = sys.argv[1][:sys.argv[1].rfind('.')]
        print basename
        fname = '%s-p%d.gpi'%(basename, page)
        fo = open(fname, 'w')
        print 'writing %s'%fname
        s = hs + 'set out "%s-p%d.eps"\nset multiplot\n'%(basename, page) + header
        #s += 'set multiplot\n'

        for i in range(x, x+min(PLOTS_PER_PAGE, num_plots-x+1)):
            print 'i=%d'%i
            s += 'set origin 0.05,%f\n'%(y_size*(i-x)+0.015/2) #+0.015) #*(i-2))
            s += 'set label "%s" at graph -0.145, graph 0.5\n'%(labels[i])
            #s += 'plot "%s" using 1:%d with lines title "%s"\n'%(sys.argv[1], i, labels[i-1])
            s += 'plot "%s" using 1:%d notitle with lines linestyle 1\n'%(sys.argv[1], i+1)
            s += 'unset label\n'
        fo.write(s)
        fo.close()
        os.system('gnuplot %s'%fname)
        print 'generated %s-p%d.eps'%(basename,page)
        page += 1

if __name__ == '__main__':
    main()
