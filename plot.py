#!/usr/bin/python

import os
import logging
import node
from numpy import matrix, multiply, sqrt

log = logging.getLogger('plot')

def stripTraceFile(tracefile):
    'Remove flat signals from the tracefile'

    fi = open(tracefile, 'r')
    labelCommentLine = fi.readline()
    labels = (labelCommentLine[2:]).split()
    log.debug('labels = %s', labels)
    cols = len(labels)
    total = matrix([0.0]*cols)

    rows = 0
    # allow some short time for signals to settle
    for _ in range(10):
        fi.readline()
        rows += 1

    while 1:
        s = fi.readline()
        if s == '':
            break
        vals = s.split()
        assert len(vals) == cols
        l = [float(x) for x in vals]
        m = matrix(l)
        total += m
        rows += 1

    mean = total/rows
    vms = mean.tolist()[0][1:]
    log.debug('means = %s', vms)

    fi.seek(0)
    fi.readline()
    sigma = matrix([0.0]*cols)
    while 1:
        s = fi.readline()
        if s == '':
            break
        vals = matrix([float(x) for x in s.split()])
        t = vals-mean
        sigma += multiply(t, t)
    s = sqrt(sigma / (rows-1))
    log.debug('standard deviation = %s',s)

    l = s.tolist()[0]
    b = [x > 0.025 for x in l]
    log.info('stripping flat signals %s', [x for x in labels if not b[labels.index(x)]])
    log.info('leaving %s', [x for x in labels if b[labels.index(x)]])

    fi.seek(0)
    fo = open('strip.trace', 'w')
    fi.read(2)
    fo.write('# ')
    while 1:
        s = fi.readline()
        if s == '':
            break
        vals = s.split()
        t = ''
        for x in range(len(b)):
            if b[x]:
                t += '%s '%vals[x]
        fo.write(t+'\n')

    fi.close()
    fo.close()
    os.rename(tracefile, tracefile+'.bak')
    os.rename('strip.trace', tracefile)

def plotSignals(tracefile, quanta=0, ext='.pdf'):
    log.debug('plotting tracefile %s', tracefile)

    f = open(tracefile, 'r')
    labelCommentLine = f.readline()
    f.close()
    labels = labelCommentLine.split()[1:]
    num_plots = len(labels)-1
    log.debug('%d signals to plot', num_plots)
    PLOTS_PER_PAGE = 10
    (basename, _) = os.path.splitext(tracefile)
    log.debug('basename = %s', basename)
    font = 'Helvetica'
    font_size = 8
    if ext == '.pdf':
        term = 'pdf font "%s,%d"'%(font, font_size)
    elif ext == '.eps':
        term = 'postscript portrait "%s" %d'%(font, font_size)
    header = """#!/usr/bin/gnuplot
    set terminal %s
    set out "%%s"
    set multiplot layout %%d,1
    set border 3
    set key top outside
    set style line 1 linetype 1 linewidth 1
    set lmargin 10
    set xtics nomirror
    """%(term)

    page = 0
    fnames = []
    for x in range(1, num_plots+1, PLOTS_PER_PAGE):
        log.debug('plotting rows %d-%d', x, min(num_plots, x+PLOTS_PER_PAGE))
        fname = '%s-p%d.gnuplot'%(basename, page)
        fo = open(fname, 'w')
        log.debug('creating gnuplot script %s', fname)
        epsFile = "%s-p%d%s"%(basename, page, ext)
        fnames.append(epsFile)
        s = header%(epsFile, min(PLOTS_PER_PAGE, num_plots+1-x))
        for i in range(x, x+min(PLOTS_PER_PAGE, num_plots-x+1)):
            log.debug('plotting row %d', i)
            yrange = '[-0.25:1]'
            ytics = '0,1,1'
            if 'M' in labels[i]:
                yrange = '[-5:3.14]'
                ytics = '-3.1,6.2,3.1'
            if 'angle' == labels[i]:
                yrange = '[-1.8:1.8]'
                ytics = '-1.8,1.8,1.8'
            if 'ctrlf' == labels[i]:
                yrange = '[-1000:1000]'
                ytics = '-1000,1000,1000'
            if 'randf' == labels[i]:
                yrange = '[-200:200]'
                ytics = '-200,200,200'
            style = 'lines'
            if quanta:
                style = 'steps'
            s += """
            set yrange %s
            set ytics nomirror %s
            set label "%s" at graph -0.10, graph 0.5
            plot "%s" using 1:%d notitle with %s linestyle 1
            unset label
            """%(yrange, ytics, labels[i].lower(), tracefile, i+1, style)
        fo.write(s)
        fo.close()
        os.chmod(fname, 0755)
        os.system('gnuplot %s >> gnuplot.out 2>&1'%fname)
        log.debug('generated %s-p%d.eps', basename, page)
        page += 1
    log.info('generated %s', fnames)
    return fnames

