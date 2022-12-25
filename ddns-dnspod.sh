#!/bin/bash

############################################################################
# Linux ER-X 4.14.54-UBNT #1 SMP Fri Jan 22 10:21:07 UTC 2021 mips GNU/Linux
# sudo chmod +x /config/ddns-dnspod.sh
# configure
# set system task-scheduler task ddns crontab-spec '*/5 * * * *'
# set system task-scheduler task ddns executable path /config/ddns-dnspod.sh
# commit ; save
############################################################################

login_token=13490,6b5976c68aba5b14a0558b77c17c3932
domain=dnspod.cn
sub_domain=pi

ddns_conf=/tmp/ddns-dnspod.conf
ddns_log=/tmp/ddns-dnspod.log

interface_name_v4=pppoe0
interface_name_v6=switch0

# get ipv4 address
#expect_addr_v4=$(curl -s http://v4.ipv6-test.com/api/myip.php)
expect_addr_v4=$(ip -o -4 addr show $interface_name_v4 | awk '{print $4}' | cut -d / -f 1)

# get ipv6 address
#expect_addr_v6=$(curl -s http://v6.ipv6-test.com/api/myip.php)
#expect_addr_v6=$(ip -o -6 addr show $interface_name_v6 | grep 'scope global' | awk '{print $4}' | cut -d / -f 1)

if [ -n "$expect_addr_v4" ]; then
    # get record ipv4 address
    record_addr_v4=$(host -t A $sub_domain.$domain 119.29.29.29 | grep 'has IPv4 address' | awk '{print $5}')
    if [[ -z "$record_addr_v4" || "$record_addr_v4" != "$expect_addr_v4" ]]; then
        need_ddns_v4=0
    fi
    #echo "expect_addr_v4 : $expect_addr_v4" >> $ddns_log
    #echo "record_addr_v4 : $record_addr_v4" >> $ddns_log
fi

if [ -n "$expect_addr_v6" ]; then
    # get record ipv6 address
    record_addr_v6=$(host -t AAAA $sub_domain.$domain 119.29.29.29 | grep 'has IPv6 address' | awk '{print $5}')
    if [[ -z "$record_addr_v6" || "$record_addr_v6" != "$expect_addr_v6" ]]; then
        need_ddns_v6=0
    fi
    #echo "expect_addr_v6 : $expect_addr_v6" >> $ddns_log
    #echo "record_addr_v6 : $record_addr_v6" >> $ddns_log
fi

if [[ -n "$need_ddns_v4" || -n "$need_ddns_v6" ]]; then
    if [ -f "$ddns_conf" ]; then
        source $ddns_conf
    fi
    #echo "domain_id=$domain_id, record_id_v4=$record_id_v4, record_id_v6=$record_id_v6" >> $ddns_log
fi

