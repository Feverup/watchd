
# IN MINUTES
SLEEP_TIME = 5
PRED_TIME = 2 * SLEEP_TIME


class Command(BaseCommand):

    delta = 100  # step for speed changes
    latency = (None, 0, -1)
    db_cpu = (None, 0, -1)
    front_cpu = (None, 0, -1)

    # reliability thresholds
    latency_threshold = 3
    db_cpu_threshold = 70
    front_cpu_threshold = 90

    # trace cloudwatch latency
    latency_tstamp = None
    latency_value = -1
    latency_ticks = 0

    def extrapolate_metric(self, values):
        if len(values) < 2:
            return values[0]['Timestamp'], values[0]['Average'], -1
        metrics = {}
        for value in values:
            metrics[int(value['Timestamp'].strftime("%s"))] = (value['Timestamp'], value['Average'])
        datelist = sorted(metrics.keys())
        date0, date1 = datelist[-2:]
        rate = (metrics[date1][1] - metrics[date0][1]) / (date1 - date0)
        prediction = metrics[date1][1] + rate * PRED_TIME
        return metrics[date1][0], metrics[date1][1], prediction

    def check_reliability(self, elb_instances):
        def get_latency():
            latency = self.aws.get_metric_statistics(
                period=60,
                start_time=datetime.now() - timedelta(minutes=3),
                end_time=datetime.now() + timedelta(minutes=1),
                metric_name='Latency',
                namespace='AWS/ELB',
                statistics=['Average'],
                dimensions={u'Service': [u'ELB']}
            )
            output = self.extrapolate_metric(latency)
            if self.latency_tstamp != output[0]:
                self.latency_tstamp = output[0]
                self.latency_ticks = 0
            self.latency_ticks += SLEEP_TIME
            # Usually, only the two first values are bad, but three wrongs happen from time to time
            if self.latency_ticks < 20:
                return output[0], self.latency_value, -1
            self.latency_value = output[1]
            return output

        def get_db_cpu():
            avg_cpu = self.aws.get_metric_statistics(
                period=60,
                start_time=datetime.now() - timedelta(minutes=4),
                end_time=datetime.now() + timedelta(minutes=1),
                metric_name='CPUUtilization',
                namespace='AWS/RDS',
                statistics=['Average'],
                dimensions={u'DatabaseClass': [u'db.r3.4xlarge']}
            )
            return self.extrapolate_metric(avg_cpu)

        def get_front_cpu(elb_instances):
            avg_cpu = []
            for instance_id in elb_instances:
                avg_cpu.extend(self.aws.get_metric_statistics(
                    period=60,
                    start_time=datetime.now() - timedelta(minutes=3),
                    end_time=datetime.now() + timedelta(minutes=1),
                    metric_name='CPUUtilization',
                    namespace='AWS/EC2',
                    statistics=['Average'],
                    dimensions={u'InstanceId': instance_id}))

            return self.linear_fit(avg_cpu, PRED_TIME)

        def exceed_thresholds():
            if self.latency[1] > self.latency_threshold or self.db_cpu[1] > self.db_cpu_threshold or self.front_cpu[1] > self.front_cpu_threshold:
                return True
            if self.latency[2] > self.latency_threshold:
                print("\nWARNING, threshold will be crossed for latency ; %s > %s\n" % (self.latency[2], self.latency_threshold))
            if self.db_cpu[2] > self.db_cpu_threshold:
                print("\nWARNING, threshold will be crossed for db_cpu ; %s > %s\n" % (self.db_cpu[2], self.db_cpu_threshold))
            if self.front_cpu[2] > self.front_cpu_threshold:
                print("\nWARNING, threshold will be crossed for front_cpu ; %s > %s\n" % (self.front_cpu[2], self.front_cpu_threshold))
            return False

        def update_data(elb_instances):
            self.latency = get_latency()
            self.db_cpu = get_db_cpu()
            self.front_cpu = get_front_cpu(elb_instances)

        update_data(elb_instances)

        if exceed_thresholds():
            print("[WARNING] Stoping...")

    def tick(self):

        def get_elb_instance(elb_name):
            load_balancer = self.elb.get_all_load_balancers([elb_name])[0]
            servicing = filter(lambda x: "InService" == x.state, load_balancer.get_instance_health())
            return map(lambda x: x.instance_id, servicing)

        elb_instances = get_elb_instance('front-balancer')
        self.check_reliability(elb_instances)

