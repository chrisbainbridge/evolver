
#set style data line
# eps
set terminal postscript portrait noenhanced  solid defaultplex

#set out 'n.trace.eps'
set out "n-p20.eps"
set multiplot
# time bp0-0 bp0-1 bp0-2 bp0-3 bp0-4 bp0-5 bp0-6 bp0-7 bp0-8 bp0-9 bp1-0 bp1-1 bp1-2 bp1-3 bp1-4 bp1-5 bp1-6 bp1-7 bp1-8 bp1-9 bp2-0 bp2-1 bp2-2 bp2-3 bp2-4 bp2-5 bp2-6 bp2-7 bp2-8 bp2-9 bp3-0 bp3-1 bp3-2 bp3-3 bp3-4 bp3-5 bp3-6 bp3-7 bp3-8 bp3-9 
set yrange [0:1]
set size 1,0.035000
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
set origin 0.05,0.007500
set label "bp2-0" at graph -0.145, graph 0.5
plot "n.trace" using 1:22 notitle with lines linestyle 1
unset label
set origin 0.05,0.057500
set label "bp2-1" at graph -0.145, graph 0.5
plot "n.trace" using 1:23 notitle with lines linestyle 1
unset label
set origin 0.05,0.107500
set label "bp2-2" at graph -0.145, graph 0.5
plot "n.trace" using 1:24 notitle with lines linestyle 1
unset label
set origin 0.05,0.157500
set label "bp2-3" at graph -0.145, graph 0.5
plot "n.trace" using 1:25 notitle with lines linestyle 1
unset label
set origin 0.05,0.207500
set label "bp2-4" at graph -0.145, graph 0.5
plot "n.trace" using 1:26 notitle with lines linestyle 1
unset label
set origin 0.05,0.257500
set label "bp2-5" at graph -0.145, graph 0.5
plot "n.trace" using 1:27 notitle with lines linestyle 1
unset label
set origin 0.05,0.307500
set label "bp2-6" at graph -0.145, graph 0.5
plot "n.trace" using 1:28 notitle with lines linestyle 1
unset label
set origin 0.05,0.357500
set label "bp2-7" at graph -0.145, graph 0.5
plot "n.trace" using 1:29 notitle with lines linestyle 1
unset label
set origin 0.05,0.407500
set label "bp2-8" at graph -0.145, graph 0.5
plot "n.trace" using 1:30 notitle with lines linestyle 1
unset label
set origin 0.05,0.457500
set label "bp2-9" at graph -0.145, graph 0.5
plot "n.trace" using 1:31 notitle with lines linestyle 1
unset label
set origin 0.05,0.507500
set label "bp3-0" at graph -0.145, graph 0.5
plot "n.trace" using 1:32 notitle with lines linestyle 1
unset label
set origin 0.05,0.557500
set label "bp3-1" at graph -0.145, graph 0.5
plot "n.trace" using 1:33 notitle with lines linestyle 1
unset label
set origin 0.05,0.607500
set label "bp3-2" at graph -0.145, graph 0.5
plot "n.trace" using 1:34 notitle with lines linestyle 1
unset label
set origin 0.05,0.657500
set label "bp3-3" at graph -0.145, graph 0.5
plot "n.trace" using 1:35 notitle with lines linestyle 1
unset label
set origin 0.05,0.707500
set label "bp3-4" at graph -0.145, graph 0.5
plot "n.trace" using 1:36 notitle with lines linestyle 1
unset label
set origin 0.05,0.757500
set label "bp3-5" at graph -0.145, graph 0.5
plot "n.trace" using 1:37 notitle with lines linestyle 1
unset label
set origin 0.05,0.807500
set label "bp3-6" at graph -0.145, graph 0.5
plot "n.trace" using 1:38 notitle with lines linestyle 1
unset label
set origin 0.05,0.857500
set label "bp3-7" at graph -0.145, graph 0.5
plot "n.trace" using 1:39 notitle with lines linestyle 1
unset label
set origin 0.05,0.907500
set label "bp3-8" at graph -0.145, graph 0.5
plot "n.trace" using 1:40 notitle with lines linestyle 1
unset label
set origin 0.05,0.957500
set label "bp3-9" at graph -0.145, graph 0.5
plot "n.trace" using 1:41 notitle with lines linestyle 1
unset label
