
# binary array of n eg. binary(5) = ['1', '0', '1']
binary = lambda n: n>0 and binary(n>>1) + [str(n&1)] or []
# string of binary array above '010...'
sbinary = lambda n: len(n)>0 and n[0] + sbinary(n[1:]) or ''


# random stuff
#j0.setParam(ode.ParamFMax,40)
#j0.setParam(ode.ParamVel,10)

        # UNCOMMENT THIS TO APPLY FORCES DIRECTLY RATHER THAN MOTOR MODEL
        # clip and apply force directly (no motor model)
        #if force<-2.5: force = -2.5
        #if force>2.5: force = 2.5
        #self.geoms['body0'].getBody().addForce((force,0,0))

        # quantise.
        #force = (round(((force+2.5)*3))/3)-2.5
        # neural net will already be quantised to range [0,1]

        #if len(outputs) > 1:
        #    print 'WARNING: some outputs from the neural net aren\'t connected!'
        




            # THIS CODE IS SUPPOSED TO FIGURE OUT THE BEST WAY TO GET TO AN
            # ANGLE TAKING INTO ACCOUNT JOINT STOPS... 
            # ... BUT IT SEEMS COMPLICATED AND UNNECESSARY
#            lostop = self.getParam(params[x][0])
#            if lostop != -ode.Infinity:
#                lostop %= (2*math.pi)
#            print 'lostop=',lostop
#            histop = self.getParam(params[x][1])
#            if histop != ode.Infinity:
#                histop %= (2*math.pi)
#            print 'histop=',histop
#            d = None
#            dist = None
#            if a<b and ((histop==None or histop==ode.Infinity) or not a<=histop<=b):
#                if not d or b-a<=math.pi:
#                    d = 'ccw'
#                    dist = b-a
#            if a>b and ((lostop==None or lostop==ode.Infinity) or not b<=lostop<=a):
#                if not d or a-b<=math.pi:
#                    d = 'cw'
#                    dist = a-b
#            if a<b and ((lostop==None or lostop==ode.Infinity) or (not 0<=lostop<=a and not b<=lostop<=2*math.pi)):
#                if not d or b-a>=math.pi:
#                    d = 'cw'
#                    dist = 2*math.pi-b+a
#            if a>b and (histop==ode.Infinity or (not a<=histop<2*math.pi and not 0<=histop<=b)):
#                if not d or a-b>=math.pi:
#                    d = 'ccw'
#                    dist = 2*math.pi-a+b
 
            # fixme: these contants need tuning
