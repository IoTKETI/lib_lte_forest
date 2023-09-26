#!/usr/bin/python3
import json
import os
import signal
import sys
import socket
from struct import *
import binascii
import time
import threading

import paho.mqtt.client as mqtt

i_pid = os.getpid()
argv = sys.argv

lteQ = {}

lib_mqtt_client = None
missionPort = None

UDPClientSocket = None
bufferSize = None


# ---MQTT----------------------------------------------------------------


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('[msw_mqtt_connect] connect to ', broker_ip)
    else:
        print("Bad connection Returned code=", rc)


def on_disconnect(client, userdata, flags, rc=0):
    print(str(rc))


def on_message(client, userdata, msg):
    print(str(msg.payload.decode("utf-8")))


def msw_mqtt_connect(host):
    global lib_mqtt_client

    lib_mqtt_client = mqtt.Client()
    lib_mqtt_client.on_connect = on_connect
    lib_mqtt_client.on_disconnect = on_disconnect
    lib_mqtt_client.on_message = on_message
    lib_mqtt_client.connect(host, 1883)

    lib_mqtt_client.loop_start()


# -----------------------------------------------------------------------


def missionPortOpening():
    global missionPort
    global UDPClientSocket
    global bufferSize

    missionPort = ('10.10.10.254', 8901)
    bufferSize = 1024

    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

    lteReqGetRssi()
    # send_data_to_msw(data_topic, lteQ)


def lteReqGetRssi():
    global missionPort
    global UDPClientSocket
    global bufferSize

    info = pack('>7sc', b'LTEInfo', b'\x00')
    UDPClientSocket.sendto(info, missionPort)

    msgFromServer = UDPClientSocket.recvfrom(bufferSize)

    missionPortData(msgFromServer[0].decode())


def send_data_to_msw(data_topic, obj_data):
    global lib_mqtt_client
    global lib

    lib_mqtt_client.publish(data_topic, obj_data)


def missionPortData(response):
    global lteQ

    try:
        data_arr = response.split(',')

        lteQ = dict()
        lteQ['CellID'] = data_arr[0]
        lteQ['MCC'] = data_arr[1]
        lteQ['MNC'] = data_arr[2]
        lteQ['RSRP'] = data_arr[3]
        lteQ['RSRQ'] = data_arr[4]
        lteQ['REGI'] = data_arr[5]
        lteQ['LTE_MODE'] = data_arr[6]
        lteQ['PCI'] = data_arr[7]
        lteQ['USIM'] = data_arr[8]

        data_topic = '/MUV/data/' + lib["name"] + '/' + lib["data"][0]
        lteQ = json.dumps(lteQ)
        print(lteQ)

        send_data_to_msw(data_topic, lteQ)

        lteQ = json.loads(lteQ)

    except e:
        print(e)

    threading.Timer(1, lteReqGetRssi).start()


if __name__ == '__main__':
    my_lib_name = 'lib_lte_forest'

    try:
        lib = dict()
        with open(my_lib_name + '.json', 'r') as f:
            lib = json.load(f)
            lib = json.loads(lib)
    except Exception as e:
        lib = dict()
        lib["name"] = my_lib_name
        lib["target"] = 'armv6'
        lib["description"] = "[name] [portnum] [baudrate]"
        lib["scripts"] = './' + my_lib_name + ' /dev/ttyUSB1 115200'
        lib["data"] = ['LTE']
        lib["control"] = []
        lib = json.dumps(lib, indent=4)
        lib = json.loads(lib)

        with open('./' + my_lib_name + '.json', 'w', encoding='utf-8') as json_file:
            json.dump(lib, json_file, indent=4)

    broker_ip = 'localhost'
    msw_mqtt_connect(host=broker_ip)

    missionPort = None
    missionPortOpening()


# python3 -m PyInstaller -F lib_lte_forest.py
