# -*- coding: utf-8 -*-
import urllib2
import json
import re
import boto3
import time
import datetime
import os
from boto3.dynamodb.conditions import Key, Attr
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')


def isNotInt(s):
    try: 
        int(s)
        return False
    except ValueError:
        return True
		
def convertTimePeriodToEarliestTime(timeperiod):
	# Get now minus the timeperiod as epoch
	if not timeperiod or timeperiod.rstrip().lstrip() == "":
	  timeperiod='24 hours'
	# format OK?
	timeperiodArr = timeperiod.split()
	if len(timeperiodArr) != 2 or timeperiodArr[1].lower() not in ["hours", "minutes", "days"] or isNotInt(timeperiodArr[0]):
	  # invalid format
	  print "invalid format for TIMEPERIOD "+timeperiod+ " therefore using 24 hours"
	  timeperiod='24 hours'
	  timeperiodArr = timeperiod.split()
	  
	if timeperiodArr[1] == 'hours':
		earliest = datetime.datetime.now() - datetime.timedelta(hours=int(timeperiodArr[0]))
	elif timeperiodArr[1] == 'minutes':
		earliest = datetime.datetime.now() - datetime.timedelta(minutes=int(timeperiodArr[0]))	
	elif timeperiodArr[1] == 'days':
		earliest = datetime.datetime.now() - datetime.timedelta(days=int(timeperiodArr[0]))	
		
	return int(earliest.strftime("%s"))
	
def handler(event, context):


	# what is the request TYPE - defaults to LIST
	# Types - LIST - shows me a list a things in news in past 24 hours
	# User TIMEPERIOD to limit the timeframe - defaults to 24 hours - can specify as N hours, days, minutes
	TYPE='list'
	TIMEPERIOD='24 hours'
	if 'TYPE' in event:
		TYPE=event['TYPE']	
	if 'TIMEPERIOD' in event:
		TIMEPERIOD=event['TIMEPERIOD']	
		
	news_items=dynamodb.Table(os.environ['news_items_tablename'])	
	# We need to exit whatever happens so wrap in try
	try:	
		results = news_items.scan(
			FilterExpression=Attr('publishedat').gt(convertTimePeriodToEarliestTime(TIMEPERIOD)),
			ProjectionExpression='tally, newsitem, publishedat'
		)['Items']
		response={}
		for result in results:
			if hasattr(response, result['newsitem'].encode('utf-8')):
				response[result['newsitem'].encode('utf-8')] = response[result['newsitem'].encode('utf-8')] + result['tally']
			else:
				response[result['newsitem'].encode('utf-8')] = result['tally']
		# remove anything with a count of 1
		responses = filter(lambda x: response[x] > 2, response)
		filteredResponse={}
		for x in responses:
			filteredResponse[x]=response[x]
		return filteredResponse

	except Exception as e:
		print "EXCEPTION: "+str(e)
			