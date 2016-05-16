#!/usr/bin/python

from fevertools import recv, aggregated_metric
import rrdtool

import boto.ec2
import boto.ec2.elb

import socket
import time

import array
import math
import os

unixsock = '/var/run/collectd-unixsock'
topdir = '/var/lib/collectd/rrd/'

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

    elb_data = array.array( 'f' )

    sock = socket.socket( socket.AF_UNIX )
    sock.connect( unixsock )

    sock.send("LISTVAL\n")
    listval = [ s.split() for s in recv(sock) ]
    listval = dict( [ (b,a) for a,b in listval ] )

    for hostname in [ str(i.private_dns_name.split('.')[0]) for i in instances ] :

      for metric_instance in ('system', 'user', 'nice', 'wait', 'idle', 'interrupt', 'softirq', 'steal') :
        identifier = os.path.join( hostname , 'cpu-0' , 'cpu-%s' % metric_instance )
        date = listval.get(identifier)
        sock.send("GETVAL %s\n" % identifier)
        data0 = recv(sock)

        rrdfile = os.path.join( topdir , "%s.rrd" % identifier )

        try :
            info = rrdtool.info( rrdfile )
        except Exception , ex :
            print "ERROR %s" % ex
            print "     ", dir(ex)
            info = rrdtool.info( rrdfile )
        last = info['last_update'] - info['last_update'] % 60
        data = rrdtool.fetch( rrdfile, 'AVERAGE', '--resolution' , '60' ,
                              '--start' , '-10m' , '--end' , str(last) )

        elb_data.extend( [ d[0] for d in data[2] if d[0] is not None ] )

        if not metrics.has_key(hostname) :
            metrics[hostname] = aggregated_metric()
        metrics[hostname][date] = metric_instance , float(data0.split('=')[1])

    n = len(elb_data)
    mean = sum(elb_data) / n
    data2 = [ v*v for v in elb_data ]
    sd  = math.sqrt( sum(data2) / n - mean*mean )

    # As indexes start at 0, we use floor instead of ceil for percentile index
    limit = int(math.floor( n * 0.2 ))
    minval = sorted(elb_data)[limit]

    time.sleep(60)

