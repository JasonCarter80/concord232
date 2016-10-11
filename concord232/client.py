import json
import requests
import time


class Client(object):
    def __init__(self, url):
        self._url = url
        self._session = requests.Session()
        self._last_event_index = 0

    def list_zones(self):
        r = self._session.get(self._url + '/zones')
        try:
            return r.json['zones']
        except TypeError:
            return r.json()['zones']

    def list_partitions(self):
        r = self._session.get(self._url + '/partitions')
        try:
            return r.json['partitions']
        except TypeError:
            return r.json()['partitions']

    def arm(self, armtype='auto'):
        if armtype not in ['stay', 'exit', 'auto']:
            raise Exception('Invalid arm type')
        r = self._session.get(
            self._url + '/command',
            params={'cmd': 'arm',
                    'type': armtype})
        return r.status_code == 200

    def disarm(self, master_pin):
        r = self._session.get(
            self._url + '/command',
            params={'cmd': 'disarm',
                    'master_pin': master_pin})
        return r.status_code == 200

    def send_keys(self, keys, group=False):
        r = self._session.get(
            self._url + '/command',
            params={'cmd': 'keys',
                    'keys': keys,
                    'group': group})
        return r.status_code == 200

    def get_version(self):
        r = self._session.get(self._url + '/version')
        if r.status_code == 404:
            return '1.0'
        else:
            return r.json()['version']
