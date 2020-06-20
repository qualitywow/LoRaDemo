#!/usr/bin/env python3
import sys
from time import sleep
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
import LoRaWAN
from LoRaWAN.MHDR import MHDR
import json,datetime
import socket
import random
import math
global PORT
PORT =9180
global g
global b
global A
global a
global shift
global safeflag
safeflag = False
BOARD.setup()
parser = LoRaArgumentParser("LoRaWAN sender")
def receiveB():
    global PORT
    HOST = '192.168.1.28'
    PORT += 1
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(15)
    
    print ('Server start at: %s:%s' %(HOST, PORT))
    print ('wait for connection...')
    conn, addr = s.accept()
    print ('Connected by ', addr)
    data = conn.recv(1024)
    print(data)
    #conn.send("server received you message.")
    s.close()
    #print(type(data.decode()))
    return int(data.decode())
    
class LoRaWANsend(LoRa):
    def __init__(self, devaddr = [], nwkey = [], appkey = [], verbose = False):
        super(LoRaWANsend, self).__init__(verbose)
        createGPA()
    def on_tx_done(self):
    
        global g,p,a,A,shift,safeflag
        print("TxDone\n")
        self.set_mode(MODE.STDBY)
        self.clear_irq_flags(TxDone=1)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_invert_iq(1)
        self.reset_ptr_rx()
        sleep(1)
        B = receiveB()
        
        temp = B
        for i in range(a):
            B *= temp 
        shift = B % p
        print("shift", shift)
        safeflag = True
        
        self.set_mode(MODE.RXSINGLE)
        
    def on_rx_done(self):
        global RxDone
        RxDone = any([self.get_irq_flags()[s] for s in ['rx_done']])
        print("RxDone")
        self.clear_irq_flags(RxDone=1)
       
        payload = self.read_payload(nocheck=True)
        lorawan = LoRaWAN.new(nwskey, appskey)
        lorawan.read(payload)
      
    
    def send(self):
        global fCnt,g,p,a,A,shift,safeflag 
        lorawan = LoRaWAN.new(nwskey, appskey)
        message = str(g)+','+str(p)+','+str(A)
        print (message)

        lorawan.create(MHDR.CONF_DATA_UP, {'devaddr': devaddr, 'fcnt': fCnt, 'data': list(map(ord, message)) })
        print("fCnt: ",fCnt)
        print("Send Message: ",message)
        fCnt = fCnt+1
        datalist = lorawan.to_raw()
        
            
        self.write_payload(datalist)
        
        self.set_mode(MODE.TX)
        
        
    def send_data(self):
        global fCnt,safeflag,shift
        lorawan = LoRaWAN.new(nwskey, appskey)
        message = "loraserver"
        lorawan.create(MHDR.CONF_DATA_UP, {'devaddr': devaddr, 'fcnt': fCnt, 'data': list(map(ord, message)) })
        print("fCnt: ",fCnt)
        fCnt = fCnt+1
        
        datalist = lorawan.to_raw()
        print(datalist)
        for i in range(1,len(datalist)-4):
            datalist[i] += shift
        print(datalist)
        
        print("Send Message: ",message)
        
        self.write_payload(datalist)
        self.set_mode(MODE.TX)
        
    def time_checking(self):
        global RxDone

        TIMEOUT = any([self.get_irq_flags()[s] for s in ['rx_timeout']])
        if TIMEOUT:
            print("TIMEOUT!!")
            sleep(3)
            self.send_data()
            write_config()
           
        elif RxDone:
            print("SUCCESS!!")
  
    
    def start(self):
        self.send()
        
        while True:
            self.time_checking()
            
            sleep(3)

def binary_array_to_hex(array):
    return ''.join(format(x, '02x') for x in array)

def write_config():
    global devaddr,nwskey,appskey,fCnt
    config = {'devaddr':binary_array_to_hex(devaddr),'nwskey':binary_array_to_hex(nwskey),'appskey':binary_array_to_hex(appskey),'fCnt':fCnt}
    data = json.dumps(config, sort_keys = True, indent = 4, separators=(',', ': '))
    fp = open("config.json","w")
    fp.write(data)
    fp.close()

def read_config():
    global devaddr,nwskey,appskey,fCnt
    config_file = open('config.json')
    parsed_json = json.load(config_file)
    devaddr = list(bytearray.fromhex(parsed_json['devaddr']))
    nwskey = list(bytearray.fromhex(parsed_json['nwskey']))
    appskey = list(bytearray.fromhex(parsed_json['appskey']))
    fCnt = parsed_json['fCnt']
    print("devaddr: ",parsed_json['devaddr'])
    print("nwskey : ",parsed_json['nwskey'])
    print("appskey: ",parsed_json['appskey'],"\n")
def createGPA():
    global g,p,a,A
    g = random.randint(1,20)
    print("g", g)
    p = random.randint(1,20)
    print("p", p)
    a = random.randint(1,20)
    A = int(math.pow(g,a)%p)

    
# Init
RxDone = False
fCnt = 0
devaddr = []
nwskey = []
appskey = []
read_config()
lora = LoRaWANsend(False)

# Setup
lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([1,0,0,0,0,0])
lora.set_freq(924.1)
#lora.set_freq(AS923.FREQ7)
lora.set_spreading_factor(SF.SF9)
lora.set_bw(BW.BW125)
lora.set_pa_config(pa_select=1)
lora.set_pa_config(max_power=0x0F, output_power=0x0E)
lora.set_sync_word(0x34)
lora.set_rx_crc(True)

#print(lora)
assert(lora.get_agc_auto_on() == 1)

try:
    print("Sending LoRaWAN message")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
    write_config()