def gnuplotSetup(filename, genName):
    view = 0
    if filename == '-':
        view = 1
        assert genName
        filename = 'tmp-%s.pdf'%genName
    (fbase, ext) = os.path.splitext(filename)
    gnuplotFile = fbase + '.gnuplot'
    datFile = fbase + '.dat'
    return (view, fbase, ext, gnuplotFile, datFile)

def gnuplot(gnuplotFile, ext, view, datFile, fbase):
    if ext != '.gnuplot':
        assert ext == '.pdf'
        os.system('gnuplot %s >> gnuplot.out 2>&1'%(gnuplotFile))
        os.remove(gnuplotFile)
        os.remove(datFile)
        if view:
            os.system('kpdf %s.pdf'%fbase)
            os.remove('%s.pdf'%fbase)

def plot_generation_vs_fitness(g, outputFilename, genName=None):
    (view, fbase, ext, gnuplotFile, datFile) = gnuplotSetup(outputFilename, genName)

    fdat = open(datFile, 'w')
    gen = 0
    for s in g.scores:
        fdat.write('%d %f %f %f\n'%(gen, s.min, s.mean, s.max))
        gen += 1
    fdat.close()

    f = open(gnuplotFile, 'w')
    s = """#!/usr/bin/gnuplot
    set style data line
    set terminal pdf
    set output "%s.pdf"
    set xlabel "Generation"
    set ylabel "Fitness"
    set multiplot
    plot "%s" using 1:2 title "min", "%s" using 1:3 title "mean", "%s" using 1:4 title "max"
    """%(fbase, datFile, datFile, datFile)
    f.write(s)
    f.close()

    gnuplot(gnuplotFile, ext, view, datFile, fbase)

def plot_mutation_vs_prob_improvement(g, outputFilename, genName=None):
    (view, fbase, ext, gnuplotFile, datFile) = gnuplotSetup(outputFilename, genName)

    improved = {}
    total = {}
    for (parentFitness, mutations, childFitness) in g.mutationStats:
        improved[mutations] = 0
        total[mutations] = 0
    for (parentFitness, mutations, childFitness) in g.mutationStats:
        if childFitness > parentFitness:
            improved[mutations] += 1
        total[mutations] += 1

    fdat = open(datFile, 'w')
    for m in total:
        pi = float(improved[m]) / total[m]
        fdat.write('%d %f\n'%(m, pi))
    fdat.close()

    f = open(gnuplotFile, 'w')
    s = """#!/usr/bin/gnuplot
    set style data line
    set terminal pdf
    set output "%s.pdf"
    set xlabel "Number of mutations"
    set ylabel "Probability of improvement"
    set multiplot
    set xtics 1
    set xrange [1:]
    plot "%s" using 1:2:(0.5) notitle with boxes fs solid 0.5
    """%(fbase, datFile)
    f.write(s)
    f.close()

    gnuplot(gnuplotFile, ext, view, datFile, fbase)

def plot_mutation_vs_fitness_change(g, outputFilename, genName=None):
    (view, fbase, ext, gnuplotFile, datFile) = gnuplotSetup(outputFilename, genName)

    fdat = open(datFile, 'w')
    mn = 0
    mx = 0
    for (parentFitness, mutations, childFitness) in g.mutationStats:
        fitnessChange = childFitness - parentFitness
        fdat.write('%d %f\n'%(mutations, fitnessChange))
        mn = min(mn, fitnessChange)
        mx = max(mx, fitnessChange)
    fdat.close()

    f = open(gnuplotFile, 'w')
    s = """#!/usr/bin/gnuplot
    set style data points
    set terminal pdf
    set output "%s.pdf"
    set xlabel "Number of mutations"
    set ylabel "Change in fitness"
    set xtics 1
    set xrange [1:]
    set yrange [%f:%f]
    set multiplot
    plot "%s" using 1:2 notitle with points pt 2
    """%(fbase, mn, mx, datFile)
    f.write(s)
    f.close()

    gnuplot(gnuplotFile, ext, view, datFile, fbase)

def dot(filename, s):
    "Write string s to a file and run dot"
    view = 0
    assert filename
    if filename == '-':
        view = 1
        filename = 'tmp.pdf'
    (fbase, ext) = os.path.splitext(filename)
    f = open(fbase+'.dot', 'w')
    f.write(s)
    f.close()
    if ext != '.dot':
        if ext == '.pdf':
            os.system('dot -Tps -o%s.eps %s.dot >> dot.out 2>&1'%(fbase, fbase))
            os.system('epstopdf %s.eps'%fbase)
            os.remove(fbase+'.eps')
            if view:
                os.system('kpdf %s.pdf'%fbase)
        else:
            cmd = 'dot -T%s -o%s%s %s.dot >> dot.out 2>&1'%(ext[1:], fbase, ext, fbase)
            os.system(cmd)
            os.remove(fbase+'.dot')

