#!/usr/bin/python

from fevertools import aggregated_elb

import boto.ec2
import boto.ec2.elb

import yaml

import threading

import socket
import time

import os

unixsock = '/var/run/collectd-unixsock'

def server ( sock ) :
    # https://pymotw.com/2/socket/uds.html

    sock.bind(sockfile)
    sock.listen(1)

    while True :
        connection, client_address = sock.accept()

        try:

            # Receive the data in small chunks and retransmit it
            while True:
                data = connection.recv(256)
                if data:
                    connection.sendall("echo: "+data)
                else:
                    break

        finally:
            # Clean up the connection
            connection.close()


if __name__ == '__main__' :

  if len(os.sys.argv) != 1 :
      print "Usage: %s" % os.sys.argv[0].split('.')[-1]
      os.sys.exit(2)

  sockfile = "/var/run/watchd.sock"
  if os.path.exists(sockfile) :
      print "watchd socket found, another watchd instance is running"
      os.sys.exit(1)

  newpid = os.fork()
  if newpid :
      os.sys.exit(0)

  servsock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  serverthread = threading.Thread(target=server, args=( servsock ,) )
  serverthread.daemon = True
  serverthread.start()

  config = 'watchd.yml'
  if not os.path.isfile( config ) :
      conf_file = os.path.join( '/etc' , config )
  with open( config ) as fd :
      config = yaml.load( fd )

  metrics = []
  for name in config :
      metrics.append( aggregated_elb(name, config) )

  while True :

   for metric in metrics :
    sock = socket.socket( socket.AF_UNIX )
    sock.connect( unixsock )

    try :
      metric.update( sock )
      metric.check_thresholds()
    except Exception , ex :
      os.sys.stdout.write( "Exception happened at %s\n%s\n" %( datetime.datetime.now() , ex ) )
      traceback.print_exc()
      os.sys.stdout.write( "\n" )
      os.sys.stdout.flush()

   with open('/var/lib/nagios3/rw/nagios.cmd', 'a+') as fd :
        fd.write( "[%d] PROCESS_SERVICE_CHECK_RESULT;admin11;watchd;0;watchd OK - service running\n" % time.time() )

   time.sleep(60)

