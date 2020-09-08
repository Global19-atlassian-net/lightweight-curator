# Lightweight Curator for Elasticsearch

Simplistic cousin of [Elasticsearch curator](https://github.com/elastic/curator), created for one purpose only:

Delete log indices created by fluentd which are above specified PERCENTAGE_THRESHOLD and older than a certain number of days.

## Configuration

The following environment variables can be used for configuration:

- `ELASTICSEARCH_HOST`: Name of the host that's running elasticsearch (default: `elasticsearch.openshift-logging.svc.cluster.local:9200`)
- `RETENTION_DAYS`: Number of days to keep indices for (default: `14`)
- `PERCENTAGE_THRESHOLD`: Max allowed size for indices on disk (default: `80`)
