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
                    items = data[:-1].split()
                    if items[0] == "what" :
                        if len(items) == 2 :
                            for metric in metrics :
                                if metric.elbname == items[1] :
                                    connection.sendall("alarms %s\n" % ", ".join([a.name for a in metric.alarms]))
                                    break
                            else :
                                connection.sendall("error bad metric\n")
                        else :
                            connection.sendall("metrics %s\n"%", ".join([m.name for m in metrics]))
                    elif items[0] == "kill" :
                        connection.sendall("stopping\n")
                        state['serving'] = False
                        break
                    elif items[0] == "get" and len(items) == 3 :
                        metric = [ m for m in metrics if m.elbname == items[1] ]
                        if len(metric) == 1 :
                            for alarm in metric[0].alarms :
                                if alarm.name == items[2] :
                                    if alarm.check_thresholds(metric[0], 5*60) :
                                        connection.sendall("state WARNING\n")
                                    else :
                                        connection.sendall("state OK\n")
                                    break
                            else :
                                connection.sendall("error bad alarm\n")
                        else :
                            connection.sendall("error bad metric\n")
                    else :
                        connection.sendall("echo: %s\n"%data)
                else:
                    break

        finally:
            # Clean up the connection
            connection.close()


if __name__ == '__main__' :

  if len(os.sys.argv) != 1 :
      print "Usage: %s" % os.sys.argv[0].split('.')[-1]
      os.sys.exit(2)

  pidfile = "/var/run/watchd.pid"
  if os.path.isfile(pidfile) :
      print "PID file exists, another watchd instance is likely running"
      os.sys.exit(1)

  newpid = os.fork()
  if newpid :
      with open( pidfile , 'w' ) as fd :
          fd.write( "%d\n" % newpid )
      os.sys.exit(0)

  sockfile = "/var/run/watchd.sock"
  if os.path.exists(sockfile) :
      print "stale watchd socket found, removing"
      os.unlink( sockfile )

  servsock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  serverthread = threading.Thread(target=server, args=( servsock ,) )
  serverthread.name = "SocketServer"
  serverthread.daemon = True
  serverthread.start()

  config = 'watchd.yml'
  if not os.path.isfile( config ) :
      conf_file = os.path.join( '/etc' , config )
  with open( config ) as fd :
      config = yaml.load( fd )

  state = { 'serving':True }

  metrics = []
  for name in config :
      metrics.append( aggregated_elb(name, config) )

  while state['serving'] :

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

  os.unlink( sockfile )
  os.unlink( pidfile )

