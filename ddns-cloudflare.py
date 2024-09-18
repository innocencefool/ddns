#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import http.client
import json
import logging
import os
import socket

# permission needed: #zone:read #dns_records:edit
API_TOKEN = '########################################'
ZONE = 'cloudflare.com'
RECORD = 'api'

DOMAIN = '%s.%s' % (RECORD, ZONE)
DDNS_PATH = os.path.split(os.path.realpath(__file__))[0] + os.sep
DDNS_CONF = DDNS_PATH + 'ddns-cloudflare.conf'
DDNS_LOG = DDNS_PATH + 'ddns-cloudflare.log'


def load_conf():
    try:
        if os.path.exists(DDNS_CONF):
            with open(DDNS_CONF, 'r') as ddns_conf:
                dict_conf = json.load(ddns_conf)
                if dict_conf.get('zone_id') is not None \
                        and dict_conf.get('record_id') is not None \
                        and dict_conf.get('domain') is not None \
                        and dict_conf.get('domain') == DOMAIN:
                    return dict_conf.get('zone_id'), dict_conf.get('record_id')
        zone_id, record_id = save_conf()
        return zone_id, record_id
    except Exception as e:
        logging.error(e)
        zone_id, record_id = save_conf()
        return zone_id, record_id


def save_conf():
    zone_id, record_id = list_records()
    dump_conf(zone_id, record_id)
    return zone_id, record_id


def dump_conf(zone_id=None, record_id=None):
    try:
        dict_conf = {'domain': DOMAIN, 'zone_id': zone_id, 'record_id': record_id}
        with open(DDNS_CONF, 'w') as ddns_conf:
            json.dump(dict_conf, ddns_conf)
    except Exception as e:
        logging.error(e)


def restful_api(url, method='GET', data=None):
    try:
        headers = {'Authorization': 'Bearer %s' % API_TOKEN, 'Content-Type': 'application/json'}
        connection = http.client.HTTPSConnection(host='api.cloudflare.com', timeout=10)
        if data is not None:
            logging.info('%s %s %s' % (method, url, data))
            connection.request(method, url, json.dumps(data), headers)
        else:
            logging.info('%s %s' % (method, url))
            connection.request(method, url, headers=headers)
        response = connection.getresponse()
        logging.info('%s %s' % (response.status, response.reason))
        result = json.loads(response.read().decode('utf-8'))
        connection.close()
        if result.get('errors') is not None and len(result.get('errors')) > 0 \
                and result.get('errors')[0].get('message') is not None:
            logging.error(result.get('errors')[0].get('message'))
        return result.get('result')
    except Exception as e:
        logging.error(e)


def list_zones():
    url = '/client/v4/zones?name=%s' % ZONE
    result = restful_api(url)
    if result is not None and len(result) == 1 and result[0].get('id') is not None:
        return result[0].get('id')
    raise RuntimeError('List Zones NOT ONE.')


def list_records():
    zone_id = list_zones()
    if zone_id is None:
        return None, None
    url = '/client/v4/zones/%s/dns_records?name=%s' % (zone_id, DOMAIN)
    result = restful_api(url)
    if result is None or len(result) == 0:
        return zone_id, None
    record_id = None
    for record in result:
        if record.get('type') == 'CNAME':
            delete_record(zone_id, record.get('id'))
        elif record.get('type') == 'AAAA':
            if record_id is None:
                record_id = record.get('id')
            else:
                delete_record(zone_id, record.get('id'))
    return zone_id, record_id


def delete_record(zone_id, record_id):
    url = '/client/v4/zones/%s/dns_records/%s' % (zone_id, record_id)
    restful_api(url, 'DELETE')


def update_record(zone_id, record_id, content):
    url = '/client/v4/zones/%s/dns_records/%s' % (zone_id, record_id)
    data = {'type': 'AAAA', 'name': DOMAIN, 'content': content, 'ttl': 120, 'proxied': False}
    result = restful_api(url, 'PUT', data)
    if result is None or result.get('id') is None:
        dump_conf()


def create_record(zone_id, content):
    url = '/client/v4/zones/%s/dns_records' % zone_id
    data = {'type': 'AAAA', 'name': DOMAIN, 'content': content, 'ttl': 120, 'proxied': False}
    result = restful_api(url, 'POST', data)
    if result is None or result.get('id') is None:
        dump_conf()
    else:
        save_conf()


def get_record():
    try:
        client = socket.getaddrinfo(DOMAIN, 3389)
        return client[0][4][0]
    except Exception as e:
        logging.error(e)


def get_expect():
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as client:
            client.connect(('2400:3200::1', 53))
            return client.getsockname()[0]
    except Exception as e:
        logging.error(e)


def main():
    expect = get_expect()
    if expect is None:
        raise RuntimeError('Failed to get IP ADDRESS.')
    record = get_record()
    if record is not None and record == expect:
        return
    zone_id, record_id = load_conf()
    if zone_id is not None and record_id is not None:
        update_record(zone_id, record_id, expect)
    elif zone_id is not None:
        create_record(zone_id, expect)


if __name__ == '__main__':
    logging.basicConfig(filename=DDNS_LOG, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
