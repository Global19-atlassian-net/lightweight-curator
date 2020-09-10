# coding: utf8

from datetime import date
from datetime import timedelta
from elasticsearch import Elasticsearch
import json
import os
import subprocess
import sys

# read environment variables
elasticsearch_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch.openshift-logging:9200")
percentage_threshold = os.getenv("PERCENTAGE_THRESHOLD", 80)
retention_days = int(os.getenv("RETENTION_DAYS", "2"))
index_name_prefixes = os.getenv("INDEX_NAME_PREFIXES", "infra-,app-,audit-")

def log(level="info", message="", extra=None):
    """
    Prints a JSON-formatted log message
    """
    msg = {
        "level": level,
        "message": message
    }
    if extra is not None:
        msg["extra"] = extra
    print(json.dumps(msg))

def env_validation(retention_days, index_name_prefixes, elasticsearch_host):
    """
    Initial validation of environment variables.
    """
    if retention_days < 1:
        log("error", "Retention period in days is too short (RETENTION_DAYS='{days}')".format(days=retention_days))
        sys.exit(1)

    if index_name_prefixes == "":
        log("error", "Index name prefix is empty (INDEX_NAME_PREFIXES='')")
        sys.exit(1)

    if elasticsearch_host == "":
        log("error", "Elasticsearch host is empty (ELASTICSEARCH_HOST='')")
        sys.exit(1)

    return

def es_connect(host):
    """
    Returns created Elasticsearch instance.
    """
    try:
        es = Elasticsearch(
            [host],
            # enable SSL
            use_ssl=True,
            # verify SSL certificates to authenticare
            verify_certs=True,
            # path to ca
            ca_certs='/home/data/ca',
            # path to key
            client_key='/home/data/key',
            # path to cert
            client_cert='/home/data/cert'
        )
    except Exception as e:
        log("error", "Could not connect to elasticsearch", extra={
            "exception": e
        })
        sys.exit(1)

    return es

def get_max_allowed_size(es, percentage_threshold):
    """
    Returns a integer which is calculated as maximal allowed size. We think of <percentage_value_input> as 100% of our total available storage limit.
    """
    i = 0
    data = es.cluster.client.cat.allocation(h='disk.total', bytes='b')
    for node in data.splitlines():
        i = i + int(node)

    max_allowed_size = (percentage_threshold * i) / 100.0

    return max_allowed_size

def get_actionable_indices(es, max_allowed_size, index_name_prefixes_list):
    """
    Returns a list of actionable indices based on percentage size and age.
    """
    i = 0
    for index_name_prefixes in index_name_prefixes_list:
        # Prepare dictionary of indices with their size and creation_date values.
        data = {}
        for name in es.indices.get_alias(index=index_name_prefixes + "*").keys():
            size = list(es.indices.stats(index=name)['indices'][name]['total']['store'].values())[0]
            creation_date = int(es.indices.get(index=name)[name]['settings']['index']['creation_date'])
            data.update({name: {'size': size, 'creation_date': creation_date}})

        # Output are one or more indices which are above the <percentage_value_input> threshold and are supposed to be deleted.
        indices_to_delete = []
        for k, v in sorted(data.items(), key=lambda e: e[1]["creation_date"]):
            for value in sorted(v.items()):
                if value[0] == "size":
                    if i < max_allowed_size:
                        i = i + int(value[1])
                        log("info", "Removed from actionable list: '{indice}', summed disk usage is {usage} B and disk limit is {limit} B".format(
                            indice=k, usage=i, limit=int(max_allowed_size)))
                    else:
                        indices_to_delete.append(k)
                        log("info", "Remains in actionable list: '{indice}', summed disk usage is {usage} B and disk limit is {limit} B".format(
                            indice=k, usage=value[1], limit=int(max_allowed_size)))
                else:
                    continue

    return indices_to_delete

def delete_indices(es, indices_to_delete, index_name_prefixes):
    """
    Delete actionable indices pasted from get_actionable_indices() function.
    """
    # Search existing indices for index_name_prefixes.
    searchterm = index_name_prefixes + "*"
    try:
        indices = es.indices.get(searchterm)
    except Exception as e:
        log("error", "Could not list indices for '{s}'".format(s=searchterm), extra={
            "exception": e
        })
        sys.exit(1)

    if len(indices) == 0:
        log("info", "No indices with prefix '{prefix}' found".format(prefixes=index_name_prefixes))
        sys.exit(1)

    # Delete indices.
    for indice in indices_to_delete:
        try:
            es.indices.delete(index=indice)
            log("info", "Deleted indice '{s}'".format(s=indice))
        except Exception as e:
            log("error", "Error deleting indice '{s}'".format(s=indice), extra={
                "exception": e
            })

    return

def main():
    global index_name_prefixes
    global retention_days
    global elasticsearch_host
    global percentage_threshold

    # Initial validation of environment variables.
    env_validation(retention_days, index_name_prefixes, elasticsearch_host)

    # Index name prefixes from space-separated string.
    index_name_prefixes_list = index_name_prefixes.split(',')

    # Iterate through all (infra-*, app-*, audit-*) indices and if needed delete those above <percentage_value_input> threshold.
    for index_name_prefixes in index_name_prefixes_list:

        log("info", "Removing indices with name format '{prefix}' which are above {percentage} threshold and older than {days} days from host '{host}'".format(
            prefix=index_name_prefixes,
            days=retention_days,
            host=elasticsearch_host,
            percentage=percentage_threshold
        ))

        # Initiate new elasticsearch instance.
        es = es_connect(elasticsearch_host)

        # List of actionable indices to be deleted.
        indices_to_delete = get_actionable_indices(es, get_max_allowed_size(es, int(percentage_threshold)), index_name_prefixes_list)
        print(indices_to_delete)

        # For development purpose, exitting code before indice deletion.
        sys.exit(1)

        # Delete indices.
        delete_indices(es, indices_to_delete, index_name_prefixes)

if __name__ == "__main__":
    main()
