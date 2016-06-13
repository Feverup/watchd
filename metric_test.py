#!/usr/bin/python

import fevertools

stream1 = "1465835356 9.220013e+01 8.465013e+01 9.305006e+01 8.128337e+01 9.184971e+01 8.361654e+01 8.761658e+01 7.796592e+01 8.441707e+01 7.660061e+01"
stream2 = "1465835356 8.923330e+01 8.089996e+01 8.853328e+01 7.746370e+01 8.991515e+01 8.106831e+01 8.345048e+01 7.833369e+01 8.696770e+01 8.078445e+01"
stream3 = "1465835416 8.719994e+01 8.958326e+01 8.764982e+01 8.616683e+01 8.005028e+01"
stream4 = "1465835597 8.936671e+01 8.118335e+01 8.528335e+01 7.461678e+01 8.991679e+01"

class test_metric ( fevertools.aggregated_metric ) :

    @classmethod
    def from_datastream ( cls , *streams ) :
        obj = cls()
        for stream in streams :
            tstamp , values = stream.split(None,1)
            tstamp = int(tstamp)
            for val in values.split() :
                obj[tstamp] = val
                tstamp += 60
        return obj

if __name__ == "__main__" :
    metric = test_metric.from_datastream ( stream1 , stream2 , stream3 , stream4 )
    t_predict = 1465835837 + 300
    print metric
    print metric.predict( t_predict , False )

