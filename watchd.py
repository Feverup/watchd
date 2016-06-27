#!/usr/bin/python

from fevertools import recv, aggregated_elb

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

  if os.fork() :
      os.sys.exit(0)

  config = 'watchd.yml'
  if not os.path.isfile( config ) :
      conf_file = os.path.join( '/etc' , config )
  with open( config ) as fd :
      config = yaml.load( fd )

  metrics = []
  for name in config :
      metrics.append( aggregated_elb(config[name]) )

  while True :

   for metric in metrics :
    sock = socket.socket( socket.AF_UNIX )
    sock.connect( unixsock )

    metric.update( sock )
    metric.check_thresholds()

   with open('/var/lib/nagios3/rw/nagios.cmd', 'a+') as fd :
        fd.write( "[%d] PROCESS_SERVICE_CHECK_RESULT;admin11;watchd;0;watchd OK - service running\n" % time.time() )

   time.sleep(60)

