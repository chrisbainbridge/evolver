#!/usr/bin/python

import os, sys
import logging

log = logging.getLogger('plot')

def plotSignals(tracefile):
    log.debug('plotting tracefile %s', tracefile)
    f = open(tracefile, 'r')
    labelCommentLine = f.readline()
    f.close()
    labels = labelCommentLine.split()[1:]
    num_plots = len(labels)-1
    log.debug('%d signals to plot', num_plots)
    PLOTS_PER_PAGE = 20
    y_size = 1.0/PLOTS_PER_PAGE
    (basename, ext) = os.path.splitext(tracefile)
    log.debug('basename = %s', basename)
    header = """#!/usr/bin/gnuplot
    set terminal postscript portrait
    set out "%%s"
    set multiplot
    set yrange [0:1]
    set size 1,%f
    set bmargin 0.05
    set tmargin 0.05
    set border 2
    set key top outside
    set ytics nomirror 0, 1, 1
    set noxtics
    set style line 1 linetype 1 linewidth 1
    """%(y_size-0.015)

    page = 0
    fnames = []
    for x in range(1, num_plots+1, PLOTS_PER_PAGE):
        log.debug('plotting rows %d-%d', x, min(num_plots, x+PLOTS_PER_PAGE))
        fname = '%s-p%d.gnuplot'%(basename, page)
        fo = open(fname, 'w')
        log.debug('creating gnuplot script %s', fname)
        epsFile = "%s-p%d.eps"%(basename, page)
        fnames.append(epsFile)
        s = header%(epsFile)
        for i in range(x, x+min(PLOTS_PER_PAGE, num_plots-x+1)):
            log.debug('plotting row %d', i)
            s += """
            set origin 0.05, %f
            set label "%s" at graph -0.145, graph 0.5
            plot "%s" using 1:%d notitle with lines linestyle 1
            unset label
            """%(y_size*(i-x)+0.015/2, labels[i], tracefile, i+1)
        fo.write(s)
        fo.close()
        os.chmod(fname, 0755)
        os.system('gnuplot %s'%fname)
        log.debug('generated %s-p%d.eps', basename, page)
        page += 1
    log.info('generated %s', fnames)
    return fnames

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print '%s infile.trace'%sys.argv[0]
        sys.exit(1)
    files = plotSignals(sys.argv[1])
