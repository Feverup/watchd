
import socket

class collectd :

    def __init__ ( self , sockname="/var/run/collectd-unixsock" ) :
        self.sock = socket.socket( socket.AF_UNIX )
        self.sock.connect( sockname )

    def get ( self , payload ) :
        return self.__send("GETVAL %s\n" % payload)

    def put ( self , payload ) :
        return self.__send("PUTVAL %s\n" % payload)

    def __send ( self , payload , buffsize=1024 ) :
        self.sock.send( payload )
        data = self.sock.recv(buffsize)
        while data.find(' ') < 0 :
            data += self.sock.recv(buffsize)
        size = data.split()[0]
        if size == '-1' :
          size = 0
        size = int(size) + 2 # Add header and trailing newline
        while len(data.split('\n')) < size :
            while data[-1] != "\n" :
                data += self.sock.recv(buffsize)
            if len(data.split('\n')) < size :
                data += self.sock.recv(buffsize)
        items = data.split('\n')
        items.pop() # Remove trailing endline
        response_size , status_line = items.pop(0).split(None, 1)
        if size == 2 :
            if response_size == '-1' :
                os.sys.stderr.write( "ERROR : %s , '%s %s' gave %s\n" % ( datetime.datetime.now() , command , payload , status_line ) )
            return
        elif size == 3 :
            return items[0]
        return items

