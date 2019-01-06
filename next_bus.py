# -*- coding: utf-8 -*-
#!/usr/bin/env python

import i2c_lcd_driver
import RPi.GPIO as GPIO
import datetime
from datetime import timedelta
from time import *
import json
import threading
import api_key
from threading import *
import requests

#Set API key from TRAFIKLAB
apiKey=api_key.api_key

import socket
def get_ip():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# doesn't even have to be reachable
		s.connect(('10.255.255.255', 1))
		IP = s.getsockname()[0]
	except:
		IP = '127.0.0.1'
	finally:
		s.close()
	return IP

def display_off():
    GPIO.output(11,GPIO.LOW)

def fetch_api():
	global fetching_active
	global response
	global dest1
	global line1
	global time1
	global time1time
	global dest2
	global line2
	global time2
	global time2time
	global mylcd
	global lastApiFetch
	fetching_active=True
	
	try:
		lastApiFetch=datetime.datetime.now()
		response = requests.get("http://api.sl.se/api2/realtimedeparturesv4.json?&key="+apiKey+"&maxJourneys=2&Bus=true&Metro=false&Train=false&Tram=false&Ship=false&TimeWindow=60&siteid=1981&Format=xml")
		data = response.json()
		dest1=data['ResponseData']['Buses'][0]['Destination'].encode('ascii','replace')
		line1=data['ResponseData']['Buses'][0]['LineNumber'].encode('ascii','replace')
		time1=data['ResponseData']['Buses'][0]['ExpectedDateTime']
		time1time=datetime.datetime.strptime(time1, '%Y-%m-%dT%H:%M:%S')
		#Fulfix för att testa
		#time1time=datetime.datetime.now()+timedelta(seconds=5)
		
		dest2=data['ResponseData']['Buses'][1]['Destination'].encode('ascii','replace')
		line2=data['ResponseData']['Buses'][1]['LineNumber'].encode('ascii','replace')
		time2=data['ResponseData']['Buses'][1]['ExpectedDateTime']
		time2time=datetime.datetime.strptime(time2, '%Y-%m-%dT%H:%M:%S')
		dest1=dest1.replace('?lvsj?','Alvsja').replace('H?gdalen','Hogdalen')
		dest2=dest2.replace('?lvsj?','Alvsja').replace('H?gdalen','Hogdalen')

	except:
		print("Something failed when fetching data")
		dest1="N/A"
		line1="N/A"
		time1time=datetime.datetime.now()
		dest2="N/A"
		line2="N/A"
		time2time=datetime.datetime.now()
	sleep(1)
	fetching_active=False


def update_time():
	global fetching_active
	global response
	global dest1
	global line1
	global time1
	global time1time
	global dest2
	global line2
	global time2
	global time2time
	global mylcd
	global diff1
	global diff2
	now=datetime.datetime.now()
	diff1=time1time-datetime.datetime.now()
	diff2=time2time-datetime.datetime.now()


	if(diff1.total_seconds()<0):
		diff1str="-"+str(-diff1)
	else:
		diff1str=" "+str(diff1)
	if(diff2.total_seconds()<0):
		diff2str="-"+str(-diff2)
	else:
		diff2str=" "+str(diff2)
	
	if fetching_active==False:
		mylcd.lcd_display_string(line1[:3],1)
		mylcd.lcd_display_string(line2[:3],2)
		mylcd.lcd_display_string(dest1[:3],1,4)
		mylcd.lcd_display_string(dest2[:3],2,4)
		mylcd.lcd_display_string(diff1str,1,8)
		mylcd.lcd_display_string(diff2str,2,8)

def callback_light(channel):
	global t
	if GPIO.input(13) == GPIO.HIGH:
		#if GPIO.input(11)==1:
		#	GPIO.output(11,GPIO.LOW)
		#else:
		#	GPIO.output(11,GPIO.HIGH)
		GPIO.output(11,GPIO.HIGH)
		t.cancel()
		t=Timer(30.0, display_off)
		t.start()
	else:
		# Button goes back up
		True

def callback_api(channel):
	if GPIO.input(15) == GPIO.HIGH:
		fetch_api()
		print("fetch due to button")	
	else:
		# Button goes back up
		True

try:
	#Setup pins
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(11, GPIO.OUT)
	GPIO.output(11,GPIO.HIGH)
	
	
	#Setup Callbacks
	GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.add_event_detect(13, GPIO.BOTH, callback=callback_light, bouncetime=300)
	GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.add_event_detect(15, GPIO.BOTH, callback=callback_api, bouncetime=300)
	
	#Initialize LCD
	mylcd = i2c_lcd_driver.lcd()
	mylcd.lcd_display_string(get_ip())
	sleep(3)
	mylcd.lcd_clear()
	
	lastApiFetch=datetime.datetime.now()
	time1time=datetime.datetime.now()
	time2time=datetime.datetime.now()
	diff1=time1time-lastApiFetch
	diff2=time2time-lastApiFetch
	
	fetching_active=False
	t=Timer(30.0, display_off)
	t.start()
	print("initial fetch")
	fetch_api()
	#test
	while True:
		time_passed_since_last_fetch=(datetime.datetime.now()-lastApiFetch).total_seconds()
		# If 60 sec past diff1 or diff2
		# If 30 min have passed with no fetch
		if diff1.total_seconds()<-60:
			fetch_api()
			print(str(datetime.datetime.now())+" : Fetch due to diff1")
		elif diff2.total_seconds()<-60:
			fetch_api()
			print(str(datetime.datetime.now())+" : Fetch due to diff2")
		elif time_passed_since_last_fetch>(30*60):
			fetch_api()
		sleep(0.2)
		update_time()
finally:
	GPIO.cleanup()
	print("Goodbye!")