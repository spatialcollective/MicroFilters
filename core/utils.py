import json, csv, time, urllib2, os, hashlib
from django.http import HttpResponse
from django.core.cache import cache
from core.models import *

def generateData(dataFile, app, source, cacheKey):
	if source == "file":
		extension = getFileExtension(dataFile)
	elif source == "url":
		dataFile, extension = fetchFileFromURL(dataFile, cacheKey)
		if dataFile == 'error':
			return HttpResponse(status=400)
	
	#sha256_hash = str(hashfile(dataFile, hashlib.sha256()))
	# if ProcessedFile.objects.filter(sha256_hash=sha256_hash).exists():
	# 	return HttpResponse("{'status': 400, 'error_message': 'This file appears to have been processed already' }", status=400, content_type="application/json")
	# else:
	# 	ProcessedFile.objects.create(sha256_hash=sha256_hash)

	if extension == ".json":
		processJSONInput(dataFile, app, cacheKey)

	elif extension == ".csv":
		processCSVInput(dataFile, app, cacheKey)

	return HttpResponse(status=200)

def processJSONInput(dataFile, app, cacheKey):
	jsonObject = json.loads(dataFile.read())
	tweetIds = []
	lineModifier = 0
	line_limit = 1500
	data = []
	offset = ""
	
	cacheData = cache.get(cacheKey)
	cacheData['state'] = 'processing'
	cacheData['progress'] = 50
	cache.set(cacheKey, cacheData)

	for index, row in enumerate(jsonObject):
		datarow = {}
		if row.get("id") in tweetIds:
			lineModifier = lineModifier + 1
			continue

		if row.get("user").get("screen_name"):
			datarow["User-Name"] = row.get("user").get("screen_name")
		if row.get("text"):
			if 'RT ' in row.get('text'):
				lineModifier = lineModifier + 1
				continue
			datarow["Tweet"] = row.get("text").encode('ascii', 'ignore')

		if row.get("created_at"):
			datarow["Time-stamp"] = time.strftime("%Y-%m-%d %H:%M:%S" ,time.strptime(row.get('created_at'), "%a %b %d %H:%M:%S +0000 %Y"))
		if row.get("id"):
			datarow["TweetID"] = row.get("id")
		data.append(datarow)

		if index-lineModifier == line_limit:
			offset = "_"+str(line_limit/1500)
			writeFile(data, app, cacheKey, offset)
			line_limit += 1500
			data = []
			print "file written at", index

	writeFile(data, app, cacheKey, offset)

def processCSVInput(dataFile, app, cacheKey):
	csvDict = csv.DictReader(dataFile)
	line_limit = 1500
	data = []
	tweetIds = []
	lineModifier = 0
	offset = ""

	cacheData = cache.get(cacheKey)
	cacheData['state'] = 'processing'
	cacheData['progress'] = 50
	cache.set(cacheKey, cacheData)

	for index, row in enumerate(csvDict):
		datarow = {}

		if row["tweetID"] in tweetIds:
			lineModifier = lineModifier + 1
			continue

		if row["userName"]:
			datarow["User-Name"] = row["userName"]
		if row["message"]:
			if 'RT ' in row["message"]:
				lineModifier = lineModifier + 1
				continue
			datarow["Tweet"] = row["message"]

		if row["createdAt"]:
			try:
				datarow["Time-stamp"] = time.strftime("%Y-%m-%d %H:%M:%S" ,time.strptime(row["createdAt"], "%Y-%m-%dT%H:%MZ"))
			except:
				datarow["Time-stamp"] = time.strftime("%Y-%m-%d %H:%M:%S" ,time.strptime(row["createdAt"], "%a %b %d %H:%M:%S +0000 %Y"))
		if row["tweetID"]:
			datarow["TweetID"] = row["tweetID"]
		data.append(datarow)

		if index-lineModifier == line_limit:
			offset = "_"+str(line_limit/1500)
			writeFile(data, app, cacheKey, offset)
			line_limit += 1500
			data = []

	writeFile(data, app, cacheKey, offset)


def writeFile(data, app, cacheKey, offset=""):
	filename = app+time.strftime("%Y%m%d%H%M%S",time.localtime())+offset+'.csv'
	outputfile = open("static/output/"+filename, "w")

	cacheData = cache.get(cacheKey)
	cacheData['state'] = 'writing'
	cacheData['progress'] = 75
	cache.set(cacheKey, cacheData)

	writer = csv.DictWriter(outputfile, ["User-Name","Tweet","Time-stamp","Location","Latitude","Longitude","Image-link","TweetID"])
	writer.writeheader()
	for row in data:
		writer.writerow(row)

	cacheData = cache.get(cacheKey)
	cacheData['state'] = 'done'
	cacheData['progress'] = 100
	cache.set(cacheKey, cacheData)

	outputfile.close()
	

def fetchFileFromURL(url, cacheKey):
	cache.set(cacheKey, {
            'state': 'uploading',
            'progress': 25
        })

	response = urllib2.urlopen(url)
	if response.headers.type == 'application/json':
		return response, '.json'
	elif response.headers.type == 'text/csv':
		return response, '.csv' 
	else:
		return 'error', 'error'

def getFileExtension(dataFile):
		dataFileName, extension = os.path.splitext(dataFile.name)
		return extension

def hashfile(afile, hasher, blocksize=65536):
	buf = afile.read(blocksize)
	while len(buf) > 0:
		hasher.update(buf)
		buf = afile.read(blocksize)
	return hasher.hexdigest()

def getCSVRowCount(csvDict):
	rows = list(csvDict)
	return len(rows)
