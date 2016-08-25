
from fevertools import elb_group, fever_config

import boto.ec2.autoscale

import urllib, urllib2
import uuid

import math
import threading
import datetime
import time
import os

def collectd( sock , payload , command='GETVAL' , buffsize=1024 ) :
    sock.send("%s %s\n" % (command,payload))
    data = sock.recv(buffsize)
    while data.find(' ') < 0 :
        data += sock.recv(buffsize)
    size = data.split()[0]
    if size == '-1' :
      size = 0
    size = int(size) + 2 # Add header and trailing newline
    while len(data.split('\n')) < size :
        while data[-1] != "\n" :
            data += sock.recv(buffsize)
        if len(data.split('\n')) < size :
            data += sock.recv(buffsize)
    items = data.split('\n')
    items.pop() # Remove trailing endline
    response_size , status_line = items.pop(0).split(None, 1)
    if size == 2 :
        if response_size == '-1' :
            os.sys.stderr.write( "ERROR : %s , '%s %s' gave %s\n" % ( datetime.datetime.now() , command , payload , status_line ) )
        return
    elif size == 3 :
        return items[0]
    return items

class weighted ( float ) :

    def __new__ ( cls , value , weight ) :
        return super( weighted , cls ).__new__( cls , value )

    def __init__ ( self , value , weight ) :
        self.weight = weight

    def __add__ ( self , other ) :
        if self.weight != other.weight :
            raise Exception( "Cannot sum weighted numbers with different weights" )
        return weighted( super( weighted , self ).__add__( other ) , self.weight )

    def __radd__ ( self , other ) :
        if other == 0 :
            return self
        return self.__add__( other )

    def __iadd__ ( self , other ) :
        return self.__add__( other )

    def scaled ( self ) :
        return float(self) * self.weight

    def scaled2 ( self ) :
        return float(self) * self.scaled()

    def __str__ ( self ) :
        return "%sw%s" % ( float(self) , self.weight )

class cpu ( dict ) :

    busy = ('system', 'user', 'nice', 'wait', 'interrupt', 'softirq')
    types = ('system', 'user', 'nice', 'wait', 'idle', 'interrupt', 'softirq', 'steal')

    def __init__ ( self ) :
        dict.__init__( self )
        for attr in self.types :
            self[attr] = float('nan')

    def summary ( self ) :
        return sum([self[v] for v in self.busy]) , self['idle'] , self['steal']

    def dump ( self ) :
        return "%5.2f %5.2f %5.2f" % self.summary()

    def __str__ ( self ) :
        return " ".join( [ "%5.2f" % self[k] for k in self.types ] )

def sign ( value ) :
    floatsign = math.copysign(1, value)
    return int(floatsign)

class alarm :

    def __init__ ( self , params , metric ) :
        self.name = params['alarm']
        interval = params.get('interval', metric.window)
        if max( interval , metric.length ) == interval :
            metric.length = interval + 5
        cooldown = params.get('cooldown', metric.window)
        if max( interval , cooldown ) == interval :
            cooldown = interval
        self.interval = interval * 60
        self.cooldown = cooldown * 60
        self.statistics = params['statistics']
        self.action = get_action( params['action'] , metric.name , self )

