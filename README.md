# Lightweight Curator for Elasticsearch

Simplistic cousin of [Elasticsearch curator](https://github.com/elastic/curator), created for one purpose only:

Delete log indices created by fluentd which are above threshold of 80% calculated from total disk size.

## Prerequisite

- OpenShift user is able to create pods in *openshift-logging* namespace.

## Deployment

Result of running following commands would be newly created *lightweight-curator* pod in *openshift-logging* namespace. From within this pod you can run lightweight_curator.py script.

    $ oc apply src/cronjob.yaml -n openshift-logging

    $ oc rsh lightweight-curator-xxxx-yyyy

    $ python /home/lightweight_curator.py
