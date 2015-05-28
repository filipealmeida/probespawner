from __future__ import with_statement
from pprint import pprint
#from databaseprobe import DatabaseProbe
from threading import Thread
from java.lang import Thread as JThread, InterruptedException
from java.util.concurrent import ExecutionException
from java.util.concurrent import Executors, TimeUnit
from java.util.concurrent import Executors, ExecutorCompletionService
from time import sleep
import time
import datetime
import getopt, sys
import traceback
import com.xhaus.jyson.JysonCodec as json
import sys

import logging
from logging.config import fileConfig
fileConfig('probespawner.ini')
logger = logging.getLogger(__name__)

configurationLiterals = ["verbose", "help", "configuration="];
configurationHelp = ["Increase verbosity of messages", "Display help", "JSON configuration file"];
configurationFile = "some.feeder.config.json";
probeListStr      = "databaseprobe.py,jmxprobe.py";
json_string       = "theres is no JSON"

def usage():
        print "USAGE:"
        for index in range(len(configurationLiterals)):
                print "  --" + configurationLiterals[index] + " : " + configurationHelp[index];

def shutdown_and_await_termination(pool, timeout):
    pool.shutdown()
    try:
        if not pool.awaitTermination(timeout, TimeUnit.SECONDS):
            pool.shutdownNow()
            if (not pool.awaitTermination(timeout, TimeUnit.SECONDS)):
                print >> sys.stderr, "Pool did not terminate"
    except InterruptedException, ex:
        # (Re-)Cancel if current thread also interrupted
        pool.shutdownNow()
        # Preserve interrupt status
        Thread.currentThread().interrupt()

try:
    opts, args = getopt.getopt(sys.argv[1:], "vhc:", configurationLiterals)
except getopt.GetoptError, err:
	print str(err)
	usage()
	sys.exit(2)

for o, a in opts:
	if o == "-v":
		verbose = True
	if o in ("-h", "--help"):
		usage()
	elif o in ("-c", "--configuration"):
		configurationFile = a
		#TODO: split and load libs
	else:
		assert False, "Unknown option"

try:
	with open(configurationFile) as data_file:
		json_string = data_file.read()   
except EnvironmentError, err:
	print str(err)
	usage()
	sys.exit(3)

try:
	config = json.loads(json_string.decode('utf-8'))
except:
	print "JSON from file '" + configurationFile + "' is malformed."
	e = sys.exc_info()[0]
	print str(e)
	sys.exit(4)

pool = Executors.newFixedThreadPool(len(config["input"]))
ecs  = ExecutorCompletionService(pool)

def scheduler(roots):
    for inputConfig in roots:
        yield inputConfig

def getClassByName(module, className):
    if not module:
        if className.startswith("services."):
            className = className.split("services.")[1]
        l = className.split(".")
        m = __services__[l[0]]
        return getClassByName(m, ".".join(l[1:]))
    elif "." in className:
        l = className.split(".")
        m = getattr(module, l[0])
        return getClassByName(m, ".".join(l[1:]))
    else:
        return getattr(module, className)

for inputConfig in scheduler(config["input"]):
    outputs = {}
    for output in config[inputConfig]["output"]:
        outputs[output] = config[output]
    module = config[inputConfig]['probemodule']['module']
    name = config[inputConfig]['probemodule']['name']
    #TODO: consider input singletons 
    #from config[inputConfig]['probemodule']['module'] import config[inputConfig]['probemodule']['name']
    probemodule = __import__(module, globals(), locals(), [''], -1)
    probeclass = getClassByName(probemodule, name)
    obj = probeclass(config[inputConfig], outputs)
    ecs.submit(obj)

workingProbes = len(config["input"])
#TODO: handle signals for stopping, thread exits, etc.
while workingProbes > 0:
	result = "No result"
	try:
		result = ecs.take().get()
	except InterruptedException, ex:
		pprint(ex)
		traceback.print_exc()
	except ExecutionException, ex:
		pprint(ex)
		traceback.print_exc()
	print result
	workingProbes -= 1

print "shutting threadpool down..."
shutdown_and_await_termination(pool, 5)
print "done"
sys.exit(1)

