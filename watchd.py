#!/usr/bin/python

from fevertools import recv, aggregated_metric

import boto.ec2
import boto.ec2.elb

import socket
import time

import array
import math
import os

unixsock = '/var/run/collectd-unixsock'

if __name__ == '__main__' :

  if len(os.sys.argv) != 2 :
      print "Usage: %s elbname" % os.sys.argv[0].split('.')[-1]
      os.sys.exit(2)

  if os.fork() :
      os.sys.exit(0)

  metrics = {}

  while True :

    elbname = os.sys.argv[1]
    elb = boto.ec2.elb.connect_to_region("eu-west-1") \
                      .get_all_load_balancers([elbname])[0]

    in_service = [ i.instance_id for i in elb.get_instance_health() if i.state == 'InService' ]
    instances = boto.ec2.connect_to_region("eu-west-1") \
                        .get_only_instances(in_service)

    sock = socket.socket( socket.AF_UNIX )
    sock.connect( unixsock )

    date = time.time()
    full = True

    for hostname in [ str(i.private_dns_name.split('.')[0]) for i in instances ] :

      if not metrics.has_key(hostname) :
          metrics[hostname] = aggregated_metric()

      for metric_instance in ('system', 'user', 'nice', 'wait', 'idle', 'interrupt', 'softirq', 'steal') :
        identifier = os.path.join( hostname , 'cpu-0' , 'cpu-%s' % metric_instance )
        sock.send("GETVAL %s\n" % identifier)

        data = recv(sock)
        metrics[hostname][date] = metric_instance , float(data.split('=')[1])

      if not metrics[hostname].full() :
          full = False

    if full :
      elb_data = array.array( 'f' ) , array.array( 'f' ) , array.array( 'f' )
      for h in metrics :
        metrics[h].push( elb_data )

      for i in range(3) :
        n = len(elb_data[i])
        mean = sum(elb_data[i]) / n
        data2 = [ v*v for v in elb_data[i] ]
        sd  = math.sqrt( sum(data2) / n - mean*mean )

        # As indexes start at 0, we use floor instead of ceil for percentile index
        limit = int(math.floor( n * 0.2 ))
        minval = sorted(elb_data[i])[limit]

    time.sleep(60)

