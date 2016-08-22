
# watchd

watchd is a metric monitoring daemon wich on a first glance acts as an aggregator
of collectd metrics. It allows to define for each metric a set of thresholds that will
trigger specific actions when crossed.

It was initially developed as a kind of replacement for AWS cloudwatch service, with
a larger set of statistics function to apply to it (quantiles, linear predictors ...)

## License

Source code is licensed under Apache license (version 2.0)

