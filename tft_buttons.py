import digitalio
import board
import sys
import time

buttonA = digitalio.DigitalInOut(board.D23)
buttonB = digitalio.DigitalInOut(board.D24)

buttonA.switch_to_input()
buttonB.switch_to_input()

current_state = 0

def state ():
    a = 0 if buttonA.value else 1
    b = 0 if buttonB.value else 2
    return (a | b)

def event ():
    global current_state
    s = state()
    if s == current_state:
        return None
    else:
        current_state = s
        return s

if __name__ == '__main__':
    while True:
        a = not buttonA.value
        b = not buttonB.value
        
        if a:
            print("A =", a)
        if b:
            print("B =", b)

        if a and b:
            sys.exit(0)
        
        time.sleep(.1)

