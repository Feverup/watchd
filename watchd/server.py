
import socket

def server ( sock , sockfile ) :
    # https://pymotw.com/2/socket/uds.html

    sock.bind(sockfile)
    sock.listen(1)

    while True :
        connection, client_address = sock.accept()

        try:

            # Receive the data in small chunks and retransmit it
            while True:
                data = connection.recv(256)
                if data:
                    items = data[:-1].split()
                    if items[0] == "WHAT" :
                        if len(items) == 2 :
                            for metric in metrics :
                                if metric.elbname == items[1] :
                                    connection.sendall("alarms %s\n" % ", ".join([a.name for a in metric.alarms]))
                                    break
                            else :
                                connection.sendall("error bad metric\n")
                        else :
                            connection.sendall("metrics %s\n"%", ".join([m.name for m in metrics]))
                    elif items[0] == "KILL" :
                        connection.sendall("stopping\n")
                        state['serving'] = False
                        break
                    elif items[0] == "GETVAL" and len(items) == 2 :
                        metric = [ m for m in metrics if m.elbname == items[1] ]
                        if len(metric) == 1 :
                            metric = metric[0]
                            interval = 60 * metric.window
                            avg , std = metric.mean(interval)
                            connection.sendall("value %s %s\n"%(avg,std))
                        else :
                            connection.sendall("error bad metric\n")
                    elif items[0] == "GETTHRESHOLD" and len(items) == 3 :
                        metric = [ m for m in metrics if m.elbname == items[1] ]
                        if len(metric) == 1 :
                            metric = metric[0]
                            for alarm in metric.alarms :
                                if alarm.name == items[2] :
                                    threshold = max([statistic['threshold'] for statistic in alarm.statistics])
                                    connection.sendall("threshold %s\n"%threshold)
                                    break
                            else :
                                connection.sendall("error bad alarm\n")
                        else :
                            connection.sendall("error bad metric\n")
                    elif items[0] == "STATE" and len(items) == 3 :
                        metric = [ m for m in metrics if m.elbname == items[1] ]
                        if len(metric) == 1 :
                            metric = metric[0]
                            interval = 60 * metric.window
                            for alarm in metric.alarms :
                                if alarm.name == items[2] :
                                    if metric.full(alarm, interval) :
                                        connection.sendall("state UNKNOWN\n")
                                    elif alarm.check_thresholds(metric, interval) :
                                        connection.sendall("state WARNING\n")
                                    else :
                                        connection.sendall("state OK\n")
                                    break
                            else :
                                connection.sendall("error bad alarm\n")
                        else :
                            connection.sendall("error bad metric\n")
                    else :
                        connection.sendall("echo: %s\n"%data)
                else:
                    break

        finally:
            # Clean up the connection
            connection.close()

