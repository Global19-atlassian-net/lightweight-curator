# coding: utf8

from datetime import date
from datetime import timedelta
from elasticsearch import Elasticsearch
from hurry.filesize import size
import json
import os
import subprocess
import sys

# read environment variables
elasticsearch_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch.openshift-logging.svc.cluster.local:9200")
#percentage_threshold = os.getenv("PERCENTAGE_THRESHOLD", "80")
retention_days = int(os.getenv("RETENTION_DAYS", "2"))
index_name_prefix = os.getenv("INDEX_NAME_PREFIX", "infra- app- audit-")
index_name_timeformat = os.getenv("INDEX_NAME_TIMEFORMAT", "%Y.%m.%d")

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


def prepare_valid_indices_names(nameprefix, retention_days, timeformat):
    """
    Returns a set of valid index names to keep. These names are just user-friendly and NOT equal to actual indices names.
    """
    out = set()
    for n in range(retention_days):
        today = date.today() - timedelta(days=n)
        index_name_format = nameprefix + timeformat
        string = today.strftime(index_name_format)
        out.add(string)
    return out

def get_max_allowed_size(es):                                                                                            
    """                                                                                                                  
    Returns a integer which is calculated as maximal allowed size. We think of <percentage_value_input> as 100% of our total available storage limit.
    """                                                                                                                                              
    i = 0                                                                                                                                            
    data = es.cluster.client.cat.allocation(h='disk.total', bytes='b')                                                                               
    for node in data.splitlines():                                                                                       
        i = i + int(node)                                                                                                                            
                                                                                                                                                     
    max_allowed_size = (80 * i) / 100.0 
    
    return max_allowed_size

def get_actionable_indices(es, max_allowed_size):
    """
    Returns a list of actionable indices based on percentage size and age.                                                                           
    """
    # Prepare dictionary of indices with their size and creation_date values.
    data = {}
    for name in es.indices.get_alias(index=index_name_prefix + "*").keys():
        size = list(es.indices.stats(index=name)['indices'][name]['total']['store'].values())[0]
        creation_date = int(es.indices.get(index=name)[name]['settings']['index']['creation_date'])
        data.update({name: {'size': size, 'creation_date': creation_date}})

    # Output are one or more indices which are above the 80% threshold and are supposed to be deleted.                                               
    max_allowed_size = get_max_allowed_size(es)                                                                                                      
    print(max_allowed_size)                                                                                                                          
    to_delete = []                                                                                                                                   
    i = 0                                                                                                                                            
    for k, v in sorted(data.items(), key=lambda e: e[1]["creation_date"]):                                                                           
        for value in sorted(v.items()):                                                                                                              
            if value[0] == "size":                                                                                                                   
                if i < max_allowed_size:                                                                                                             
                    i = i + int(value[1])                                                                                                            
                else:                                                                                                                                
                    to_delete.append(k)                                                                                                              
            else:                                                                                                                                    
                continue                                                                                                                             
                                                                                                                                                     
    return to_delete 

def main():
    global index_name_prefix
    global retention_days
    global index_name_timeformat
    global elasticsearch_host

    # Initial validation

    if retention_days < 1:
        log("error", "Retention period in days is too short (RETENTION_DAYS=%d)" % retention_days)
        sys.exit(1)

    if index_name_prefix == "":
        log("error", "Index name prefix is empty (INDEX_NAME_PREFIX='')")
        sys.exit(1)

    if index_name_timeformat == "":
        log("error", "Index name time format is empty (INDEX_NAME_TIMEFORMAT='')")
        sys.exit(1)

    if elasticsearch_host == "":
        log("error", "Elasticsearch host is empty (ELASTICSEARCH_HOST='')")
        sys.exit(1)

    # index name prefixes from space-separated string
    index_name_prefix_list = index_name_prefix.split()

    for index_name_prefix in index_name_prefix_list:

        log("info", "Removing indices with name format '{prefix}{timeformat}' which are above 80% threshold and older than {days} days from host '{host}'".format(
            prefix=index_name_prefix,
            timeformat=index_name_timeformat,
            days=retention_days,
            host=elasticsearch_host,
        ))

        # Create a set of names with index names that should be kept for now
        valid = prepare_valid_indices_names(index_name_prefix, retention_days, index_name_timeformat)
        if len(valid) == 0:
            log("error", "The current index name settings yield no index names to retain")
            sys.exit(1)

        try:
            es = Elasticsearch(                                                                                                        
                ['elasticsearch.openshift-logging.svc.cluster.local:9200'],                                                
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

        searchterm = index_name_prefix + "*"

        # Get content of actionable list.
        limit = size(get_max_allowed_size(es))
        for indice in get_actionable_indices(es, get_max_allowed_size(es)):
            if 1 == 1:
                log("info", "Removed from actionable list: '{indice}', summed disk usage is '{usage}' and disk limit is '{limit}'.".format(indice, "xyz", limit))
            else:
                log("info", "Remains in actionable list: '{indice}', summed disk usage is '{usage}' and disk limit is '{limit}'.".format(indice, "xyz", limit))

        # For development purpose, exitting code bellow.
        sys.exit(1)

        try:
            indices = es.indices.get(searchterm)
        except Exception as e:
            log("error", "Could not list indices for '%s'" % searchterm, extra={
                "exception": e
            })
            sys.exit(1)

        if len(indices) == 0:
            log("info", "No indices found")
            sys.exit()

        for index in es.indices.get(searchterm):
            if index not in valid:
                try:
                    es.indices.delete(index=index)
                    log("info", "Deleted index %s" % index)
                except Exception as e:
                    log("error", "Error deleting index '%s'" % index, extra={
                        "exception": e
                    })


if __name__ == "__main__":
    main()
