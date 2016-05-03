#!/usr/bin/python

import rrdtool

import array
import math
import os

topdir = '/var/lib/collectd/rrd/'

if __name__ == '__main__' :

    if len(os.sys.argv) != 2 :
        print "Usage: %s hostname" % os.sys.argv[0].split('.')[-1]
        os.sys.exit(2)

    hostname = os.sys.argv[1]
    rrdfile = os.path.join( topdir , hostname , 'cpu-0' , 'cpu-idle.rrd' )

    info = rrdtool.info( rrdfile )
    last = info['last_update'] - info['last_update'] % 60
    data = rrdtool.fetch( rrdfile, 'AVERAGE', '--resolution' , '60' ,
                         '--start' , '-10m' , '--end' , str(last) )

    data = array.array( 'f' , [ d[0] for d in data[2] if d[0] ] )

    n = len(data)
    mean = sum(data) / n
    data2 = [ v*v for v in data ]
    sd  = math.sqrt( sum(data2) / n - mean*mean )

    # For 10 values, the second point marks 20% percentile
    minval = sorted(data)[1]

