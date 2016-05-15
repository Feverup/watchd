
def recv( sock , buffsize=1024 ) :
    data = sock.recv(buffsize)
    size = int(data.split('\n')[0].split()[0]) + 1
    if size == 0 :
        print "ERROR : %s" % " ".join(data.split()[1:])
        return
    if size+1 == len(data.split('\n')) :
        return data.split('\n')[1]
    while size > 0 :
        buff = sock.recv(buffsize)
        data += buff
        items = buff.split('\n')
        size -= len(buff.split('\n'))
    return data.split('\n')[1:-1]

class aggregated_metric ( dict ) :

    def __init__ ( self , length=10 ) :
        self.length = length
        dict.__init__( self )

    def unshift ( self ) :
        keys = self.keys()
        keys.sort()
        keys.reverse()
        return dict.pop(self, keys.pop())

    def __setitem__ ( self , key , value ) :
        dict.__setitem__( self , "%d"%float(key) , value )
        if len(self) > self.length :
            self.unshift()

    def __str__ ( self ) :
        return "size: %d\n%s" % ( len(self) , "\n".join( [ "%s %s" % ( k , self[k] ) for k in self.keys() ] ) )

