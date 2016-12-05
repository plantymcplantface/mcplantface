


import time
import math
import subprocess
from contextlib import contextmanager
import os

import RPIO
import cv2

def reset():
    RPIO.cleanup()


#reset() #for debug



class Output(object):
    def __init__(self,pin):
        self.state=False
        self.pin=pin
        RPIO.setup(pin,RPIO.OUT)
        RPIO.output(pin,self.state)
    def get(self):
        return bool(self.state)
    def set(self,v):
        self.state=v
        RPIO.output(self.pin,self.get())
    def __int__(self):
        return int(self.get())
    def __bool__(self):
        return bool(self.get())

class Relay(Output):
    def __init__(self,pin):
        self.state=False
        self.pin=pin
        RPIO.setup(pin,RPIO.OUT)
        RPIO.output(pin,not self.state)
    def set(self,v):
        self.state=v
        RPIO.output(self.pin,not self.get())

class Input(object):
    waiting_for_interrupts=False
    def __init__(self,pin,interrupt=None):
        self.pin=pin
        RPIO.setup(pin,RPIO.IN,pull_up_down=RPIO.PUD_UP)
        if interrupt:
            self.interrupt=interrupt
            RPIO.add_interrupt_callback(pin,self._cb,edge="falling",pull_up_down=RPIO.PUD_UP,debounce_timeout_ms=100)
            if not Input.waiting_for_interrupts:
                RPIO.wait_for_interrupts(threaded=True)
                Input.waiting_for_interrupts=True
    def get(self):
        return RPIO.input(self.pin)
    def _cb(self,gpio_id,val):
        if gpio_id==self.pin:
            self.interrupt()



relay_nc = Relay(7)
relay_12VDC_A = Relay(8)
relay_12VDC_B = Relay(25)
relay_115VAC = Relay(24)
led = Relay(14)


#button_pressed=False
#def cb():
#    global button_pressed
#    button_pressed=True
button = Input(3)#nope. interrrupts also interact badly with subprocess


    

def buzz(duration, pitch):
    on_time = 0.5/pitch
    counts = int(duration/on_time)
    for i in range(counts):
        relay_nc.set(i%2)
        time.sleep(on_time)
    relay_nc.set(0)

def chirp(duration,startPitch,endPitch,endDuration=0):
    startPeriod = 1.0/startPitch
    endPeriod = 1.0/endPitch
    period = startPeriod
    steps = int((2*duration)/(startPeriod+endPeriod))
    dPeriod = (endPeriod-startPeriod)/steps
    for i in range(steps):
        relay_nc.set(1)
        time.sleep(period/2)
        relay_nc.set(0)
        time.sleep(period/2)
        period += dPeriod
    steps = int(endDuration/period)
    for i in range(steps):
        relay_nc.set(1)
        time.sleep(period/2)
        relay_nc.set(0)
        time.sleep(period/2)

def sprayerOn():
    relay_12VDC_A.set(1)
def sprayerOff():
    relay_12VDC_A.set(0)

def lightsOn():
    relay_115VAC.set(1)
def lightsOff():
    relay_115VAC.set(0)



@contextmanager
def wifiKludge():
    yield
    print "checking wifi connection, and restoring if necessary..."
    subprocess.call("/usr/local/bin/wifi_rebooter.sh",shell=False) 
    #above is how I found out about the signal bug in RPIO.PWM
    

    
def heartBeatLED():
    while True:
        time.sleep(0.5)
        led.set(0)
        time.sleep(0.5)
        led.set(1)


def klaxon():
    for i in range(3):
        chirp(1.0,30,72,0.5)
        time.sleep(1)

def morning():
    klaxon()
    lightsOn()

def evening():
    klaxon()
    lightsOff()

def spray():
    for i in range(2):
        buzz(1.0,44)
        time.sleep(1.0)
    try:
        subprocess.call("python happy_plant_servo.py start",shell=True)
        sprayerOn()
        subprocess.call("python happy_plant_servo.py spray",shell=True)
    finally:
        sprayerOff()
    subprocess.call("python happy_plant_servo.py home",shell=True)
    
def interpreter():
    import code
    code.interact(local=dict(globals(),**locals()))
    interpreter.exited=True
interpreter.exited=False

def quit():
    print "use ctrl-D instead"

DATA_DIR = "../happy-plant-data"
IMG_DIR = os.path.join(DATA_DIR,"images")
TIME_LAPSE = os.path.join(IMG_DIR,"timelapse")

def captureTimelapse():
    c = cv2.VideoCapture(0)
    #prune some black startup frames
    for i in range(100):
        flag,img = c.read()
    cv2.imwrite(img,os.path.join(TIME_LAPSE,datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S.jpg")))
    
                                 

if __name__=="__main__":
    import datetime
    if datetime.datetime.now().hour > 6 or datetime.datetime.now().hour < 1:
        lightsOn()
    else:
        lightsOff()
    sprayerOff()

    import schedule
    wakeUp = 6 #hour of the day
    lightHours = 19
    schedule.every().day.at("%d:00"%wakeUp).do(morning)
    schedule.every().day.at("%d:00"%((wakeUp+lightHours)%24)).do(evening)
    print "on time %d:00, off time %d:00"%(wakeUp,(wakeUp+lightHours)%24)
    for i in range(lightHours-1):#dry out for an hour before bedtime
        schedule.every().day.at("%d:00"%((wakeUp+i)%24)).do(spray)
        schedule.every().day.at("%d:30"%((wakeUp+i)%24)).do(spray)
        print "spray time %d:00"%((wakeUp+i)%24)
        print "spray time %d:30"%((wakeUp+i)%24)
    l = True
    import threading
    interpThread = threading.Thread(target=interpreter)
    interpThread.start()
    while True:
        time.sleep(0.25)
        if not button.get():
            spray()
        if interpreter.exited:
            print "goodbye"
            break
        led.set(l)
        l = not l
        schedule.run_pending()
