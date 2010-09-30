pdf('${base}.pdf')
d <- read.table('${base}.txt', header=T)
attach(d)
#lty=2,
plot(time, stimulus, type='l', bty='n',  las=1,  col='blue' ,xlab='time', ylab='strength')
title(main='$title')
lines(c(0.5,0.5), c(-0.1,1.1), col='darkgray')
text(c(0.15), c(-0.022), labels=c('off'), col='black')
lines(c(1.5,1.5), c(-0.1,1.1), col='darkgray')
text(c(1.0), c(-0.022), labels=c('inh'), col='black')
text(c(2.7), c(-0.022), labels=c('exc'), col='black')
lines(c(4.0,4.0), c(-0.1,1.1), col='darkgray')
text(c(4.5), c(-0.022), labels=c('off'), col='black')
lines(time, output, type='l',  col='red')
#lines(c(0,5), c(0.5,0.5), col='red', lty=2)
#if $plot_state
lines(time, state, type='l', col='green')
#legend(0, 1, c('stimulus','response','state'), lty=c(2,1,1), col=c('black','black','blue'))
#else
#legend(0, 1, c('stimulus','response'), lty=c(2,1))
#end if
