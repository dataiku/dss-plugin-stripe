import json
from dataiku.connector import Connector
import requests
from requests.auth import HTTPBasicAuth


def log(msg):
    print('Stripe plugin - %s' % msg)


def iterate_dict(dictionary, parents=[]):
    """
    This function iterates over one dict and returns a list of tuples: (list_of_keys, value)
    Usefull for looping through a multidimensional dictionary.
    """

    ret = []
    for key, value in dictionary.items():
        if isinstance(value, dict):
            ret.extend(iterate_dict(value, parents + [key]))
        else:
            ret.append((parents + [key], value))
    return ret


def flatten_json(row_obj):
    """
    Iterates over a JSON to tranfsorm each element into a column.
    Example:
    {'a': {'b': 'c'}} -> {'a.b': 'c'}
    """
    row = {}
    for keys, value in iterate_dict(row_obj):
        row[".".join(keys)] = value if value is not None else ''
    return row


class MyConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        self.api_key = self.config.get("api_key", "")
        self.object = self.config.get("object")
        self.custom_object = self.config.get("custom_object")
        self.result_format = self.config.get("result_format", "readable")
        if self.object == "other" and self.custom_object:
            self.object = self.custom_object


    def get_read_schema(self):
        # We don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None


    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                            partition_id=None, records_limit = -1):
        has_more = True
        params = {
            "limit": 100
        }
        log("Start generate_rows")
        while has_more:
            resp = requests.get(
                "https://api.stripe.com/%s" % self.object,
                auth=HTTPBasicAuth(self.api_key, ''),
                params=params
            )
            log(resp.url)
            log(resp.status_code)
            try:
                data = resp.json()
            except Exception as e:
                data = {}
            if "error" in data and "message" in data["error"]:
                raise Exception("Stripe API error. %s" % data["error"]["message"])
            resp.raise_for_status()
            has_more = data.get("has_more", False)
            last_id = None
            for row in data.get("data", []):
                last_id = row["id"]
                if self.result_format == 'json':
                    yield { "data" : json.dumps(row) }
                else:
                    yield flatten_json(row)
            if has_more:
                params["starting_after"] = last_id


    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                         partition_id=None):
        raise Exception("Unimplemented")


    def get_records_count(self, partitioning=None, partition_id=None):
        raise Exception("unimplemented")
