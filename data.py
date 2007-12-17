from persistent import Persistent
class Run(Persistent):
    def __init__(self, name, cl):
        self.name = name
        self.cl = cl
        self.taken = 0

    def __repr__(self):
        return 'Run(%s,%d)'%(self.name, self.taken)

