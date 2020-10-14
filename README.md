# Lightweight Curator for Elasticsearch

Simplistic cousin of [Elasticsearch curator](https://github.com/elastic/curator), created for one purpose only:

Delete log indices created by fluentd which are above threshold of 80% calculated from total disk size.

## Prerequisite

- OpenShift user is able to create pods in *openshift-logging* namespace.

## Deployment

### Comand-line options

Dry_run prints the list of indices which would be passed onto deletion process, but do not execute.

    -d --debug
    -v --verbose
    -n --dry_run

### Manually running script for development purposed

Result of running following commands would be newly created *lightweight-curator* pod in *openshift-logging* namespace. From within this pod you can run *lightweight_curator.py* script.

    $ oc apply src/cronjob.yaml -n openshift-logging
    $ oc rsh deploy/lightweight-curator /bin/bash
    $ python /home/lightweight_curator.py
