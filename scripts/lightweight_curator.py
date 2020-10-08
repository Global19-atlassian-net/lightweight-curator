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
index_name_prefixes = os.getenv("INDEX_NAME_PREFIXES", "infra-,app-,audit-")
dry_run = bool(os.getenv("DRY_RUN", "false"))

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
        sys.exit(1)

    msg = {
        "level": level,
        "message": message
    }

    if extra is not None:
        msg["extra"] = extra
    print(json.dumps(msg))

    return

def env_validation(index_name_prefixes, elasticsearch_host):
    """
    Initial validation of environment variables.
    """
    if index_name_prefixes == "":
        log(log_err, "Index name prefix is empty (INDEX_NAME_PREFIXES='')")
        sys.exit(1)

    if elasticsearch_host == "":
        log(log_err, "Elasticsearch host is empty (ELASTICSEARCH_HOST='')")
        sys.exit(1)

    return

def es_connect_args(host):
    """
    Returns class with Elasticsearch arguments which will be used for api calls.
    """
    if host == "":
        log(log_err, "Elasticsearch host is empty (ELASTICSEARCH_HOST='')")
        sys.exit(1)

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

    return es

def get_max_allowed_size(es, percentage_threshold):
    """
    Returns a integer which is calculated as maximal allowed size. We think of <percentage_value_input> as 100% of our total available storage limit.
    """
    i = 0
    data = es.cluster.client.cat.allocation(h='disk.total', bytes='b')
    for node in data.splitlines():
        i = i + int(node)

    max_allowed_size = int( (percentage_threshold * i) / 100.0 )

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
    class indices_struct:
      def __init__(self, name, size, creation_date):
        self.name = name
        self.size = size
        self.creation_date = creation_date

    """
    Appends all indice into the list with their name, size and creation_date values.
    """
    indices = []
    for index_name_prefixes in index_name_prefixes_list:
        for name in es.indices.get_alias(index=index_name_prefixes + "*").keys():
            size = int(get_first_item(es.indices.stats(index=name)['indices'][name]['total']['store']))
            creation_date = int(es.indices.get(index=name)[name]['settings']['index']['creation_date'])
            indices.append(indices_struct(name, size, creation_date))

    """
    Returns list of indices which are above threshold limit.
    """
    indices_to_delete = []
    indices_size_counter = 0
    for index in sorted(indices, key=lambda x: x.creation_date, reverse=True):
        expected_size = index.size + sum_disk_usage
        def index_smaller_then_max_allowed_size(indices_size_counter, expected_size, max_allowed_size):
            if indices_size_counter < max_allowed_size and expected_size < max_allowed_size:
                return True
        if index_smaller_then_max_allowed_size(indices_size_counter, expected_size, max_allowed_size):
            log(log_info, "Do not add into actionable list: '{index}', summed disk usage is {usage} B and disk limit is {limit} B".format(
                index=index.name, usage=indices_size_counter, limit=max_allowed_size))
            indices_size_counter += index.size
        else:
            log(log_info, "Add into actionable list: '{index}', summed disk usage is {usage} B and disk limit is {limit} B".format(
                index=index.name, usage=indices_size_counter, limit=max_allowed_size))
            indices_to_delete.append(index.name)

    return indices_to_delete

def delete_indices(es, indices_to_delete):
    """
    Delete actionable indices pasted from get_actionable_indices() function.
    """
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
    global elasticsearch_host
    global percentage_threshold
    global dry_run

    # Initial validation of environment variables.
    env_validation(index_name_prefixes, elasticsearch_host)

    # Index name prefixes from comma-separated string.
    index_name_prefixes_list = index_name_prefixes.split(',')

    # Pass elasticsearch connect arguments.
    es = es_connect_args(elasticsearch_host)

    log(log_info, "Searching for indices which are above {percentage}% threshold from host '{host}'".format(
        host=elasticsearch_host,
        percentage=percentage_threshold
    ))

    # Get list of actionable indices.
    indices_to_delete = get_actionable_indices(es, get_max_allowed_size(es, percentage_threshold), index_name_prefixes_list)

    # For development purpose.
    if dry_run:
        print(indices_to_delete)
        sys.exit(1)

    # Delete actionable indices.
    delete_indices(es, indices_to_delete)

if __name__ == "__main__":
    main()
