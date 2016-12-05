
import time
import math
import signal
from contextlib import contextmanager

HORIZ = 18
VERT = 23

@contextmanager
def signalSaving():
    #bug in RPIO, dies on way too many signals
    safesigs=[signal.SIGCHLD,signal.SIGCONT,signal.SIGTSTP,
              signal.SIGTTIN,signal.SIGTTOU,signal.SIGURG,
              signal.SIGWINCH,signal.SIGPIPE,signal.SIGINT,
              signal.SIGIO]
    savedsigs = [signal.getsignal(name) for name in safesigs]
    yield
    for name,sig in zip(safesigs,savedsigs):
        signal.signal(name,sig)
    
#with signalSaving(): #not necessary in subprocess
from RPIO import PWM

#with signalSaving():#not necessary when this is run in a separate process
servo = PWM.Servo()

@contextmanager
def kickServo():
    #hmm RPIO seems to fuck up occasionally and start sending crappy
    #commands to the servo. I'm not sure what causes it except it
    #may be related to USB camera use? not verified. in any case
    #it sucks; the servo just jitters and once the problem occurs
    #it appears to persist until the script is shut down cleanly
    #(DMA shutdown) and reloaded. Maybe this bullshit will fix it.
    #Nope... it didn't.
    global servo
    print "restarting servo..."
    PWM.cleanup()
    servo = PWM.Servo()
    print "restarted."
    yield
    print "restarting servo again..."
    PWM.cleanup()
    servo = PWM.Servo()
    print "restarted."


def sprayerPos(h,v,seekTime=0.4):
    assert 0 <= h and h <= 1
    assert 0 <= v and v <= 1
    try:
        LEFT_SOFT_LIM= 800
        RIGHT_SOFT_LIM= 1700
        DOWN_SOFT_LIM=1400
        UP_SOFT_LIM= 2100
        if h is not None:
            h_command = int((RIGHT_SOFT_LIM-LEFT_SOFT_LIM)*h+LEFT_SOFT_LIM)
            h_command -= h_command%10
        if v is not None:
            v_command = int((UP_SOFT_LIM-DOWN_SOFT_LIM)*v+DOWN_SOFT_LIM)
            v_command -= v_command%10
        #seeking both servos at the same time seems to be able to brown out the pi :(
        #with signalSaving():
        if h is not None: servo.set_servo(HORIZ,h_command)
        if v is not None: servo.set_servo(VERT,v_command)
        time.sleep(seekTime)
    finally:
        #with signalSaving():
        servo.stop_servo(HORIZ)
        servo.stop_servo(VERT)

def goToStart():
    sprayerPos(0.0,1.0)

def goHome():
    sprayerPos(0.0,0.0)

def sprayPattern0():
    #with kickServo():
    steps = 5
    for v in [5,4,3,2,3,4,5,4,3,4,5]:
        sprayerPos(0.0,v/float(steps))
        sprayerPos(1.0,v/float(steps))


if __name__=="__main__":
    import sys
    if sys.argv[1]=="start":
        goToStart()
    elif sys.argv[1]=="home":
        goHome()
    elif sys.argv[1]=="spray":
        sprayPattern0()
    PWM.cleanup()
    print "servo process exiting."
