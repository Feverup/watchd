
from fevertools import fever_config

import uuid
import threading
import datetime
import time
import os
import urllib2

def get ( action , metric_name , alarm ) :
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

    def cooldown( self , msg=None ) :
        lockfile = "/tmp/%s.lock" % self.name
        if os.path.isfile( lockfile ) :
            stat = os.stat( lockfile )
            if time.time() - stat.st_mtime < self.period :
                return True
        if not msg :
            msg = "%d cooldown activated" % time.time()
        with open( lockfile , 'w' ) as fd :
            fd.write( msg )


class autoscale_action ( action ) :

    name = 'autoscale'

    def __init__ ( self , metric_name , alarm_name , count ) :
        action.__init__( self , metric_name , alarm_name )
        self.count = count

    def execute ( self , groupname ) :
        url = "http://mgmnt.feverup.com:8000/autoscale/%s/%s" % ( groupname , self.count )
        try :
            res = urllib2.urlopen(url)
            if res.getcode() != 201 :
                os.sys.stdout.write( "WARNING : %s returned '%s'\n" % ( url , res.getcode() ) )
        except Exception , ex :
            os.sys.stdout.write( "WARNING : scaling error : %s\n" % ex )

    def __str__ ( self ) :
        return "Scale action (#%s instances)" % self.count

class http_action ( action ) :

    name = 'http'

    def __init__ ( self , metric_name , alarm_name , url ) :
        action.__init__( self , metric_name , alarm_name )
        self.url = "http:%s" % url

    def execute ( self , groupname ) :
        url = self.url.format( groupname=groupname , production=fever_config('production') )
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