class aggregated_metric ( dict ) :

    def __init__ ( self , name , conf , window=5 , length=10 ) :
        config = conf[name]
        self.name = name
        self.alias = config.get('alias', name)
        self.metric_list = config['metric_list']
        self.tstamp = 'N'
        self.logfile = config.get('logfile', False)
        self.window = window
        self.length = length
        self.alarms = []
        for params in config['alarms'] :
            self.alarms.append( alarm(params, self) )
        dict.__init__( self )

    def unshift ( self ) :
        keys = self.keys()
        keys.sort()
        keys.reverse()
        return dict.pop(self, keys.pop())

    def input_value ( self , datastr ) :
        return float(datastr)

    def __setitem__ ( self , key , valstr ) :
        if not self.has_key(key) :
            dict.__setitem__( self , key , [] )
        self.tstamp = key
        self[self.tstamp].append( self.input_value(valstr) )
        if len(self) > self.length :
            self.unshift()

    def full ( self , alarm , interval ) :
        return len(self) > alarm.interval/60 and len(self.last(interval)) > 0

    def last ( self , interval ) :
        if not interval :
            return self[self.tstamp]
        elif interval < 0 :
            return [ i for k in self.keys() for i in self[k] ]
        tstamp = time.time() - interval
        return [ i for k in self.keys() for i in self[k] if k > tstamp ]

    def check_thresholds ( self , interval=None ) :
      for alarm in self.alarms :
        if interval is None :
            interval = alarm.interval
        if self.full(alarm, interval) :
            for statistic in alarm.statistics :
                methods = [ getattr(self, s) for s in statistic['methods'] ]
                values = [ method(interval) for method in methods ]
                if [ v for v in values if not math.isnan(v) and cmp(v, abs(statistic['threshold'])) == sign(statistic['threshold']) ] :
                    alarm.action.run( elb_group(self.elbname) )
                    break

    def average ( self , interval ) :
      return self.mean(interval)[0]

    def sigma ( self , interval ) :
      return self.mean(interval)[1]

    def two_sigma ( self , interval ) :
      mean , sd = self.mean(interval)
      return mean + 2 * sd

    def sigma_down ( self , interval ) :
      mean , sd = self.mean(interval)
      return mean - 2 * sd

    def one_tenth ( self , interval ) :
      return self.quantile(0.9, interval)

    # prediction will use all collected values
    def five_mins ( self , interval ) :
      return self.predict(5*60)

    def minmax ( self , interval ) :
        data = self.last(interval)
        if not data :
            return float('nan') , float('nan')
        return min(data), max(data)

    def mean ( self , interval ) :
        data = self.last(interval)
        if not data :
            return float('nan') , float('nan')
        n = len(data)
        mean = sum(data) / n
        data2 = [ v*v for v in data ]
        sd  = math.sqrt( sum(data2) / n - mean*mean )
        return mean , sd

    def quantile ( self , prob , interval ) :
        data = self.last(interval)
        if not data :
            return float('nan')
        n = len(data)
        # As indexes start at 0, we use floor instead of ceil for percentile index
        limit = int(math.floor( n * prob ))
        return sorted(data)[limit]

    def predict ( self , t_0 , delta=True ) :

        if not len(self) > 1 :
            return float('NaN')

        # Formulae taken from http://terpconnect.umd.edu/~toh/spectrum/CurveFitting.html#MathDetails
        # Y = a + bX

        # t_0 is set so that prediction is at t=0
        if delta :
            t_0 = time.time() + t_0
        x, y = [], []

        for tstamp in self.keys() :
            for v in self[tstamp] :
                x.append(tstamp - t_0)
                y.append(float(v))

        fit = lm( x , y )
        return fit[0]

    def dump ( self , interval ) :
        output  = "%7.2f %5.2f %7.2f %7.2f" % ( self.average(interval) , self.sigma(interval) , self.one_tenth(interval) , self.five_mins(interval) )
        output += " :: " +  " , ".join( [ "%7.2f" % v for v in self.last(interval) ] )
        return output

    def __str__ ( self ) :
        vals_str = {}
        for k in self.keys() :
            vals_str[k] = map(str, self[k])
        return "size: %d\n%s" % ( len(self) , "\n".join( [ "%s %s" % ( k , vals_str[k] ) for k in self.keys() ] ) )

def lm ( x , y ) :

    xy = zip(x, y)

    N = len(x)
    if N < 7 :
        return float('nan') , float('nan')
    X, Y = sum(x), sum(y)
    X2 = sum([v*v for v in x])
    XY = sum(map(lambda p: p[0] * p[1], xy))

    det = N * X2 - X * X
    if det == 0 :
        os.sys.stdout.write( "DEGENERATED DATA : %s , %s\n" % (x,y) )
        return float('nan') , float('nan')
    b = (N * XY - X * Y) / det
    a = (Y - b * X) / N

    # SSY = sum(map(lambda p: pow2(p[1] - Y / N), xy))
    # SSR = sum(map(lambda p: pow2(p[1] - (a + b * p[0])), xy))

    # R2 = 1 - SSR / SSY
    # e_b = math.sqrt(SSR / (N - 2)) * math.sqrt(N / det)
    # e_a = math.sqrt(SSR / (N - 2)) * math.sqrt(X2 / det)

    # As we use prediction time as origin, axis crossing is the predicted value
    return a , b


import boto.ec2
import boto.ec2.elb

