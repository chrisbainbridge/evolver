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

def plotGenerationVsFitness(g, filename):
    view = 0
    if filename == '-':
        view = 1
        filename = 'tmp.pdf'
    (fbase, ext) = os.path.splitext(filename)
    ext = ext[1:]
    datname = fbase + '.dat'
    fdat = open(datname, 'w')
    gen = 0
    for (mn, mean, mx) in g.fitnessList:
        fdat.write('%d %f %f %f\n'%(gen, mn, mean, mx))
        gen += 1
    fdat.close()
    f = open(fbase + '.gnuplot', 'w')
    s = """#!/usr/bin/gnuplot
    set style data line
    set terminal pdf
    set output "%s"
    set xlabel "Generation"
    set ylabel "Fitness"
    set multiplot
    plot "%s" using 1:2 title "min", "%s" using 1:3 title "mean", "%s" using 1:4 title "max"
    """%(fbase+'.pdf', datname, datname, datname)
    f.write(s)
    f.close()
    if ext != 'gnuplot':
        assert ext == 'pdf'
        os.system('gnuplot %s'%(fbase + '.gnuplot'))
        os.remove(fbase + '.gnuplot')
        if view:
            os.system('kpdf tmp.pdf')

def dot(filename, s):
    "Write string s to a file and run dot"
    view = 0
    assert filename
    if filename == '-':
        view = 1
        filename = 'tmp.pdf'
    (fbase, ext) = os.path.splitext(filename)
    ext = ext[1:]
    f = open(fbase+'.dot', 'w')
    f.write(s)
    f.close()
    if ext != 'dot':
        if ext == 'pdf':
            os.system('dot -Tps -o%s.eps %s.dot'%(fbase, fbase))
            os.system('epstopdf %s.eps'%fbase)
            os.remove(fbase+'.eps')
            if view:
                os.system('kpdf %s.pdf'%fbase)
        else:
            os.system('dot -T%s -o%s.%s %s.dot'%(ext, fbase, ext, fbase))
            os.remove(fbase+'.dot')

def plotNetworks(bg, filename, toponly):
    "Plot a graph with the interconnected networks of each bodypart"
    log.debug('plotNetworks(%s,%s)', filename, toponly)
    bg.sanityCheck()

    s = 'digraph G {\n compound=true\n'
    for i in range(len(bg.bodyparts)):
        s += ' subgraph cluster%d {\n'%i
        s += '  label = "bp%d"\n'%i
        bp = bg.bodyparts[i]
        prefix = 'bp%d_'%i
        s += bp.network.plotNodes(toponly, prefix)
        s += bp.network.plotEdges(toponly, prefix)
        if bp.joint == 'hinge':
            motors = ['MOTOR_2']
        elif bp.joint == 'universal':
            motors = ['MOTOR_0', 'MOTOR_1']
        elif bp.joint == 'ball':
            motors = ['MOTOR_0', 'MOTOR_1', 'MOTOR_2']
        signals = ['CONTACT', 'JOINT_0', 'JOINT_1', 'JOINT_2']

        for signal in signals + motors:
            if toponly:
                s += '  %s%s [shape=point]\n'%(prefix, signal)
            else:
                style = ''
                s += '  %s%s [label="%s"%s]\n'%(prefix, signal, signal, style)
        s += ' }\n'

    # plot inter-bodypart (node.external_input) edges here
    for bp in bg.bodyparts:
        sources = bg.getInputs(bp)
        for (tsignal, (sbp, signal)) in sources:
            sbp_i = bg.bodyparts.index(sbp)
            tbp_i = bg.bodyparts.index(bp)
            if isinstance(tsignal, node.Node):
                tn_i = bp.network.index(tsignal)
                ts = '%d'%tn_i
            else:
                ts = str(tsignal)
            if type(signal) is str:
                s += ' bp%d_%s -> bp%d_%s\n'%(sbp_i, signal, tbp_i, ts)
            else: # node
                s += ' bp%d_%d -> bp%d_%s\n'%(sbp_i, sbp.network.index(signal), tbp_i, ts)

    # plot bpg topology
    for i in range(len(bg.bodyparts)):
        targets = [ e.child for e in bg.bodyparts[i].edges ]
        for t in targets:
            ti = bg.bodyparts.index(t)
            s += ' bp%d_0 -> bp%d_0 [ltail=cluster%d, lhead=cluster%d, color=red]\n'%(i, ti, i, ti)

    s += '}\n'

    dot(filename, s)
    return s

def plotBpg(bg, filename=None, toponly=0):
    "Dump this BodyPartGraph to a graphviz dot string/file"
    log.debug('BodyPartGraph.plot')
    bg.sanityCheck()

    s = 'digraph G {\n'
    # first dump all of the nodes with labels
    for i in range(len(bg.bodyparts)):
        bp = bg.bodyparts[i]
        label = 'bp%d'%(i)
        if not toponly:
            label += ' (scale=%.2f,' % (bp.scale)
            label += 'rec_lim=%d,' % (bp.recursive_limit)
            label += 'joint=%s,' % (bp.joint)
            label += 'net.inputs=%d)' % (len(bp.network.inputs))
        s += ' '*4 + 'n%d [label="%s"]\n' % (i,label)
    s += '\n'
    # now dump all of the edges with labels
    for i in range(len(bg.bodyparts)):
        bp = bg.bodyparts[i]
        # plot all edges to children
        for edge in bp.edges:
            child_index = bg.bodyparts.index(edge.child)
            label = ''
            if not toponly:
                label += 'joint_end=%d,terminal_only=%d' % (edge.joint_end, edge.terminal_only)
            s += ' '*4 + 'n%d -> n%d [label="%s"]\n' % (i, child_index, label)
        # plot all incoming sensory edges
        sources = bg.getInputs(bp)
        for (tsignal, (sbp, ssignal)) in sources:
            if toponly:
                label = ''
            else:
                if isinstance(ssignal, str):
                    slabel = ssignal
                else:
                    slabel = 'bp%d-%d'%(bg.bodyparts.index(sbp), sbp.network.index(ssignal))
                if isinstance(tsignal, str):
                    tlabel = tsignal
                else:
                    tlabel = 'bp%d-%d'%(i, bp.network.index(tsignal))
                label = '%s -> %s'%(slabel, tlabel)
            # edge between 2 bps labelled with signal source
            s += ' '*4 + 'n%d -> n%d [style=dashed, label="%s"]\n' % (bg.bodyparts.index(sbp), i, label)
    s += '}\n'

    dot(filename, s)
    # return graph as a string
    return s
