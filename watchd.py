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

  if len(os.sys.argv) != 3 :
      print "Usage: %s metric[,metric,...] elbname" % os.sys.argv[0].split('.')[-1]
      os.sys.exit(2)

  if os.fork() :
      os.sys.exit(0)

  metrics = aggregated_metric()

  while True :

    metric_list = os.sys.argv[1].split(",")
    elbname = os.sys.argv[2]
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

     for metric in metric_list :
      sock.send("GETVAL %s/%s\n" % (hostname,metric))
      data = recv(sock)

      metrics[date] = float(data.split('=')[1])

      if not metrics.full() :
          full = False

    if full :
      elb_data = array.array( 'f' )
      for values in metrics.values() :
          elb_data.extend( values )

      n = len(elb_data)
      mean , sd = metrics.mean()

      # As indexes start at 0, we use floor instead of ceil for percentile index
      limit = int(math.floor( n * 0.2 ))
      minval = sorted(elb_data)[limit]

    time.sleep(60)

