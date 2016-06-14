#!/usr/bin/python

from fevertools import recv, aggregated_metric
from fevertools import elb_group

import boto.ec2
import boto.ec2.elb

import ConfigParser

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

  config = ConfigParser.ConfigParser()
  config.read( [ 'watchd.ini' , '/etc/watchd.ini' ] )

  metrics = []
  for name in config.sections() :
      metrics.append( aggregated_metric(config, name) )

  while True :

   for metric in metrics :
    elb = boto.ec2.elb.connect_to_region("eu-west-1") \
                      .get_all_load_balancers([metric.elbname])[0]

    in_service = [ i.instance_id for i in elb.get_instance_health() if i.state == 'InService' ]
    instances = boto.ec2.connect_to_region("eu-west-1") \
                        .get_only_instances(in_service)

    sock = socket.socket( socket.AF_UNIX )
    sock.connect( unixsock )

    date = time.time()
    full = True

    for hostname in [ str(i.private_dns_name.split('.')[0]) for i in instances ] :

     for m in metric.metric_list :
      sock.send("GETVAL %s/%s\n" % (hostname,m))
      data = recv(sock)

      if data :
          metrics[date] = float(data.split('=')[1])

    if not metrics.full() :
        full = False

    if full :

      if metrics.check_threshold( metric.threshold ) :
        metrics.action.run( elb_group(metric.elbname) )

    time.sleep(60)

