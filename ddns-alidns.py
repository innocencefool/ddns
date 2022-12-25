#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import logging
import os
import socket

from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeSubDomainRecordsRequest import DescribeSubDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkcore.client import AcsClient

# pip3 install aliyun-python-sdk-alidns -i https://pypi.tuna.tsinghua.edu.cn/simple

ACCESSKEY_ID = '########################'
ACCESSKEY_SECRET = '##############################'
DOMAIN = 'alidns.com'
RECORD = 'www'

SUBDOMAIN = '%s.%s' % (RECORD, DOMAIN)

DDNS_CONF = os.path.split(os.path.realpath(__file__))[0] + os.sep + 'ddns-alidns.conf'
DDNS_LOG = os.path.split(os.path.realpath(__file__))[0] + os.sep + 'ddns-alidns.log'

acsClient = AcsClient(ACCESSKEY_ID, ACCESSKEY_SECRET, 'cn-hangzhou')


def describe_records():
    try:
        logging.info('DescribeSubDomainRecordsRequest %s' % SUBDOMAIN)
        request = DescribeSubDomainRecordsRequest()
        request.set_DomainName(DOMAIN)
        request.set_SubDomain(SUBDOMAIN)
        request.set_Type('AAAA')
        request.set_accept_format('json')
        response = acsClient.do_action_with_exception(request)
        return json.loads(response)['DomainRecords']['Record'][0]['RecordId']
    except Exception as e:
        logging.error(e)


def add_record(value):
    try:
        logging.info('AddDomainRecordRequest %s %s' % (SUBDOMAIN, value))
        request = AddDomainRecordRequest()
        request.set_DomainName(DOMAIN)
        request.set_RR(RECORD)
        request.set_Type('AAAA')
        request.set_Value(value)
        request.set_accept_format('json')
        response = acsClient.do_action_with_exception(request)
        return json.loads(response)['RecordId']
    except Exception as e:
        logging.error(e)


def update_record(record_id, value):
    try:
        logging.info('UpdateDomainRecordRequest %s %s' % (SUBDOMAIN, value))
        request = UpdateDomainRecordRequest()
        request.set_RecordId(record_id)
        request.set_RR(RECORD)
        request.set_Type('AAAA')
        request.set_Value(value)
        request.set_accept_format('json')
        response = acsClient.do_action_with_exception(request)
        return json.loads(response)['RecordId']
    except Exception as e:
        logging.error(e)
        if 'DomainRecordDuplicate' in str(e):
            return record_id


def get_recorded():
    try:
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
        if os.path.exists(DDNS_CONF):
            with open(DDNS_CONF, 'r') as ddns_conf:
                dict_conf = json.load(ddns_conf)
                if dict_conf.get('subdomain') is not None and dict_conf.get('subdomain') == SUBDOMAIN:
                    return dict_conf.get('record_id')
    except Exception as e:
        logging.error(e)


def save_conf(record_id=None):
    try:
        dict_conf = {'subdomain': SUBDOMAIN, 'record_id': record_id}
        with open(DDNS_CONF, 'w') as ddns_conf:
            json.dump(dict_conf, ddns_conf)
    except Exception as e:
        logging.error(e)


def clear_conf():
    save_conf()


def main():
    expected = get_expected()
    if expected is not None:
        recorded = get_recorded()
        if recorded is None or recorded != expected:
            record_id = load_conf()
            if record_id is None:
                record_id = describe_records()
                if record_id is None:
                    record_id = add_record(expected)
                    if record_id is not None:
                        save_conf(record_id)
                else:
                    record_id = update_record(record_id, expected)
                    if record_id is not None:
                        save_conf(record_id)
            else:
                record_id = update_record(record_id, expected)
                if record_id is not None:
                    save_conf(record_id)
                else:
                    clear_conf()


if __name__ == '__main__':
    logging.basicConfig(filename=DDNS_LOG, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
