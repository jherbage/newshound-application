# newshound-application
An AWS Lambda based news scraping application using newsapi.org to report on commonly occurring things in the news for a given time period.

This is a simple backend processing application I knocked up so I could experiment with AWS Cloud Formation stacks and Lambda but it has some interest in its own right.

It comprises of 2 scripts, written as AWS lambda functions, mapping to the 2 parts to the application:
newshound.py - python script accepting 4 parameters in the event passed. The parameters are:
  newsApiKey - a key obtained from newsapi.org to query their API
  run_history_tablename - AWS dynamodb table name to store run history 
  news_items_tablename - AWS dynamodb table name to store news items
  news_url_tablename - AWS dynamodb table name to store nes urls processed

newshound.py queries the newsapi API reading the urls and stripping out things which are referenced as counts.
It requires the libs that are stored in the accompanying newshound-pylibs.tar.gz file to perform its actions and that library needs to be included within any lambda function zipfile. The libs allow the function to act like a browser and process the client side scripts of any news website and also some natural langauage processing to detect nouns in text so names can be extracted.

whatshot.py - python script accepting 2 parameters in the event passed. The parameters are:
  news_items_tablename - AWS dynamodb table name to retrieve news items from
  TIMEPERIOD - the time period over which to report news item counts - defaults to 24 hours if not specified - accepts minutes, hours, days

whatshot.py returns a json object of things and counts of the number of times the thing has been mentioned in the news for the time period requested.

The 2 lambda functions created for these scripts are expected to form the backend processing for the newshound application. An API gateway ma be used to front the whatshot app and the an AWS event rule used to periodically trigger the newshound application to update the stored data.

Seperate repositories will store the implementation instructions for this source code.
  

