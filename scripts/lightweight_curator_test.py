# -*- coding: utf-8 -*-

import elasticsearch
import unittest
from datetime import datetime
from elasticmock_extra import elasticmock, behaviour

INDEX_NAME = 'test_index'
DOC_TYPE = 'doc-Type'
BODY = {
    'author': 'tgabriel',
    'text': 'Elasticsearch: cool. bonsai cool.',
    'timestamp': datetime.now(),
}

class TestElasticmock(unittest.TestCase):

    @elasticmock
    def setUp(self):
        self.es = elasticsearch.Elasticsearch(hosts=[{'host': 'localhost', 'port': 9200}])

    def tearDown(self):
        behaviour.disable_all()

class TestCluster(TestElasticmock):

    def test_should_return_internal_server_error_when_simulate_server_error_is_true(self):
        behaviour.server_failure.enable()
        data = self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        expected = {
            'status_code': 500,
            'error': 'Internal Server Error'
        }

        self.assertDictEqual(expected, data)

    def test_should_return_health(self):
        health_status = self.es.cluster.health()

        expected_health_status = {
            'cluster_name': 'testcluster',
            'status': 'green',
            'timed_out': False,
            'number_of_nodes': 1,
            'number_of_data_nodes': 1,
            'active_primary_shards': 1,
            'active_shards': 1,
            'relocating_shards': 0,
            'initializing_shards': 0,
            'unassigned_shards': 1,
            'delayed_unassigned_shards': 0,
            'number_of_pending_tasks': 0,
            'number_of_in_flight_fetch': 0,
            'task_max_waiting_in_queue_millis': 0,
            'active_shards_percent_as_number': 50.0
        }

        self.assertDictEqual(expected_health_status, health_status)

    def test_should_return_allocation(self):
        allocation = self.es.cluster.client.allocation()

        expected_allocation = {
            'shards': 1,
            'disk.indices': '260b',
            'disk.used': '47.3gb',
            'disk.avail': '43.4gb',
            'disk.total': '100.7gb',
            'disk.percent': '46',
            'host': '127.0.0.1',
            'ip': '127.0.0.1',
            'node': 'CSUXak2'
        }

        self.assertDictEqual(expected_allocation, allocation)

class TestIndices(TestElasticmock):

    def test_should_return_indices_stats(self):
        get_stats = self.es.indices.stats(INDEX_NAME)["total"]["store"]
        expected_stats = {'size_in_bytes': 15521849910}

        self.assertEqual(expected_stats, get_stats)


    def test_should_return_index(self):
        get_index = self.es.indices.get(INDEX_NAME)[INDEX_NAME]['settings']['index']['creation_date']
        expected_get_index = '1429308615170'

        self.assertEqual(expected_get_index, get_index)

    def test_should_return_aliases(self):
        get_alias = self.es.indices.get_alias("infra-*").keys()
        expected_get_alias = {
            "infra-xyz-13-11-2020",
            "infra-xyz-20-10-2021"
        }

        self.assertEqual(expected_get_alias, get_alias)

    def test_should_delete_index(self):
        self.assertFalse(self.es.indices.exists(INDEX_NAME))

        self.es.indices.create(INDEX_NAME)
        self.assertTrue(self.es.indices.exists(INDEX_NAME))

        self.es.indices.delete(INDEX_NAME)
        self.assertFalse(self.es.indices.exists(INDEX_NAME))

    def test_should_delete_inexistent_index(self):
        self.assertFalse(self.es.indices.exists(INDEX_NAME))

        self.es.indices.delete(INDEX_NAME)
        self.assertFalse(self.es.indices.exists(INDEX_NAME))
