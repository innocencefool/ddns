#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import http.client
import json
import logging
import os
import socket
from urllib import parse

try:
    dns_resolver = True
    import dns.resolver  # pip3 install dnspython -i https://pypi.tuna.tsinghua.edu.cn/simple
except ImportError:
    dns_resolver = False

LOGIN_TOKEN = '13490,6b5976c68aba5b14a0558b77c17c3932'
DOMAIN = 'dnspod.cn'
RECORD = 'www'

SUBDOMAIN = '%s.%s' % (RECORD, DOMAIN)

DDNS_CONF = os.path.split(os.path.realpath(__file__))[0] + os.sep + 'ddns-dnspod.conf'
DDNS_LOG = os.path.split(os.path.realpath(__file__))[0] + os.sep + 'ddns-dnspod.log'


def resolve():
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5
        resolver.nameservers = ['119.29.29.29']
        res = resolver.resolve(SUBDOMAIN, 'AAAA')
        for answer in res.response.answer:
            for item in answer.items:
                return item.address
    except Exception as e:
        logging.error(e)


def get_recorded():
    try:
        if dns_resolver:
            return resolve()
        else:
            client = socket.getaddrinfo(SUBDOMAIN, 3389)
            return client[0][4][0]
    except Exception as e:
        logging.error(e)


def get_expected():
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as client:
            client.connect(('2400:3200::1', 53))
            return client.getsockname()[0]
    except Exception as e:
        logging.error(e)


def load_conf():
    try:
        if not os.path.exists(DDNS_CONF):
            return None, None
        with open(DDNS_CONF, 'r') as ddns_conf:
            dict_conf = json.load(ddns_conf)
            if dict_conf.get('subdomain') is not None and dict_conf.get('subdomain') == SUBDOMAIN:
                return dict_conf.get('domain_id'), dict_conf.get('record_id')
        return None, None
    except Exception as e:
        logging.error(e)
        return None, None


def save_conf(domain_id=None, record_id=None):
    try:
        dict_conf = {'subdomain': SUBDOMAIN, 'domain_id': domain_id, 'record_id': record_id}
        with open(DDNS_CONF, 'w') as ddns_conf:
            json.dump(dict_conf, ddns_conf)
    except Exception as e:
        logging.error(e)


def clear_conf():
    save_conf()


def dict_params(domain=None, domain_id=None, record=None, record_id=None, record_type=None, value=None,
                record_line_id=None):
    params = dict(format='json', login_token=LOGIN_TOKEN)
    if domain is not None:
        params['domain'] = domain
    if domain_id is not None:
        params['domain_id'] = domain_id
    if record is not None:
        params['sub_domain'] = record
    if record_id is not None:
        params['record_id'] = record_id
    if record_type is not None:
        params['record_type'] = record_type
    if value is not None:
        params['value'] = value
    if record_line_id is not None:
        params['record_line_id'] = record_line_id
    return params


def request_dnsapi(url, body):
    try:
        logging.info('%s %s' % (url, body))
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'text/json'}
        connection = http.client.HTTPSConnection(host='dnsapi.cn', timeout=6)
        connection.request('POST', url, parse.urlencode(body), headers)
        response = connection.getresponse()
        result = json.loads(response.read().decode('utf-8'))
        logging.info('%s %s %s' % (response.status, response.reason, result))
        connection.close()
        return result
    except Exception as e:
        logging.error(e)


def get_domain_id():
    try:
        params = dict_params(domain=DOMAIN)
        response = request_dnsapi('/Domain.Info', params)
        if response is not None and response.get('domain') is not None:
            return response.get('domain').get('id')
    except Exception as e:
        logging.error(e)


def get_record_id(domain_id, record_type):
    try:
        params = dict_params(None, domain_id, RECORD, None, record_type, None, None)
        response = request_dnsapi('/Record.List', params)
        if response is not None and response.get('records') is not None:
            return response.get('records')[0].get('id')
    except Exception as e:
        logging.error(e)


def create_record(domain_id):
    try:
        params = dict_params(None, domain_id, RECORD, None, 'A', '119.29.29.29', 0)
        response = request_dnsapi('/Record.Create', params)
        if response is not None and response.get('record') is not None:
            return response.get('record').get('id')
    except Exception as e:
        logging.error(e)


def remove_record(domain_id):
    try:
        record_id = get_record_id(domain_id, 'A')
        if record_id is not None:
            params = dict_params(None, domain_id, None, record_id, None, None, None)
            request_dnsapi('/Record.Remove', params)
    except Exception as e:
        logging.error(e)


def ddns_record(domain_id, record_id):
    try:
        params = dict_params(None, domain_id, RECORD, record_id, None, None, 0)
        response = request_dnsapi('/Record.Ddns', params)
        if response is not None:
            return response.get('status').get('code') == '1'
    except Exception as e:
        logging.error(e)


def modify_record(domain_id, record_id, value):
    try:
        params = dict_params(None, domain_id, RECORD, record_id, 'AAAA', value, 0)
        response = request_dnsapi('/Record.Modify', params)
        if response is not None:
            return response.get('status').get('code') == '1'
    except Exception as e:
        logging.error(e)


def main():
    try:
        expected = get_expected()
        if expected is None:
            raise RuntimeError('Failed to get IP address.')
        recorded = get_recorded()
        if recorded is not None and recorded == expected:
            return
        domain_id, record_id = load_conf()
        if domain_id is None:
            record_id = None
            domain_id = get_domain_id()
        if domain_id is None:
            raise RuntimeError('Domain %s does not exist.' % DOMAIN)
        if record_id is None:
            record_id = get_record_id(domain_id, 'AAAA')
        if record_id is None:
            record_id = create_record(domain_id)
        if record_id is None:
            remove_record(domain_id)
            raise RuntimeError('Domain %s creation failed.' % DOMAIN)
        if ddns_record(domain_id, record_id) and modify_record(domain_id, record_id, expected):
            save_conf(domain_id, record_id)
        else:
            clear_conf()
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    logging.basicConfig(filename=DDNS_LOG, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
