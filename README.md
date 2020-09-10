# Lightweight Curator for Elasticsearch

Simplistic cousin of [Elasticsearch curator](https://github.com/elastic/curator), created for one purpose only:

Delete log indices created by fluentd which are above specified **percentage threshold** and older than a certain number of days.

## Configuration

The following environment variables can be used for configuration:

- `ELASTICSEARCH_HOST`: Name of the host that's running elasticsearch (default: `elasticsearch.openshift-logging:9200`)
- `RETENTION_DAYS`: Number of days to keep indices for (default: `14`)
- `PERCENTAGE_THRESHOLD`: Max allowed size for indices on disk (default: `80`)

## Prerequisite

- OpenShift user is able to create pods in *openshift-logging* namespace.

## Deployment

Result of running following commands would be newly created *lightweight-curator* pod in *openshift-logging* namespace. From within this pod I would then run curator script.

    $ oc apply src/cronjob.yaml -n openshift-logging

    $ oc rsh lightweight-curator-xxxx-yyyy

    $ python /home/curator.py
