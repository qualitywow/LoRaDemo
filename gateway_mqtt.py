#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json,logging,base64,time,datetime,ssl
logging.basicConfig(level=logging.DEBUG)
import random
import socket
import time
import math
global PORT

PORT = 9180
def sendB(B):
    global PORT
    time.sleep(3)
    print("sendB")
    HOST = '192.168.1.28'
    PORT +=1
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    
    
   
    s.send(str(B).encode())
    data = s.recv(1024)
    print("send:",data)

    s.close()

class GatewayMQTT(mqtt.Client):
    def __init__(self,gateway_eui):
        super(GatewayMQTT, self).__init__()
        self.logger = logging.getLogger()
        self.eui = gateway_eui.lower()
        print('set gateway eui : {}'.format(self.eui))
        self.publishTopic='gateway/{}/rx'.format(gateway_eui)
        print('MQTT topic : {}'.format(self.publishTopic))
        self.connectSuccess = False

    def connect2server(self,server,mqtt_user,mqtt_pass):
        self.username_pw_set(mqtt_user,mqtt_pass)
        self.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
        self.connect(server,1883,60)
        self.loop_start()

    def send2server(self,phyPayload,freq,coderate,rssi,snr,sf,bw):
        data = {
            'rxInfo' :{
                'mac' : self.eui,
                'timestamp' : self.getTimestamp(),
                'frequency' : int(freq*1000000),
                'channel' : 0,
                'rfChain' : 0,
                'crcStatus' : 1,
                'codeRate' : coderate,
                'rssi' : rssi,
                'loRaSNR' : snr,
                'size' : len(phyPayload),
                'dataRate' : {
                    'modulation' : 'LORA',
                    'spreadFactor' : sf,
                    'bandwidth' : bw
                    },
                'board' : 0,
                'antenna' : 0
            },
            'phyPayload' : base64.b64encode(bytes(phyPayload)).decode()
        }
        print("phyPayload")
        print(phyPayload)
        j = '{}'.format(json.dumps(data))
        self.txGet = False
        self.logger.debug('uplink payload: {}'.format(j))
        self.publish(self.publishTopic,j,qos=2)

    def on_connect(self, mqttc, obj, flags, rc) :
        if rc==0:
            print('\nconnect to server')
            self.subscribe('application/5/device/0000000000000007/rx')
            self.connectSuccess=True
        else:
            print('bad connection:{}'.format(rc))

    def on_message(self, mqttc, obj, msg) :
        print("msg:", msg)
        print(type(msg))
        j=json.loads(msg.payload.decode())
        print("j:")
        print(j)
        data= j["data"]
        real_data= base64.b64decode(data).decode()
        print("data:")
        print()
        print(data)
        print()
        print("after decode_data:")
        print(real_data)
        print()
        self.logger.debug('downlink payload: {}'.format(j))
        print()
        print("dataList!!!:")
        print(type(real_data))
     
        
        alist = self.splitData(real_data)
        print(type(alist))
        print("alist: ",alist)
        g, p, b = self.getGPA(alist)
        print ("g: ",g ," p: ", p,"b: ",b)
        
        temp = g
        
        for i in range(b) :
            g *= temp
        B = g % p
        
        print("B:",B)
        sendB(B)
        
        self.wait2timestamp(txInfo['timestamp'])
        self.send2node(list(base64.b64decode(j['phyPayload'].encode())))
        self.txGet=True


    def getTimestamp(self) :
        us=int(datetime.datetime.now().timestamp()*1000000)
        return us & 0xffffffff

    def wait2timestamp(self, timestamp):
        count=0
        while True :
            t=self.getTimestamp()
            count+=1
            if t>timestamp:
                break

    def recvLoop(self, timeout=1) :
        count=0
        endTime=datetime.datetime.now().timestamp()+timeout
        self.loop_start()
        while True :
            count+=1
            currentTime=datetime.datetime.now().timestamp()
            if self.txGet or currentTime>endTime:
                self.loop_stop()
                try :
                    self.reconnect()
                except Exception as e:
                    self.logger.warning('Exception: {}'.format(e))
                break
                
    def splitData(self,theData):
        print("splitdataList:")
        dataList = theData.split(",")
        
        print(dataList)
        return dataList
    
    
    def getGPA(self,numlist):
        self.g = int(numlist[0]) #Base
        self.p = int(numlist[1]) #MOD
        self.A = int(numlist[2]) #MOD
        self.b = random.randint(1,20) #secret exponent
        
        
        return self.g, self.p, self.b

    

    
    
                
    
