#!/usr/bin/python3
import json
import os
import serial
import signal
import sys

import paho.mqtt.client as mqtt

i_pid = os.getpid()
argv = sys.argv

lteQ = {}

lib_mqtt_client = None
missionPort = None


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


def missionPortOpening(PortNum, Baudrate):
    global missionPort
    global lteQ
    global lib

    if missionPort is None:
        try:
            missionPort = serial.Serial(PortNum, Baudrate, timeout=2)
            print('missionPort open. ' + PortNum + ' Data rate: ' + Baudrate)

        except TypeError as e:
            missionPortClose()
    else:
        if not missionPort.is_open:
            missionPortOpen()

            data_topic = '/MUV/data/' + lib["name"] + '/' + lib["data"][0]
            send_data_to_msw(data_topic, lteQ)


def missionPortOpen():
    global missionPort
    print('missionPort open!')
    missionPort.open()


def missionPortClose():
    global missionPort
    print('missionPort closed!')
    missionPort.close()


def missionPortError(err):
    print('[missionPort error]: ', err)
    os.kill(i_pid, signal.SIGKILL)


def lteReqGetRssi():
    global missionPort

    if missionPort is not None:
        if missionPort.is_open:
            atcmd = b'AT@DBG\r'
            missionPort.write(atcmd)


def send_data_to_msw(data_topic, obj_data):
    global lib_mqtt_client

    lib_mqtt_client.publish(data_topic, obj_data)


def missionPortData():
    global missionPort
    global lteQ

    try:
        lteReqGetRssi()
        missionStr = missionPort.readlines()

        end_data = (missionStr[-1].decode('utf-8'))[:-2]

        if end_data == 'OK':
            data_arr = missionStr[1].decode().split(',')

            lteQ = dict()
            for d in data_arr:
                d_arr = d.split(':')
                if d_arr[0] == '@DBG':
                    key = d_arr[1]
                    value = d_arr[2]
                else:
                    key = d_arr[0]
                    if '\r\n' in d_arr[1]:
                        value = d_arr[1].replace('\r\n', '')
                    else:
                        value = d_arr[1]

                if ' ' == key[0]:
                    key = key[1:]

                lteQ[key] = value

            data_keys = list(lteQ.keys())
            if 'Bandwidth' in data_keys:
                lteQ['Carrier'] = 'KT'
            elif 'MSISDN' in data_keys:
                lteQ['Carrier'] = 'SKT'
            elif 'Frequency' in data_keys:
                lteQ['Carrier'] = 'LGU'
            else:
                if 'Cell-ID' in data_keys:
                    lteQ['Carrier'] = 'KT'
                elif 'Cell(PCI)' in data_keys:
                    lteQ['Carrier'] = 'SKT'
                elif 'Cell ID' in data_keys:
                    lteQ['Carrier'] = 'LGU'
            # print(lteQ['Carrier'])
            # print(lteQ)
        else:
            pass

        data_topic = '/MUV/data/' + lib["name"] + '/' + lib["data"][0]
        lteQ = json.dumps(lteQ)

        send_data_to_msw(data_topic, lteQ)

        lteQ = json.loads(lteQ)

    except serial.SerialException as e:
        missionPortError(e)


if __name__ == '__main__':
    my_lib_name = 'lib_lte'

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

    lib['serialPortNum'] = argv[1]
    lib['serialBaudrate'] = argv[2]

    broker_ip = 'localhost'
    msw_mqtt_connect(host=broker_ip)

    missionPort = None
    missionPortNum = lib["serialPortNum"]
    missionBaudrate = lib["serialBaudrate"]
    missionPortOpening(missionPortNum, missionBaudrate)

    while True:
        missionPortData()

# python3 -m PyInstaller -F lib_lte.py
