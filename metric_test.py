#!/usr/bin/python

import fevertools
import sys

stream1 = "1465835356 9.220013e+01 8.465013e+01 9.305006e+01 8.128337e+01 9.184971e+01 8.361654e+01 8.761658e+01 7.796592e+01 8.441707e+01 7.660061e+01"
stream2 = "1465835356 8.923330e+01 8.089996e+01 8.853328e+01 7.746370e+01 8.991515e+01 8.106831e+01 8.345048e+01 7.833369e+01 8.696770e+01 8.078445e+01"
stream3 = "1465835416 8.719994e+01 8.958326e+01 8.764982e+01 8.616683e+01 8.005028e+01"
stream4 = "1465835416 8.374998e+01 8.623329e+01 8.074983e+01 8.426661e+01 7.838331e+01"

class test_metric ( fevertools.aggregated_metric ) :

    @classmethod
    def from_datastream ( cls , config , *streams ) :
        obj = cls(config)
        for stream in streams :
            tstamp , values = stream.split(None,1)
            tstamp = int(tstamp)
            for val in values.split() :
                obj[tstamp] = val
                tstamp += 60
        return obj

tol = 1e-4

if __name__ == "__main__" :
    config = { 'metric_list':'' , 'statistics':'' , 'action':'autoscale:' }
    metric = test_metric.from_datastream ( config , stream1 , stream2 , stream3 , stream4 )
    t_predict = 1465835837 + 300
    if len(sys.argv) > 1 :
        print 'y <- matrix(nrow=0, ncol=2)'
        for date in metric.keys() :
            for val in metric[date] :
                print 'y <- rbind( y , c( %s , %s ) )' % ( date , val )
        print 'y <- data.frame(y)'
        print 'fit <- lm( X2 ~ X1 , data=y )'
        print 'par(mfrow=c(2,2))'
        print 'plot(fit)'
        print 'predict(fit, newdata=data.frame(X1=c(%s)))' % (t_predict)
        print
    predict = metric.predict( t_predict , False )
    if abs( predict - 76.77483 ) > tol :
        print "Wrong prediction : %s vs. 76.77483" % predict