class weighted_metric ( aggregated_metric ) :

    def input_value ( self , datastr ) :
        if isinstance(datastr, tuple) :
            return weighted(*datastr)
        return weighted(datastr, 1.0)

    def mean ( self , interval ) :
        data = self.last(interval)
        if not data :
            return float('nan') , float('nan')
        n = sum( [ v.weight for v in data ] )
        mean = sum( [ v.scaled() for v in data ] ) / n
        data2 = [ v.scaled2() for v in data ]
        sd  = math.sqrt( sum(data2) / n - mean*mean )
        return mean , sd

class aggregated_elb ( aggregated_metric ) :

    def __init__ ( self , name , conf , window=5 , length=10 ) :
        self.count = None
        self.healthy = None
        self.elbname = conf[name]['elbname']
        aggregated_metric.__init__ ( self , name , conf , window , length )
        self.date = None
        elbinstance = boto.ec2.elb.connect_to_region("eu-west-1") \
                                .get_all_load_balancers([self.elbname])[0]
        for alarm in self.alarms :
            tagname = "%s-%s" % ( alarm.name , self.alias )
            if elbinstance.get_tags().has_key(tagname) :
                print "WARNING : thresholds for %s %s defined on ELB tags as %s, values from configuration file will be ignored" % ( self.name , alarm.name , elbinstance.get_tags()[tagname] )
                for statistic in alarm.statistics :
                    statistic['threshold'] = sign(statistic['threshold']) * float(elbinstance.get_tags()[tagname])

    def input_value ( self , datastr ) :
        if not self.healthy :
            return aggregated_metric.input_value( self , 'nan' )
        return ( 100 - aggregated_metric.input_value( self , datastr ) ) * self.healthy

    def extreme_clean ( self ) :
        v_min , v_max = self.minmax(-1)
        for k in sorted(self.keys()) :
            if self[k].count(v_min) :
                self[k].pop(self[k].index(v_min))
                break
        for k in sorted(self.keys(), reverse=True) :
            if self[k].count(v_max) :
                self[k].pop(self[k].index(v_max))
                return

    def update ( self , sock ) :
        date = time.time()
        self.extreme_clean()
        for hostname in self.hostnames(date) :
            for metric in self.metric_list :
                data = collectd(sock, "%s/%s" % (hostname,metric))
                if data :
                    self[date] = data.split('=')[1]

        self.submit(socket, 60*self.window)
        if len(self.last(60*self.window)) and self.logfile :
            with open( '%s.out' % self.elbname , 'a+' ) as fd :
                fd.write( "%s %14.2f %s\n" % ( datetime.datetime.now() , date , self.dump(60*self.window) ) )

    def hostnames ( self , date ) :
        instances = boto.ec2.elb.connect_to_region("eu-west-1") \
                                .get_all_load_balancers([self.elbname])[0] \
                                .get_instance_health()
        in_service = [ i.instance_id for i in instances if i.state == 'InService' ]
        if self.count != len(instances) or self.healthy != len(in_service):
            self.date = date
        self.count = len(instances)
        self.healthy = len(in_service)
        instances = boto.ec2.connect_to_region("eu-west-1") \
                       .get_only_instances(in_service)
        return [ str(i.private_dns_name.split('.')[0]) for i in instances ]

    def __setitem__ ( self , key , valstr ) :
        if self.check_date( key ) :
            aggregated_metric.__setitem__( self , key , valstr )

    def check_date ( self , date ) :
        return date - self.date > 70

    def average ( self , interval ) :
        if not self.healthy :
            return float('nan')
        return aggregated_metric.average( self , interval ) / self.healthy

    def sigma ( self , interval ) :
        if not self.healthy :
            return float('nan')
        return aggregated_metric.sigma( self , interval ) / self.healthy

    def two_sigma ( self , interval ) :
        if not self.healthy :
            return float('nan')
        return aggregated_metric.two_sigma( self , interval ) / self.healthy

    def sigma_down ( self , interval ) :
        if not self.healthy :
            return float('nan')
        return aggregated_metric.sigma_down( self , interval ) / self.healthy

    def one_tenth ( self , interval ) :
        if not self.healthy :
            return float('nan')
        return aggregated_metric.one_tenth( self , interval ) / self.healthy

    def five_mins ( self , interval ) :
        if not self.healthy :
            return float('nan')
        return aggregated_metric.five_mins( self , interval ) / self.healthy

    def nodes_out ( self , interval ) :
        if not self.healthy :
            return self.count
        return self.count - self.healthy

    def submit ( self , sock, interval ) :
        output  = '"%s/%s/%s" ' % ( self.elbname , self.alias , self.__class__.__name__ )
        output += "%s:%f:%f:%f:%f" % ( self.tstamp , self.average(interval) , self.sigma(interval) , self.one_tenth(interval) , self.five_mins(interval) )
        output += ":%s:%s" % ( self.nodes_out(interval) , self.count )
        collectd(sock, output, command='PUTVAL')

    def dump ( self , interval ) :
        output = "%s %s " % ( self.nodes_out(interval) , self.count )
        output += aggregated_metric.dump( self , interval )
        return output

    def __str__ ( self ) :
        return "elb: %s/%s , %s" % ( self.healthy , self.count , aggregated_metric.__str__(self) )

