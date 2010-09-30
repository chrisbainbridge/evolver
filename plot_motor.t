pdf('$out')

d <- read.table('$data', header=T)
attach(d)
plot(seconds, dx, type='l', lty=5, ylim=c(-pi,pi), col='red', xlab='Time (seconds)', ylab='Angle (radians)',
main='Angular response of motorised $joint joint')
lines(seconds, ax, col='red')

#if $joint in ['universal','ball']
lines(seconds, dy, lty=5, col='green')
lines(seconds, ay, col='green')
#if $joint == 'ball'
lines(seconds, dz, lty=5, col='blue')
lines(seconds, az, col='blue')
#end if
#end if

legend(0.3, 3.1, c('desired','actual'), lty=c(5,1))

dev.off()
detach(d)

# vim:ft=r