def plotNetworks(bg, filename, toponly):
    "Plot a graph with the interconnected networks of each bodypart"
    log.debug('plotNetworks(%s,%s)', filename, toponly)
    bg.sanityCheck()

    s = 'digraph G {\n compound=true\n'
    for i in range(len(bg.bodyparts)):
        s += ' subgraph cluster%d {\n'%i
        bp = bg.bodyparts[i]
        nodet = bp.network.getNodeName(0)
        if bp.isRoot:
            j = 'root'
            if not bg.unrolled:
                j += ', ' + bp.joint
        else:
            j = bp.joint
        s += '  label = "bp%d (%s, %s)"\n'%(i, j, nodet)
        prefix = 'bp%d_'%i
        s += plotNodes(bp.network, toponly, prefix)
        s += plotEdges(bp.network, toponly, prefix)
        signals = ['CONTACT', 'JOINT_0', 'JOINT_1', 'JOINT_2']

        for signal in signals + bp.getMotors(bg):
            if toponly:
                s += '  %s%s [shape=point]\n'%(prefix, signal)
            else:
                l = signal[0]
                if '0' <= signal[-1] <= '9':
                    l += signal[-1]
                s += '  %s%s [label="%s"]\n'%(prefix, signal, l)
        s += ' }\n'

    # plot inter-bodypart (node.external_input) edges here
    for bp in bg.bodyparts:
        sources = bg.getInputs(bp)
        # the root node has motor_input values set, but they aren't used, so
        # filter them out
        if bg.unrolled and bp.isRoot:
            sources = [(target,src) for (target,src) in sources if not isinstance(target,str) or target[0]!='M']
        for (tsignal, (sbp, signal, w)) in sources:
            sbp_i = bg.bodyparts.index(sbp)
            tbp_i = bg.bodyparts.index(bp)
            if isinstance(tsignal, node.Node):
                tn_i = bp.network.index(tsignal)
                ts = '%d'%tn_i
            else:
                ts = str(tsignal)
            if type(signal) is str:
                s += ' bp%d_%s -> bp%d_%s'%(sbp_i, signal, tbp_i, ts)
            else: # node
                s += ' bp%d_%d -> bp%d_%s'%(sbp_i, sbp.network.index(signal), tbp_i, ts)
            color = weightToColor(w)
            s += '[%s]\n'%color

    # plot bpg topology
    for i in range(len(bg.bodyparts)):
        targets = [ e.child for e in bg.bodyparts[i].edges ]
        for t in targets:
            ti = bg.bodyparts.index(t)
            s += ' bp%d_0 -> bp%d_0 [ltail=cluster%d, lhead=cluster%d, style=dashed]\n'%(i, ti, i, ti)

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
        for (tsignal, (sbp, ssignal, w)) in sources:
            if toponly:
                label = ''
            else:
                if isinstance(ssignal, str):
                    slabel = ssignal
                else:
                    if not ssignal in sbp.network:
                        # not everything in input_map is valid, so skip it
                        continue
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

def plotNodes(net, toponly=0, prefix='n'):
    s = ''
    # write out all nodes
    for i in range(len(net)):
        if toponly:
            s += '  %s%d [shape=point]\n'%(prefix, i)
        else:
            label = '%d'%i
            if net[i] in net.inputs:
                label += 'i'
            if net[i] in net.outputs:
                label += 'o'
            s += '  %s%d [label="%s"]\n'%(prefix, i, label)
    return s

def weightToColor(x):
    if x is None: return 'color=#000000' # unweighted connections e.g. logical
    x = x/7
    if x<0:
        r = abs(x)
        g = 0
    else:
        r = 0
        g = x
    def tohex(x): return hex(int(round(abs(x)*255)))[2:].zfill(2)
    return 'color="#%s%s00"'%(tohex(r), tohex(g))

def plotEdges(net, toponly=0, prefix='n'):
    s = ''
    done = {}
    # write out all edges
    for target_index in range(len(net)):
        n = net[target_index]
        for i in n.inputs:
            if i not in net:
                # fixme: why aren't we plotting anything here?!
                continue
            src_index = net.index(i)
            if not toponly or not done.has_key((target_index,src_index)):
                edge_label = ''
                if not toponly and hasattr(net[target_index],'weights'):
                    try:
                        w = net[target_index].weights[net[src_index]]
                        sl = str(w)
                        sl = sl[:sl.find('.')+2]
                        edge_label = sl
                    except KeyError:
                        pass
                if edge_label:
#                    s += '  %s%d -> %s%d [label="%s"]\n'%(prefix, src_index, prefix, target_index, edge_label)
                    x = float(edge_label)
                    color = weightToColor(x)
                    s += '  %s%d -> %s%d [%s]\n'%(prefix, src_index, prefix, target_index, color)
                elif toponly:
                    s += '  %s%d -> %s%d [dir=none]\n'%(prefix, src_index, prefix, target_index) # or dir=both
                else:
                    s += '  %s%d -> %s%d\n'%(prefix, src_index, prefix, target_index)
                done[(src_index, target_index)] = 1
    return s

def plotNetwork(net, filename=None, toponly=0):
    """Dump this network as a (graphviz) dot file."""
    log.debug('dumping network to %s in dot graph format', filename)
    s = """digraph G {
        %s
        %s
    }
    """%(plotNodes(net, toponly), plotEdges(net, toponly))
    dot(filename, s)
    return s
