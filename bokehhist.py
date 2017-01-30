#! /usr/bin/env python
# -*- coding: utf-8 -*-

# PHASE 1 : create datasource objects

import datetime

now = datetime.datetime.now()

def watchd_data ( input_file , threshold , low ) :
    #data = dict(date=[], time=[], count=[], healthy=[], mean=[], sigma=[], two_sigma=[], decile=[], predict=[], threshold=[], low=[])
    data = dict(date=[], threshold=[], low=[])
    points = dict(date=[], value=[])
    with open(input_file) as fd :
        line = fd.readline()
        while line :
            items = line[:-1].split(None,10)
            date = datetime.datetime.strptime("%s %s" % (items[0], items[1].split('.')[0]) , "%Y-%m-%d %H:%M:%S" )
            if (now - date).total_seconds() < 3*3600 :
                healthy = int(items[4]) - int(items[3])
                data['date'].append( date )
            #    data['time'].append( float(items[2]) )
            #    data['count'].append( int(items[4]) )
            #    data['healthy'].append( int(items[4]) - int(items[3]) )
            #    data['mean'].append( float(items[5]) * ( int(items[4]) - int(items[3]) ) )
            #    data['sigma'].append( float(items[6]) * ( int(items[4]) - int(items[3]) ) )
            #    data['decile'].append( float(items[7]) * ( int(items[4]) - int(items[3]) ) )
            #    data['predict'].append( float(items[8]) * ( int(items[4]) - int(items[3]) ) )
            #    data['two_sigma'].append( ( float(items[5]) + 2 * float(items[6]) ) * ( int(items[4]) - int(items[3]) ) )
                data['threshold'].append( threshold * healthy )
                data['low'].append( low * healthy )

                if len(items) == 11 :
                 for v in items[10].split(',') :
                    points['date'].append( date )
                    points['value'].append( float(v) )
            line = fd.readline()
    return ColumnDataSource(data), ColumnDataSource(points)

from bokeh.models import ColumnDataSource

#backend = watchd_data('front-balancer.out', 80, 30)
backend = watchd_data('backend.out', 80, 30)
#recommender = watchd_data('front-balancer.out', 60, 25)
recommender = watchd_data('recommender.out', 60, 25)

# PHASE 2 : page/figure definition

from bokeh.plotting import figure, curdoc

p1 = figure(width=800, plot_height=600, title="backend", x_axis_type="datetime")
p2 = figure(width=800, plot_height=600, title="recommender", x_axis_type="datetime")

for p,d in ( p1 , backend ) , ( p2 , recommender ) :
    p.scatter(x='date', y='value', source=d[1], color='navy', size=2)
    p.line(x='date', y='threshold', source=d[0], color='red', line_width=2)
    p.line(x='date', y='low', source=d[0], color='pink', line_width=4)


from bokeh.io import gridplot
p = gridplot([[p1, p2],[]])
p.toolbar_location='above'


# PHASE 3 : application/session setup

from bokeh.plotting import output_file, show
output_file("/var/www/html/histogram.html")
show(p)

#from bokeh.client import push_session
#session = push_session(curdoc(), 'histo')
#
#session.show() # open the document in a browser
#session.loop_until_closed() # run forever

