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
DDNS_PATH = os.path.split(os.path.realpath(__file__))[0] + os.sep
DDNS_CONF = DDNS_PATH + 'ddns-dnspod.conf'
DDNS_LOG = DDNS_PATH + 'ddns-dnspod.log'


def load_conf():
    try:
        if os.path.exists(DDNS_CONF):
            with open(DDNS_CONF, 'r') as ddns_conf:
                dict_conf = json.load(ddns_conf)
                if dict_conf.get('domain_id') is not None \
                        and dict_conf.get('record_id') is not None \
                        and dict_conf.get('subdomain') is not None \
                        and dict_conf.get('subdomain') == SUBDOMAIN:
                    return dict_conf.get('domain_id'), dict_conf.get('record_id')
        return save_conf()
    except Exception as e:
        logging.error(e)
        return save_conf()


def save_conf():
    return dump_conf(get_record_id())


def dump_conf(domain_id=None, record_id=None):
    try:
        dict_conf = {'subdomain': SUBDOMAIN, 'domain_id': domain_id, 'record_id': record_id}
        with open(DDNS_CONF, 'w') as ddns_conf:
            json.dump(dict_conf, ddns_conf)
        return domain_id, record_id
    except Exception as e:
        logging.error(e)
        return None, None


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


def get_record():
    try:
        if dns_resolver:
            return resolve()
        else:
            client = socket.getaddrinfo(SUBDOMAIN, 3389)
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
    params = dict_params(domain=DOMAIN)
    response = request_dnsapi('/Domain.Info', params)
    if response is not None \
            and response.get('domain') is not None \
            and response.get('domain').get('id') is not None:
        return response.get('domain').get('id')
    raise RuntimeError('Failed to get DOMAIN ID.')


def get_record_id():
    domain_id = get_domain_id()
    if domain_id is None:
        return None, None
    params = dict_params(None, domain_id, RECORD, None, 'AAAA', None, None)
    response = request_dnsapi('/Record.List', params)
    if response is None or response.get('records') is None or len(response.get('records')) == 0:
        return domain_id, None
    record_id = None
    for record in response.get('records'):
        if record_id is None:
            record_id = record.get('id')
        else:
            remove_record(domain_id, record.get('id'))
    return domain_id, record_id


def modify_record(domain_id, record_id, value):
    params = dict_params(None, domain_id, RECORD, record_id, 'AAAA', value, 0)
    response = request_dnsapi('/Record.Modify', params)
    if response is None \
            or response.get('status') is None \
            or response.get('status').get('code') is None \
            or response.get('status').get('code') != '1':
        dump_conf()


def create_record(domain_id, value):
    params = dict_params(None, domain_id, RECORD, None, 'AAAA', value, 0)
    response = request_dnsapi('/Record.Create', params)
    if response is None or response.get('record') is None:
        dump_conf()
    else:
        save_conf()


def remove_record(domain_id, record_id):
    params = dict_params(None, domain_id, None, record_id, None, None, None)
    request_dnsapi('/Record.Remove', params)


def main():
    expect = get_expect()
    if expect is None:
        raise RuntimeError('Failed to get IP ADDRESS.')
    record = get_record()
    if record is not None and record == expect:
        return
    domain_id, record_id = load_conf()
    if domain_id is not None and record_id is not None:
        modify_record(domain_id, record_id, expect)
    elif domain_id is not None:
        create_record(domain_id, expect)


if __name__ == '__main__':
    logging.basicConfig(filename=DDNS_LOG, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
