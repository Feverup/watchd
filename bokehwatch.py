#! /usr/bin/env python
# -*- coding: utf-8 -*-

# PHASE 1 : create datasource objects

import datetime

now = datetime.datetime.now()

def watchd_data ( input_file , threshold , low ) :
    data = dict(date=[], time=[], count=[], healthy=[], mean=[], sigma=[], two_sigma=[], sigma_up=[], sigma_down=[], decile=[], threshold=[], low=[])
    predict = dict(date=[], predict=[])
    with open(input_file) as fd :
        line = fd.readline()
        while line :
            items = line[:-1].split()
            date = datetime.datetime.strptime( "%s %s" % (items[0], items[1].split('.')[0]) , "%Y-%m-%d %H:%M:%S" )
            if (now - date).total_seconds() < 3*3600 :
              try :
                healthy = int(items[4]) - int(items[3])
                data['date'].append( date )
                data['time'].append( float(items[2]) )
                data['count'].append( int(items[4]) )
                #data['healthy'].append( int(items[4]) - int(items[3]) )
                #data['mean'].append( float(items[5]) * ( int(items[4]) - int(items[3]) ) )
                #data['sigma'].append( float(items[6]) * ( int(items[4]) - int(items[3]) ) )
                #data['decile'].append( float(items[7]) * ( int(items[4]) - int(items[3]) ) )
                data['healthy'].append( healthy )
                data['mean'].append( float(items[5]) * healthy )
                data['sigma'].append( float(items[6]) * healthy )
                data['decile'].append( float(items[7]) * healthy )
                #data['two_sigma'].append( ( float(items[5]) + 2 * float(items[6]) ) * ( int(items[4]) - int(items[3]) ) )
                #data['threshold'].append( threshold * ( int(items[4]) - int(items[3]) ) )
                #data['low'].append( low * ( int(items[4]) - int(items[3]) ) )
                data['two_sigma'].append( ( float(items[5]) + 2 * float(items[6]) ) * healthy )
                data['sigma_up'].append( ( float(items[5]) + float(items[6]) ) * healthy )
                data['sigma_down'].append( ( float(items[5]) - float(items[6]) ) * healthy )
                data['threshold'].append( threshold * healthy )
                data['low'].append( low * healthy )

                #predict['date'].append( date + datetime.timedelta(minutes=5) )
                predict['date'].append( date )
                predict['predict'].append( float(items[8]) * ( int(items[4]) - int(items[3]) ) )
              except Exception , ex :
                print "Se ha roto : '%s'" % ex
                print "           : %s" % line
            line = fd.readline()
    return ColumnDataSource(data) , ColumnDataSource(predict)

from bokeh.models import ColumnDataSource

#backend = ColumnDataSource( watchd_data('front-balancer.out', 80, 30) )
#recommender = ColumnDataSource( watchd_data('recommender.out', 60, 25) )
backend = watchd_data('backend.out', 80, 30)
#backend = watchd_data('front-balancer.out', 80, 30)
recommender = watchd_data('recommender.out', 60, 25)
#alpha = watchd_data('alpha-recommender.out', 60, 25)


# PHASE 2 : page/figure definition

from bokeh.plotting import figure, curdoc

p1 = figure(width=800, plot_height=600, title="backend", x_axis_type="datetime")
p2 = figure(width=800, plot_height=600, title="recommender", x_axis_type="datetime")
#p3 = figure(width=800, plot_height=600, title="alpha", x_axis_type="datetime")

for p,d in ( p1 , backend[0] ) , ( p2 , recommender[0] ) :
#for p,d in ( p1 , backend[0] ) , ( p2 , recommender[0] ) , ( p3 , alpha[0] ) :
    p.line(x='date', y='mean', source=d, color='navy', line_width=1, legend="mean")
    p.line(x='date', y='sigma', source=d, color='crimson', line_width=1, legend="sd")
    p.line(x='date', y='decile', source=d, color='chocolate', line_width=2, legend="10%")
    p.line(x='date', y='two_sigma', source=d, color='darkcyan', line_width=2, legend="two sigma")
    p.line(x='date', y='sigma_up', source=d, color='navy', line_width=2, legend="avg + sigma")
    #p.line(x='date', y='sigma_down', source=d, color='navy', line_width=2, legend="avg - sigma")
    p.line(x='date', y='threshold', source=d, color='red', line_width=3, legend="scaling threshold")
    jilito = p.line(x='date', y='low', source=d, color='pink', line_width=4, legend="lower scale")
    #p.line(x='date', y='count', source=d, color='crimson', line_width=2, legend="# nodes")

#p3.line(x='date', y='mean', source=alpha[0], color='navy', line_width=1, legend="mean")
#p3.line(x='date', y='sigma', source=alpha[0], color='crimson', line_width=1, legend="sd")
#p3.line(x='date', y='decile', source=alpha[0], color='chocolate', line_width=2, legend="10%")
#p3.line(x='date', y='two_sigma', source=alpha[0], color='darkcyan', line_width=2, legend="two sigma")

for p,d in ( p1 , backend[1] ) , ( p2 , recommender[1] ) :
    p.line(x='date', y='predict', source=d, color='green', line_width=2, legend="5 minute prediction")

for p in p1 , p2 : # , p3 :
    p.legend[0].location = "top_left"
    #p.legend[0].label_text_font_size = '6pt'
    #p.legend[0].legend_spacing = 0

#p.xaxis.formatter=DatetimeTickFormatter(formats=dict(
#        hours=["%d %B %Y"],
#        days=["%d %B %Y"],
#        months=["%d %B %Y"],
#        years=["%d %B %Y"],
#    ))
    p.xaxis.major_label_orientation = 3.141592/4

from bokeh.models import LinearAxis, Range1d

#for p,d,threshold in ( p1 , backend[0] , 80 ) , ( p2 , recommender[0] , 60 ) :
#    p.extra_y_ranges['elb_size'] = Range1d(start=0, end=max(d.data['count'])+1)
#    p.line(x='date', y='count', source=d, color='crimson', y_range_name="elb_size", line_width=2, legend="# nodes")
#    p.add_layout(LinearAxis(y_range_name="elb_size"), 'right')

#p3.extra_y_ranges['elb_size'] = Range1d(start=0, end=max(alpha[0].data['count'])+1)
#p3.line(x='date', y='count', source=alpha[0], color='crimson', y_range_name="elb_size", line_width=2, legend="# nodes")
#p3.add_layout(LinearAxis(y_range_name="elb_size"), 'right')


from bokeh.io import gridplot
#p = gridplot([[p1, p2],[p3]])
p = gridplot([[p1, p2],[]])
p.toolbar_location='above'


# PHASE 3 : application/session setup

from bokeh.plotting import output_file, show

output_file("/var/www/html/watchd.html", title='ELB cpu usage')#, mode='inline')
show(p)


#from bokeh.embed import file_html
#from bokeh.resources import Resources
#with open( '/var/www/html/watcher.html' , 'w' ) as fd :
#    fd.write( file_html( p3 , Resources() ) )


#import os
#from bokeh.embed import components
#
#for p,f in ( ( p1 , 'backend.js' ) , ( p2 , 'recommender.js' ) , ( p3 , 'alpha.js' ) ) :
#    with open(os.path.join('/var/www/html',f), 'w') as fd :
#        script, div = components(p)
#        print div
#        fd.write( script )

