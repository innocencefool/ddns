#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import datetime
import json
import logging
import os

import pytz
from aliyunsdkalidns.request.v20150109.DescribeSubDomainRecordsRequest import DescribeSubDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkcore.client import AcsClient

# pip3 install aliyun-python-sdk-alidns pytz -i https://pypi.tuna.tsinghua.edu.cn/simple

ACCESSKEY_ID = '########################'
ACCESSKEY_SECRET = '##############################'
DOMAIN = 'alidns.com'
RECORD = 'www'
RECORD_TYPE = 'CNAME'
RECORD_TURN = {'20:00:00': 'us.alidns.com', '02:00:00': 'jp.alidns.com'}

REGION_ID = 'cn-hangzhou'
SUBDOMAIN = '%s.%s' % (RECORD, DOMAIN)
DDNS_PATH = os.path.split(os.path.realpath(__file__))[0] + os.sep
DDNS_CONF = DDNS_PATH + 'ddns-alidns-turn.conf'
DDNS_LOG = DDNS_PATH + 'ddns-alidns-turn.log'
TIMEZONE = 'Asia/Shanghai'

acsClient = AcsClient(ACCESSKEY_ID, ACCESSKEY_SECRET, REGION_ID)


def load_conf():
    try:
        if os.path.exists(DDNS_CONF):
            with open(DDNS_CONF, 'r') as ddns_conf:
                dict_conf = json.load(ddns_conf)
                if dict_conf.get('record_id') is not None \
                        and dict_conf.get('subdomain') is not None \
                        and dict_conf.get('subdomain') == SUBDOMAIN:
                    return dict_conf.get('record_id')
        return save_conf()
    except Exception as e:
        logging.error(e)
        return save_conf()


def save_conf():
    return dump_conf(describe_records())


def dump_conf(record_id=None):
    try:
        dict_conf = {'subdomain': SUBDOMAIN, 'record_id': record_id}
        with open(DDNS_CONF, 'w') as ddns_conf:
            json.dump(dict_conf, ddns_conf)
        return record_id
    except Exception as e:
        logging.error(e)


def describe_records(key='RecordId'):
    try:
        logging.info('DescribeSubDomainRecordsRequest %s' % SUBDOMAIN)
        request = DescribeSubDomainRecordsRequest()
        request.set_DomainName(DOMAIN)
        request.set_SubDomain(SUBDOMAIN)
        request.set_Type(RECORD_TYPE)
        request.set_Line('default')
        request.set_accept_format('json')
        response = acsClient.do_action_with_exception(request)
        return json.loads(response).get('DomainRecords').get('Record')[0].get(key)
    except Exception as e:
        logging.error(e)


def describe_value():
    return describe_records('Value')


def update_record(record_id, value):
    try:
        logging.info('UpdateDomainRecordRequest %s %s' % (SUBDOMAIN, value))
        request = UpdateDomainRecordRequest()
        request.set_RecordId(record_id)
        request.set_RR(RECORD)
        request.set_Type(RECORD_TYPE)
        request.set_Line('default')
        request.set_Value(value)
        request.set_accept_format('json')
        acsClient.do_action_with_exception(request)
    except Exception as e:
        logging.error(e)
        dump_conf()


def my_turn():
    now = datetime.datetime.now(pytz.timezone(TIMEZONE)).strftime("%H:%M:%S")
    keys = sorted(RECORD_TURN.keys())
    value = None
    for key in keys:
        if now >= key:
            value = RECORD_TURN.get(key)
    if value is None:
        value = RECORD_TURN.get(keys[-1])
    return value


def main():
    expect = my_turn()
    record = describe_value()
    if record is not None and record == expect:
        return
    record_id = load_conf()
    if record_id is not None:
        update_record(record_id, expect)


if __name__ == '__main__':
    logging.basicConfig(filename=DDNS_LOG, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
