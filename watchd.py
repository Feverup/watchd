#!/usr/bin/python

from fevertools import aggregated_elb

import boto.ec2
import boto.ec2.elb

import yaml

import socket
import time

import os

unixsock = '/var/run/collectd-unixsock'

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

