
from watchd import actions

from fevertools import elb_group

import math

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
        self.action = actions.get( params['action'] , metric.name , self )

    def check_thresholds ( self , metric , interval ) :
        for statistic in self.statistics :
            methods = [ getattr(metric, s) for s in statistic['methods'] ]
            values = [ method(interval) for method in methods ]
            if [ v for v in values if not math.isnan(v) and cmp(v, abs(statistic['threshold'])) == sign(statistic['threshold']) ] :
                self.action.run( elb_group(metric.elbname) )
                return True
        return False

