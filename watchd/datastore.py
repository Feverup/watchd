
import socket

class collectd :

    def __init__ ( self , sockname="/var/run/collectd-unixsock" ) :
        self.sock = socket.socket( socket.AF_UNIX )
        self.sock.connect( sockname )

    def send ( self , string ) :
        return self.sock.send( string )

    def recv ( self , buffsize=1024 ) :
        return self.sock.recv(buffsize)

