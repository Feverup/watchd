
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
            print "ERROR : %s" % status_line
        return status_line
    elif size == 3 :
        return items[0]
    return items

class weighted ( float ) :

    def __new__ ( cls , value , weight=1.0 ) :
        return super( weighted , cls ).__new__( cls , value )

    def __init__ ( self , value , weight=1.0 ) :
        self.weight = weight

    def __add__ ( self , other ) :
        if self.weight != other.weight :
            raise Exception( "Cannot sum weighted numbers with different weights" )
        return weighted( super( weighted , self ).__add__( other ) , self.weight )

    def __radd__ ( self , other ) :
        if other == 0 :
            return self
        return self.__add__( other )

    def __iadd__ ( self , other ) :
        return self.__add__( other )

    def __str__ ( self ) :
        return "%sw%s" % ( float(self) , self.weight )

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
        vals_str = {}
        for k in self.keys() :
            vals_str[k] = map(str, self[k])
        return "size: %d\n%s" % ( len(self) , "\n".join( [ "%s %s" % ( k , vals_str[k] ) for k in self.keys() ] ) )

import boto.ec2
import boto.ec2.elb

class aggregated_elb ( aggregated_metric ) :

    def __init__ ( self , elbname , minsize=5 , length=10 ) :
        self.count = None
        self.healthy = None
        self.elbname = elbname
        aggregated_metric.__init__ ( self , minsize , length )

    def hostnames ( self ) :
        instances = boto.ec2.elb.connect_to_region("eu-west-1") \
                                .get_all_load_balancers([self.elbname])[0] \
                                .get_instance_health()
        in_service = [ i.instance_id for i in instances if i.state == 'InService' ]
        self.count = len(instances)
        self.healthy = len(in_service)
        instances = boto.ec2.connect_to_region("eu-west-1") \
                       .get_only_instances(in_service)
        return [ str(i.private_dns_name.split('.')[0]) for i in instances ]

    def __str__ ( self ) :
        return "elb: %s/%s , %s" % ( self.healthy , self.count , aggregated_metric.__str__(self) )

