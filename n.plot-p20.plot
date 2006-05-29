
#set style data line
# eps
set terminal postscript portrait noenhanced  solid defaultplex

#set out 'n.trace.eps'
set multiplot
set yrange [0:1]
set size 1,0.010000
set bmargin 0.05
set tmargin 0.05
set format x ""
set xlabel ""
set border 2
set key top outside
set noytics
set ytics nomirror 0, 1, 1
set noxtics
set style line 1 linetype 1 linewidth 3
set out "n.plot-p20.eps"
set origin 0.05,0.007500
set label "bp2-0" at graph -0.145, graph 0.5
plot "n.trace" using 1:22 notitle with lines linestyle 1
unset label
set origin 0.05,0.032500
set label "bp2-1" at graph -0.145, graph 0.5
plot "n.trace" using 1:23 notitle with lines linestyle 1
unset label
set origin 0.05,0.057500
set label "bp2-2" at graph -0.145, graph 0.5
plot "n.trace" using 1:24 notitle with lines linestyle 1
unset label
set origin 0.05,0.082500
set label "bp2-3" at graph -0.145, graph 0.5
plot "n.trace" using 1:25 notitle with lines linestyle 1
unset label
set origin 0.05,0.107500
set label "bp2-4" at graph -0.145, graph 0.5
plot "n.trace" using 1:26 notitle with lines linestyle 1
unset label
set origin 0.05,0.132500
set label "bp2-5" at graph -0.145, graph 0.5
plot "n.trace" using 1:27 notitle with lines linestyle 1
unset label
set origin 0.05,0.157500
set label "bp2-6" at graph -0.145, graph 0.5
plot "n.trace" using 1:28 notitle with lines linestyle 1
unset label
set origin 0.05,0.182500
set label "bp2-7" at graph -0.145, graph 0.5
plot "n.trace" using 1:29 notitle with lines linestyle 1
unset label
set origin 0.05,0.207500
set label "bp2-8" at graph -0.145, graph 0.5
plot "n.trace" using 1:30 notitle with lines linestyle 1
unset label
set origin 0.05,0.232500
set label "bp2-9" at graph -0.145, graph 0.5
plot "n.trace" using 1:31 notitle with lines linestyle 1
unset label
set origin 0.05,0.257500
set label "bp3-0" at graph -0.145, graph 0.5
plot "n.trace" using 1:32 notitle with lines linestyle 1
unset label
set origin 0.05,0.282500
set label "bp3-1" at graph -0.145, graph 0.5
plot "n.trace" using 1:33 notitle with lines linestyle 1
unset label
set origin 0.05,0.307500
set label "bp3-2" at graph -0.145, graph 0.5
plot "n.trace" using 1:34 notitle with lines linestyle 1
unset label
set origin 0.05,0.332500
set label "bp3-3" at graph -0.145, graph 0.5
plot "n.trace" using 1:35 notitle with lines linestyle 1
unset label
set origin 0.05,0.357500
set label "bp3-4" at graph -0.145, graph 0.5
plot "n.trace" using 1:36 notitle with lines linestyle 1
unset label
set origin 0.05,0.382500
set label "bp3-5" at graph -0.145, graph 0.5
plot "n.trace" using 1:37 notitle with lines linestyle 1
unset label
set origin 0.05,0.407500
set label "bp3-6" at graph -0.145, graph 0.5
plot "n.trace" using 1:38 notitle with lines linestyle 1
unset label
set origin 0.05,0.432500
set label "bp3-7" at graph -0.145, graph 0.5
plot "n.trace" using 1:39 notitle with lines linestyle 1
unset label
set origin 0.05,0.457500
set label "bp3-8" at graph -0.145, graph 0.5
plot "n.trace" using 1:40 notitle with lines linestyle 1
unset label
set origin 0.05,0.482500
set label "bp3-9" at graph -0.145, graph 0.5
plot "n.trace" using 1:41 notitle with lines linestyle 1
unset label
