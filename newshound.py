# -*- coding: utf-8 -*-
from textblob import TextBlob
import urllib2
import json
import re
import signal
from selenium import webdriver
import boto3
import time
import os
import nltk
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')



	
def convertDateToEpoch(datestr):
	# eg date 2017-04-03T12:48:14Z
	pattern = '%Y-%m-%dT%H:%M:%S'
	# We need to trip the time as it can have different formats for ending
	m = re.search('(\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d).*', datestr)
	if m:
		return int(time.mktime(time.strptime(m.group(1), pattern)))
	else:
		raise ValueError('Date wrong format')
  
def handler(event, context):

	# phantomjs must be in the PATH
	MY_PATH = os.environ['PATH']
	os.environ['PATH'] = MY_PATH+":./phantomjs-1.9.8-linux-x86_64/bin"
	# The path for the NLTK data for TextBlob processing
	nltk.data.path.append("./nltk_data")

	starttime = time.strftime("%Y-%m-%d %H:%M:%S")
	run_history_table = dynamodb.Table(event['run_history_tablename'])
	
	if not event or not 'newsApiKey' in event:
		print "Missing newsApiKey in the event"
		exit(1)
	else:
		print "Using news api key: "+event['newsApiKey']
		
	run_history_table.put_item(Item={ 'starttime': starttime })
	
			
	# We need to exit whatever happens so wrap in try
	try:

			
		news_items = dynamodb.Table(event['news_items_tablename'])
		news_urls =  dynamodb.Table(event['news_url_tablename'])

		# dict of things
		things={}
		# query sources
		apiKey=event['newsApiKey']
		obj=json.loads(urllib2.urlopen("https://newsapi.org/v1/sources").read())
		sources=obj['sources']
			
		sourceIds={}
		for source in sources:
		  sourceIds[str(source['id'])] = {'country': source['country']}

		driver = None
		urls=[]
		for i in sourceIds:
			# Note the log to dev null - this is necessary because wont have write access to log in a lambda container
			driver = webdriver.PhantomJS(service_log_path=os.path.devnull)
			driver.set_window_size(1120, 550)

			obj=json.loads(urllib2.urlopen("https://newsapi.org/v1/articles?source="+i+"&apiKey="+apiKey).read())
			articles=obj['articles'] 
			for article in articles:
				things={}
				response=news_urls.get_item(Key={'url': article['url'], 'country': sourceIds[i]['country']})
				if response.has_key('Item'):
					continue
				urls.append(str(article['url']))
			
				try:
					driver.get(article['url'])
					text = driver.find_element_by_tag_name("body").text.encode('utf-8')
					story=TextBlob(text.decode('utf-8'))
					#print text.decode('utf-8')
			  
					for noun in story.noun_phrases:
			  
						# throw away nouns that dont appear with upper case first letters in the text ie they arent really names
						if noun.title() not in text.decode('utf-8'):
							continue;		
						# If the name if a single word check if it appears at start of sentence/paragraph ie capitalised only becuase of that
						if not " " in noun:
						# got space in it
						# Do we have a match in the text that isnt at start of sentence/paragraph if not ignore it - best we can do is ask whether a word occurs before without
						# a new line in way - need at least one match
							p=re.compile('\w+ '+noun.title())
							if p.search(text.decode('utf-8')) is None:
								continue # to next noun

						if things.has_key(noun):
							things[noun] = int(things[noun]) + 1
						else:
							things[noun] = 1
				except:
					# skip the processing of this url if we cant read it
					print article["url"] + " can't be processed"
					continue # to next article

				
				# Now add the data to the backend
				for thing, j in things.iteritems():
					# incremebnt update or insert?
					response = news_items.get_item( Key={'newsitem': thing, 'url': article['url']})
					if response.has_key('Item'):
						news_items.update_item( Key={ 'newsitem': thing , 'url': article['url']},
							UpdateExpression="set tally = :x",
							ExpressionAttributeValues={ ':x': int(response['Item']['tally']) +int(j) })
					else:
						try: 
							publishedAt = convertDateToEpoch(article['publishedAt']) if article['publishedAt'] is not None else int(time.time())
							news_items.put_item( Item={ 'newsitem': thing, 'url': article['url'], 'tally': int(j), 'publishedat': publishedAt })
						except ValueError:
							# skip as bad date
							print "can't process "+article['url']+ " because date format unknown: "+article['publishedAt']
			 
				news_urls.put_item( Item={ 'url': article['url'], 'country': sourceIds[i]['country'] })

			driver.service.process.send_signal(signal.SIGTERM)
	except Exception as e:
		print "exception in newshound: "+str(e)

