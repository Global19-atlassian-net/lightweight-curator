# Lightweight Curator for Elasticsearch

Simplistic cousin of [Elasticsearch curator](https://github.com/elastic/curator), created for one purpose only:

Delete log indices created by fluentd which are above 80% of total threshold calculated from total disk size.

## Prerequisite

- OpenShift user is able to create pods in *openshift-logging* namespace.

## Deployment

Result of running following commands would be newly created *lightweight-curator* pod in *openshift-logging* namespace. From within this pod you can run lightweight-curator script.

    $ oc apply src/cronjob.yaml -n openshift-logging

    $ oc rsh lightweight-curator-xxxx-yyyy

    $ python /home/lightweight-curator.py
