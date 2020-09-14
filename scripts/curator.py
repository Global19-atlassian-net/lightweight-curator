# coding: utf8

from datetime import date
from datetime import timedelta
from elasticsearch import Elasticsearch
import json
import os
import subprocess
import sys

# read environment variables
elasticsearch_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch:9200")
percentage_threshold = int(os.getenv("PERCENTAGE_THRESHOLD", "80"))
retention_days = int(os.getenv("RETENTION_DAYS", "2"))
index_name_prefixes = os.getenv("INDEX_NAME_PREFIXES", "infra-,app-,audit-")

# types of logs
log_info = "info"
log_err = "error"
log_types = [log_info, log_err]

def log(level, message="", extra=None):
    """
    Prints a JSON-formatted log message
    """
    if level not in log_types:
        print("Invalid level provided")
        return

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
        log(log_err, "Retention period in days is too short (RETENTION_DAYS='{days}')".format(days=retention_days))
        sys.exit(1)

    if index_name_prefixes == "":
        log(log_err, "Index name prefix is empty (INDEX_NAME_PREFIXES='')")
        sys.exit(1)

    if elasticsearch_host == "":
        log(log_err, "Elasticsearch host is empty (ELASTICSEARCH_HOST='')")
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
        log(log_err, "Could not connect to elasticsearch", extra={
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

def get_first_item(a_dict={}):
    values_view = a_dict.values()
    value_iterator = iter(values_view)
    first_value = next(value_iterator)
    return first_value

def get_actionable_indices(es, max_allowed_size, index_name_prefixes_list):
    """
    Returns a list of actionable indices based on percentage size and age.
    """
    size_counter = 0
    for index_name_prefixes in index_name_prefixes_list:
        # Prepare dictionary of indices with their size and creation_date values.
        data = {}
        for name in es.indices.get_alias(index=index_name_prefixes + "*").keys():
            size = int(get_first_item(es.indices.stats(index=name)['indices'][name]['total']['store']))
            creation_date = int(es.indices.get(index=name)[name]['settings']['index']['creation_date'])
            data.update({name: {'size': size, 'creation_date': creation_date}})

        def extract_creation_date_from_dict_item(item):
            """
            extract_creation_date_from_dict_item recieves an item in the format of:
            ("index_name", { "size" : size, "creation_date" : date})

            the return value is the value inside the "creation_date" field
            """
            index_of_value = 1
            return item[index_of_value]["creation_date"]

        # Output are one or more indices which are above the <percentage_value_input> threshold and are supposed to be deleted.
        indices_to_delete = []
        for index_name, index_info in sorted(data.items(), key=extract_creation_date_from_dict_item):
            extracted_size = index_info["size"]
            if size_counter < max_allowed_size:
                size_counter += extracted_size
                log(log_info, "Removed from actionable list: '{indice}', summed disk usage is {usage} B and disk limit is {limit} B".format(
                    indice=index_name, usage=size_counter, limit=int(max_allowed_size)))
            else:
                indices_to_delete.append(index_name)
                log(log_info, "Remains in actionable list: '{indice}', summed disk usage is {usage} B and disk limit is {limit} B".format(
                    indice=index_name, usage=size_counter, limit=int(max_allowed_size)))

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
        log(log_err, "Could not list indices for '{s}'".format(s=searchterm), extra={
            "exception": e
        })
        sys.exit(1)

    if len(indices) == 0:
        log(log_info, "No indices with prefix '{prefix}' found".format(prefixes=index_name_prefixes))
        sys.exit(1)

    # Delete indices.
    for indice in indices_to_delete:
        try:
            es.indices.delete(index=indice)
            log(log_info, "Deleted indice '{s}'".format(s=indice))
        except Exception as e:
            log(log_err, "Error deleting indice '{s}'".format(s=indice), extra={
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

        log(log_info, "Removing indices with name format '{prefix}' which are above {percentage} threshold and older than {days} days from host '{host}'".format(
            prefix=index_name_prefixes,
            days=retention_days,
            host=elasticsearch_host,
            percentage=percentage_threshold
        ))

        # Initiate new elasticsearch instance.
        es = es_connect(elasticsearch_host)

        # List of actionable indices to be deleted.
        indices_to_delete = get_actionable_indices(es, get_max_allowed_size(es, percentage_threshold), index_name_prefixes_list)
        print(indices_to_delete)

        # For development purpose, exitting code before indice deletion.
        sys.exit(1)

        # Delete indices.
        delete_indices(es, indices_to_delete, index_name_prefixes)

if __name__ == "__main__":
    main()
