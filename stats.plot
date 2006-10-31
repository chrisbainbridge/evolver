set style data line
set terminal postscript eps noenhanced color solid defaultplex

set out 'stats.eps'

plot \
'fitnessValues.tmp' using 1:2 title 'min' , \
'fitnessValues.tmp' using 1:3 title 'mean' , \
'fitnessValues.tmp' using 1:4 title 'max' 

clear

#set out 'time_vs_velocity_and_random_force.eps'
#plot 'evo.stats' using 1:($12) with lines title 'desired velocity','evo.stats' using 1:($13/10) with lines title 'random force'

