
def recv( sock , buffsize=1024 ) :
    data = sock.recv(buffsize)
    header , data = data.split('\n', 1)
    response_size , status_line = header.split(None, 1)
    if not data :
        if response_size == '-1' :
            print "ERROR : %s" % status_line
        return
    size = int(response_size) + 1
    while len(data.split('\n')) < size :
        while data[-1] != "\n" :
            data += sock.recv(buffsize)
        if len(data.split('\n')) < size :
            data += sock.recv(buffsize)
    if size == 2 :
        return data[:-1]
    return data[:-1].split('\n')

class cpu ( dict ) :

    busy = ('system', 'user', 'nice', 'wait', 'interrupt', 'softirq')
    types = ('system', 'user', 'nice', 'wait', 'idle', 'interrupt', 'softirq', 'steal')

    def __init__ ( self ) :
        dict.__init__( self )
        for attr in self.types :
            self[attr] = float('nan')

    def summary ( self ) :
        return sum([self[v] for v in self.busy]) , self['idle'] , self['steal']

    def dump ( self ) :
        return "%5.2f %5.2f %5.2f" % self.summary()

    def __str__ ( self ) :
        return " ".join( [ "%5.2f" % self[k] for k in self.types ] )

class aggregated_metric ( dict ) :

    def __init__ ( self , minsize=5 , length=10 ) :
        self.tstamp = None
        self.minsize = minsize
        self.length = length
        dict.__init__( self )

    def unshift ( self ) :
        keys = self.keys()
        keys.sort()
        keys.reverse()
        return dict.pop(self, keys.pop())

    def __setitem__ ( self , key , value ) :
        if not self.has_key(key) :
            dict.__setitem__( self , key , [] )
        self.tstamp = key
        self.last().append( value )
        if len(self) > self.length :
            self.unshift()

    def full ( self ) :
        return len(self) > self.minsize

    def last ( self ) :
        return self[self.tstamp]

    def __str__ ( self ) :
        return "size: %d\n%s" % ( len(self) , "\n".join( [ "%s %s" % ( k , self[k] ) for k in self.keys() ] ) )

