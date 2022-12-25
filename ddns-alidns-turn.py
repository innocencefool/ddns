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

# pip3 install pytz aliyun-python-sdk-alidns -i https://pypi.tuna.tsinghua.edu.cn/simple

REGION_ID = 'cn-hangzhou'
ACCESSKEY_ID = '########################'
ACCESSKEY_SECRET = '##############################'
DOMAIN = 'alidns.com'
RECORD = 'www'

TIMEZONE = 'Asia/Shanghai'
RECORD_TYPE = 'CNAME'
RECORD_TURN = {'20:00:00': 'us.alidns.com', '02:00:00': 'jp.alidns.com'}

DDNS_PATH = os.path.split(os.path.realpath(__file__))[0] + os.sep
DDNS_CONF = DDNS_PATH + 'ddns-alidns-turn.conf'
DDNS_LOG = DDNS_PATH + 'ddns-alidns-turn.log'
SUBDOMAIN = '%s.%s' % (RECORD, DOMAIN)

acsClient = AcsClient(ACCESSKEY_ID, ACCESSKEY_SECRET, REGION_ID)


def load_conf():
    try:
        if not os.path.exists(DDNS_CONF):
            save_conf()
        with open(DDNS_CONF, 'r') as ddns_conf:
            dict_conf = json.load(ddns_conf)
            if dict_conf.get('subdomain') is not None and dict_conf.get('subdomain') == SUBDOMAIN:
                record_id = dict_conf.get('record_id')
                if record_id is not None:
                    return dict_conf.get('record_id')
                else:
                    save_conf()
    except Exception as e:
        logging.error(e)


def save_conf():
    try:
        dict_conf = {'subdomain': SUBDOMAIN, 'record_id': describe_records(False)}
        with open(DDNS_CONF, 'w') as ddns_conf:
            json.dump(dict_conf, ddns_conf)
    except Exception as e:
        logging.error(e)


def describe_records(value=True):
    try:
        logging.info('DescribeSubDomainRecordsRequest %s' % SUBDOMAIN)
        request = DescribeSubDomainRecordsRequest()
        request.set_DomainName(DOMAIN)
        request.set_SubDomain(SUBDOMAIN)
        request.set_Type(RECORD_TYPE)
        request.set_Line('default')
        request.set_accept_format('json')
        response = acsClient.do_action_with_exception(request)
        if value:
            return json.loads(response)['DomainRecords']['Record'][0]['Value']
        else:
            return json.loads(response)['DomainRecords']['Record'][0]['RecordId']
    except Exception as e:
        logging.error(e)


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
        response = acsClient.do_action_with_exception(request)
        return json.loads(response)['RecordId']
    except Exception as e:
        logging.error(e)


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
    record_id = load_conf()
    if record_id is not None:
        recorded = describe_records()
        if recorded is not None:
            expected = my_turn()
            if expected is not None and expected != recorded:
                update_record(record_id, expected)


if __name__ == '__main__':
    logging.basicConfig(filename=DDNS_LOG, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