def cooldown ( alarm , period , msg=None ) :
    lockfile = "/tmp/%s.lock" % alarm
    if os.path.isfile( lockfile ) :
        stat = os.stat( lockfile )
        if time.time() - stat.st_mtime < period :
            return True
    if not msg :
        msg = "%d cooldown activated" % time.time()
    with open( lockfile , 'w' ) as fd :
        fd.write( msg )

def get_action ( action , metric_name , alarm ) :
    action , param = action.split(':',1)
    if action == 'autoscale' :
        return autoscale_action( metric_name , alarm , param )
    elif action == 'http' :
        return http_action( metric_name , alarm , param )
    elif action == 'post' :
        return post_action( metric_name , alarm , param )
    raise Exception( "ERROR: action '%s' unknown" % action )

class action :

    def __init__ ( self , metric_name , alarm ) :
        self.name = "%s-%s" % ( metric_name , alarm.name )
        self.period = alarm.cooldown
        self.metric = metric_name
        self.alarm = alarm.name

    def run ( self , groupname ) :
        if not self.cooldown() :
            self.thread = threading.Thread(target=self.execute, args=( groupname ,) )
            self.thread.start()

    def cooldown( self ) :
        return cooldown( self.name , self.period )

class autoscale_action ( action ) :

    name = 'autoscale'

    def __init__ ( self , metric_name , alarm_name , policy ) :
        action.__init__( self , metric_name , alarm_name )
        self.policy = policy

    def execute ( self , groupname ) :
        autoscale = boto.ec2.autoscale.connect_to_region('eu-west-1')
        try :
            autoscale.execute_policy( self.policy , as_group=groupname , honor_cooldown=1 )
        except boto.exception.BotoServerError , ex :
            os.sys.stdout.write( "WARNING : autoscaling error '%s': %s\n" % ( ex.error_code , ex.message ) )

    def __str__ ( self ) :
        return "AWS autoscale action (policy %s)" % self.policy

class http_action ( action ) :

    name = 'http'

    def __init__ ( self , metric_name , alarm_name , url ) :
        action.__init__( self , metric_name , alarm_name )
        self.url = "http:%s" % url

    def execute ( self , groupname ) :
        url = self.url.format( groupname=groupname , production=fever_config()['production'] )
        try :
            res = urllib2.urlopen(url)
            if res.getcode() != 200 :
                os.sys.stdout.write( "WARNING : %s returned '%s'\n" % ( url , res.getcode() ) )
        except urllib2.URLError , ex :
            os.sys.stdout.write( "WARNING : cannot contact '%s' : %s\n" % ( url , ex.reason ) )

    def __str__ ( self ) :
        return "GET action (%s)" % self.url

class post_action ( action ) :

    name = 'post'

    payload = """{
  "Type" : "watchd",
  "id":"%s",
  "tstamp":"%s",
  "validated" : true,
  "metric" : "%s",
  "alarm" : "%s"
}"""

    def __init__ ( self , metric_name , alarm_name , url ) :
        action.__init__( self , metric_name , alarm_name )
        self.url = "http://%s/" % url

    def execute ( self , groupname ) :
        data = self.payload % ( uuid.uuid1() , datetime.datetime.now() , groupname , self.alarm )
        try :
            res = urllib2.urlopen(self.url, data)
            if res.getcode() not in ( 200 , 202 ) :
                os.sys.stdout.write( "WARNING : %s returned '%s'\n" % ( res.geturl() , res.getcode() ) )
        except urllib2.URLError , ex :
            os.sys.stdout.write( "WARNING : cannot contact '%s' : %s\n" % ( self.url , ex.reason ) )

    def __str__ ( self ) :
        return "POST action (%s)" % self.url
