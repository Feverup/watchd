
import socket
import datetime
import sys

class collectd :

    def __init__ ( self , sockname="/var/run/collectd-unixsock" ) :
        self.sock = socket.socket( socket.AF_UNIX )
        try :
            self.sock.connect( sockname )
        except socket.error, ex :
            sys.stderr.write( "ERROR : %s , socket failed to connect; %s\n" % ( datetime.datetime.now() , ex ) )

    def get ( self , payload ) :
        return self.__send("GETVAL %s\n" % payload)

    def put ( self , payload ) :
        return self.__send("PUTVAL %s\n" % payload)

    def __send ( self , payload , buffsize=1024 ) :
        try :
            self.sock.send( payload )
        except socket.error, ex :
            sys.stderr.write( "ERROR : %s , socket failed to send; %s\n" % ( datetime.datetime.now() , ex ) )
            return
        try :
            data = self.sock.recv(buffsize)
            while data.find(' ') < 0 :
                data += self.sock.recv(buffsize)
        except socket.error, ex :
            sys.stderr.write( "ERROR : %s , socket failed to read; %s\n" % ( datetime.datetime.now() , ex ) )
            return
        size = data.split()[0]
        if size == '-1' :
          size = 0
        size = int(size) + 2 # Add header and trailing newline
        try :
            while len(data.split('\n')) < size :
                while data[-1] != "\n" :
                    data += self.sock.recv(buffsize)
                if len(data.split('\n')) < size :
                    data += self.sock.recv(buffsize)
        except socket.error, ex :
            sys.stderr.write( "ERROR : %s , socket failed to read; %s\n" % ( datetime.datetime.now() , ex ) )
        items = data.split('\n')
        items.pop() # Remove trailing endline
        response_size , status_line = items.pop(0).split(None, 1)
        if size == 2 :
            if response_size == '-1' :
                sys.stderr.write( "ERROR : %s , '%s' gave %s\n" % ( datetime.datetime.now() , payload , status_line ) )
            return
        elif size == 3 :
            return items[0]
        return items

