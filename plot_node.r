pdf('${base}.pdf')
d <- read.table('${base}.txt', header=T)
attach(d)
plot(time, stimulus, type='l', bty='n', las=1, lty=4, xlab='time', ylab='strength')
title(main='$title')
lines(c(1.5,1.5), c(-0.1,1.1), col='green')
text(c(1.52), c(-0.022), labels=c('inh  exc'), col='green')
lines(time, output, type='l', lty=1)
lines(c(0,5), c(0.5,0.5), col='red', lty=2)
#if $plot_state
lines(time, state, type='l', lty=1,col='blue')
legend(0, 1, c('stimulus','response','state'), lty=c(2,1,1), col=c('black','black','blue'))
#else
legend(0, 1, c('stimulus','response'), lty=c(2,1))
#end if