if [ -n "$need_ddns_v4" ]; then
    if [ -z "$domain_id" ]; then
        # get domain_id
        domain_info=$(curl -s https://dnsapi.cn/Domain.Info -d "format=json&login_token=$login_token&domain=$domain")
        domain_id=$(echo "$domain_info" | jq -r ".domain.id // empty")
        if [ -n "$domain_id" ]; then
            echo "get domain_id success : domain_id=$domain_id" >> $ddns_log
            echo "domain_id=$domain_id" > $ddns_conf
        else
            status_message=$(echo "$domain_info" | jq -r ".status.message // empty")
            echo "get domain_id failed : $status_message" >> $ddns_log
        fi
    fi

    if [ -n "$domain_id" ]; then
        if [ -z "$record_id_v4" ]; then
            # get record_id_v4
            record_list=$(curl -s https://dnsapi.cn/Record.List -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_type=A")
            record_id_v4=$(echo "$record_list" | jq -r ".records[0].id // empty")
            if [ -n "$record_id_v4" ]; then
                echo "get record_id_v4 success, record_id_v4=$record_id_v4" >> $ddns_log
            else
                status_message=$(echo "$record_list" | jq -r ".status.message // empty")
                echo "get record_id_v4 failed : $status_message" >> $ddns_log
                # create record_id_v4
                record_create=$(curl -s https://dnsapi.cn/Record.Create -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_type=A&value=119.29.29.29&record_line_id=0")
                record_id_v4=$(echo "$record_create" | jq -r ".record.id // empty")
                if [ -n "$record_id_v4" ]; then
                    echo "create record_id_v4 success, record_id_v4=$record_id_v4" >> $ddns_log
                else
                    status_message=$(echo "$record_create" | jq -r ".status.message // empty")
                    echo "create record_id_v4 failed : $status_message" >> $ddns_log
                fi
            fi
            if [ -n "$record_id_v4" ]; then
                # ddns record_id_v4
                record_ddns=$(curl -s https://dnsapi.cn/Record.Ddns -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_id=$record_id_v4&record_line_id=0")
                status_message=$(echo "$record_ddns" | jq -r ".status.message // empty")
                echo "ddns record_id_v4 result : $status_message" >> $ddns_log
                status_code=$(echo "$record_ddns" | jq -r ".status.code // empty")
                if [ "$status_code" = "1" ]; then
                    echo "record_id_v4=$record_id_v4" >> $ddns_conf
                fi
            fi
        else
            # modify record_id_v4
            record_modify=$(curl -s https://dnsapi.cn/Record.Modify -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_id=$record_id_v4&record_type=A&value=$expect_addr_v4&record_line_id=0")
            status_message=$(echo "$record_modify" | jq -r ".status.message // empty")
            echo "modify record_id_v4 result : $status_message" >> $ddns_log
            status_code=$(echo "$record_modify" | jq -r ".status.code // empty")
            if [ "$status_code" != "1" ]; then
                echo "" > $ddns_conf
            fi
        fi
    fi
fi

if [ -n "$need_ddns_v6" ]; then
    if [ -z "$domain_id" ]; then
        # get domain_id
        domain_info=$(curl -s https://dnsapi.cn/Domain.Info -d "format=json&login_token=$login_token&domain=$domain")
        domain_id=$(echo "$domain_info" | jq -r ".domain.id // empty")
        if [ -n "$domain_id" ]; then
            echo "get domain_id success : domain_id=$domain_id" >> $ddns_log
            echo "domain_id=$domain_id" > $ddns_conf
        else
            status_message=$(echo "$domain_info" | jq -r ".status.message // empty")
            echo "get domain_id failed : $status_message" >> $ddns_log
        fi
    fi

    if [ -n "$domain_id" ]; then
        if [ -z "$record_id_v6" ]; then
            # get record_id_v6
            record_list=$(curl -s https://dnsapi.cn/Record.List -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_type=AAAA")
            record_id_v6=$(echo "$record_list" | jq -r ".records[0].id // empty")
            if [ -n "$record_id_v6" ]; then
                echo "get record_id_v6 success, record_id_v6=$record_id_v6" >> $ddns_log
            else
                status_message=$(echo "$record_list" | jq -r ".status.message // empty")
                echo "get record_id_v6 failed : $status_message" >> $ddns_log
                # create record_id_v6
                record_create=$(curl -s https://dnsapi.cn/Record.Create -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_type=AAAA&value=2400:3200::1&record_line_id=0")
                record_id_v6=$(echo "$record_create" | jq -r ".record.id // empty")
                if [ -n "$record_id_v6" ]; then
                    echo "create record_id_v6 success, record_id_v6=$record_id_v6" >> $ddns_log
                else
                    status_message=$(echo "$record_create" | jq -r ".status.message // empty")
                    echo "create record_id_v6 failed : $status_message" >> $ddns_log
                fi
            fi
            if [ -n "$record_id_v6" ]; then
                # ddns record_id_v6
                record_ddns=$(curl -s https://dnsapi.cn/Record.Ddns -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$record_id_v6&record_id=$record_id_v6&record_line_id=0")
                status_message=$(echo "$record_ddns" | jq -r ".status.message // empty")
                echo "ddns record_id_v6 result : $status_message" >> $ddns_log
                status_code=$(echo "$record_ddns" | jq -r ".status.code // empty")
                if [ "$status_code" = "1" ]; then
                    # modify record_id_v6
                    record_modify=$(curl -s https://dnsapi.cn/Record.Modify -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_id=$record_id_v6&record_type=AAAA&value=$expect_addr_v6&record_line_id=0")
                    status_message=$(echo "$record_modify" | jq -r ".status.message // empty")
                    echo "modify record_id_v6 result : $status_message" >> $ddns_log
                    status_code=$(echo "$record_modify" | jq -r ".status.code // empty")
                    if [ "$status_code" = "1" ]; then
                        echo "record_id_v6=$record_id_v6" >> $ddns_conf
                    fi
                fi
            fi
        else
            # modify record_id_v6
            record_modify=$(curl -s https://dnsapi.cn/Record.Modify -d "format=json&login_token=$login_token&domain_id=$domain_id&sub_domain=$sub_domain&record_id=$record_id_v6&record_type=AAAA&value=$expect_addr_v6&record_line_id=0")
            status_message=$(echo "$record_modify" | jq -r ".status.message // empty")
            echo "modify record_id_v6 result : $status_message" >> $ddns_log
            status_code=$(echo "$record_modify" | jq -r ".status.code // empty")
            if [ "$status_code" != "1" ]; then
                echo "" > $ddns_conf
            fi
        fi
    fi
fi
