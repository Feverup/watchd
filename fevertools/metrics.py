
import array
import math
import datetime
import time
import sys

def recv( sock , buffsize=1024 ) :
    data = sock.recv(buffsize)
    while data.find(' ') < 0 :
        data += sock.recv(buffsize)
    size = data.split()[0]
    if size == '-1' :
      size = 0
    size = int(size) + 2 # Add header and trailing newline
    while len(data.split('\n')) < size :
        while data[-1] != "\n" :
            data += sock.recv(buffsize)
        if len(data.split('\n')) < size :
            data += sock.recv(buffsize)
    items = data.split('\n')
    items.pop() # Remove trailing endline
    response_size , status_line = items.pop(0).split(None, 1)
    if size == 2 :
        if response_size == '-1' :
            sys.stderr.write( "ERROR : %s %s\n" % ( datetime.datetime.now() , status_line ) )
        return
    elif size == 3 :
        return items[0]
    return items

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

def sign ( value ) :
    floatsign = math.copysign(1, value)
    return int(floatsign)

class aggregated_metric ( dict ) :

    def __init__ ( self , statistics , minsize=5 , length=10 ) :
        self.tstamp = None
        self.minsize = minsize
        self.length = length
        self.statistics = statistics
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
        self[self.tstamp].append( value )
        if len(self) > self.length :
            self.unshift()

    def full ( self ) :
        return len(self) > self.minsize

    def last ( self , interval=0 ) :
        if not interval :
            return array.array( 'f' , self[self.tstamp] )
        elif interval < 0 :
            return [ i for k in self.keys() for i in self[k] ]
        tstamp = time.time() - interval
        return array.array( 'f' , [ i for k in self.keys() for i in self[k] if k > tstamp ] )

    def check_threshold ( self , threshold , interval=-1 ) :
      methods = [ getattr(self, s) for s in self.statistics ]
      values = [ method(interval) for method in methods ]
      return [ v for v in values if cmp(v, abs(threshold)) == sign(threshold) ]

    def two_sigma ( self , interval ) :
      mean , sd = self.mean(interval)
      return mean - 2 * sd

    def one_tenth ( self , interval ) :
      return self.quantile(0.1, interval)

    def mean ( self , interval=0 ) :
        data = self.last(interval)
        n = len(data)
        mean = sum(data) / n
        data2 = [ v*v for v in data ]
        sd  = math.sqrt( sum(data2) / n - mean*mean )
        return mean , sd

    def quantile ( self , prob , interval=0 ) :
        data = self.last(interval)
        n = len(data)
        # As indexes start at 0, we use floor instead of ceil for percentile index
        limit = int(math.floor( n * prob ))
        return sorted(data)[limit]

    def __str__ ( self ) :
        return "size: %d\n%s" % ( len(self) , "\n".join( [ "%s %s" % ( k , self[k] ) for k in self.keys() ] ) )

