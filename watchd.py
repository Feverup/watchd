#!/usr/bin/python

from fevertools import recv, aggregated_elb
from fevertools import elb_group

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

    date = time.time()

    for hostname in metric.hostnames(date) :

     for m in metric.metric_list :
      sock.send("GETVAL %s/%s\n" % (hostname,m))
      data = recv(sock)

      if data :
          metric[date] = data.split('=')[1]

    if metric.full() :

      if metric.check_thresholds() :
        metric.action.run( elb_group(metric.elbname) )

   time.sleep(60)

