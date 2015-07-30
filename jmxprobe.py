# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

from dummyprobe import DummyProbe

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.openmbean.CompositeDataSupport;
import javax.management.openmbean.CompositeType;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;
import re

from pprint import pprint
import time
import datetime
import sys
from array import array
import com.xhaus.jyson.JysonCodec as json

import logging
logger = logging.getLogger(__name__)

class JMXProbe(DummyProbe):
    def initialize(self):
        self.attributes = []
        self.operations = []
        self.mbeanProbes = []
        username = self.getInputProperty("username")
        password = self.getInputProperty("password")
        host = self.getInputProperty("host")
        port = self.getInputProperty("port")
        self.queries = None
        if self.getInputProperty("metricsfile"):
            logger.info("loading %s", self.getInputProperty("metricsfile"))
            stream = open(self.getInputProperty("metricsfile"))
            if type(stream) is not file:
                raise TypeError,'Argument should be a file object!'
                # Check for the opened mode
            if stream.mode != 'r':
                raise ValueError,'Stream should be opened in read-only mode!'
            try:
                lines = stream.readlines()
                lineno=0
                i = iter(lines)
                for line in i:
                    lineno += 1
                    line = line.strip()
                    # Skip null lines
                    if not line: continue
                    # Skip lines which are comments
                    if line[0] == '#': continue
                    obj = line.split("/",1)
                    self.mbeanProbes[len(self.mbeanProbes):] = { "name" : obj[0], "attribute" : obj[1], "type": "attribute" }
            except IOError, e:
                raise
        else:
            #TODO: cleanup here, iterate once, avoid appends, etc., maybe change datastructure to manage both getAttribute and invoke
            logger.info("Loading objects from metrics field")
            lineno=0
            if self.getInputProperty("metrics") != None:
                for line in self.getInputProperty("metrics"):
                    lineno += 1
                    obj = line.split("/")
                    oname = obj[0]
                    oattr = obj[1]
                    if len(obj) > 2:
                        oattr = obj.pop()
                        oname = "/".join(obj)
                    logger.debug("Got attribute %s from %s (%d)", oattr, oname, len(obj))
                    self.mbeanProbes[len(self.mbeanProbes):] = [{ "name" : oname, "attribute" : oattr, "type": "attribute" }]
            logger.info("Loading objects from attributes field")
            lineno=0
            #TODO: parse object URI correctly, which means review above oattr/oname and apply same BETTER strategy below
            if self.getInputProperty("attributes") != None:
                for line in self.getInputProperty("attributes"):
                    lineno += 1
                    obj = line.split("/",1)
                    logger.debug("Got attribute %s from %s", obj[1], obj[0])
                    self.mbeanProbes[len(self.mbeanProbes):] = [{ "name" : obj[0], "attribute" : obj[1], "type": "attribute" }]
            #TODO: add invoke capabilities http://docs.oracle.com/cd/E19717-01/819-7758/gcitp/index.html
            logger.info("Loading objects from operations field")
            if self.getInputProperty("operations") != None:
                for operationObject in self.getInputProperty("operations"):
                    logger.debug("Got operation: %s", operationObject['name'])
                    obj = operationObject['name'].split("/",1)
                    operationObject['name'] = obj[0]
                    operationObject['attribute'] = obj[1]
                    operationObject['type'] = "operation"
                    if 'params' not in operationObject:
                        operationObject['params'] = None
                    if 'signatures' not in operationObject:
                        operationObject['signatures'] = None
                    self.mbeanProbes[len(self.mbeanProbes):] = [operationObject]

        #connect to JMX server
        ad=array(java.lang.String,[username,password])
        n = java.util.HashMap()
        n.put (javax.management.remote.JMXConnector.CREDENTIALS, ad);
        logger.info("Got %d mbeanProbes", len(self.mbeanProbes))
        logger.info("Connecting to %s@%s:%d", username, host, port)
        self.urlstring = "service:jmx:rmi:///jndi/rmi://" + host + ":" + str(port) + "/jmxrmi"
        self.jmxurl = javax.management.remote.JMXServiceURL(self.urlstring)
        self.testme = javax.management.remote.JMXConnectorFactory.connect(self.jmxurl,n)
        self.connection = self.testme.getMBeanServerConnection()

    def cleanup(self):
        self.testme.close()

    def getCompositeDataSupportDict(self, value):
        jsonDict = {}
        for key in value.getCompositeType().keySet():
            jsonDict[key] = {}
            self.setupValue(jsonDict[key], value.get(key))
        return jsonDict

    #TODO: such ugly: rethink and redo
    def setupValue(self, value, jsonDict):
        if (value.__class__.__name__ == "wtf"):
            return jsonDict
        elif (value.__class__.__name__ == "CompositeDataSupport"):
            for key in value.getCompositeType().keySet():
                val = value.get(key)
                if val != None:
                    jsonDict[str(key)] = self.setupValue(val, {})
            return jsonDict
        elif (value.__class__.__name__ == "array"):
            data = []
            dataType = "array"
            i = iter(value)
            for obj in i:
                data.append(self.setupValue(obj, {}))
        elif (value.__class__.__name__ == "float"):
            dataType = "float"
            data = value
        elif (value.__class__.__name__ == "long"):
            dataType = "long"
            data =  value
        elif (value.__class__.__name__ == "int"):
            dataType = "int"
            data = value * 1
        else:
            dataType = "string"
            data = str(value)

        if len(jsonDict) == 0:
            return data

        try:
            data
            if len(jsonDict) > 0:
                jsonDict[dataType] = data
                if (dataType == "int") or (dataType == "long") or (dataType == "float"):
                    jsonDict['number'] = data + 0.0
                jsonDict['value'] = str(data)
        except Exception, ex:
            logger.debug(ex)
            return jsonDict
        return jsonDict

    #TODO: redo this, chaos
    def queryJmx(self, obj):
        attributeName = obj['attribute']
        jsonDict = {}
        jsonDict['jmxurl'] = self.urlstring
        jsonDict['@timestamp'] = self.cycle["startdt"]
        jsonDict['name'] = obj['name']
        jsonDict['attribute'] = obj['attribute']
        if obj["type"] == "attribute":
            value = self.connection.getAttribute(javax.management.ObjectName(obj['name']), obj['attribute'])
            logger.debug(value)
        else:
            value = self.connection.invoke(javax.management.ObjectName(obj['name']), obj['attribute'], obj['params'], obj['signatures'])
        
        #TODO: such crap, this class shoul not import re
        if isinstance(self.getInputProperty("replaceInValue"), list):
            for i in self.getInputProperty("replaceInValue"):
                (pattern, repl) = i
                for key in jsonDict:
                    if isinstance(jsonDict[key], str) or isinstance(jsonDict[key], unicode):
                        jsonDict[key] = re.sub(pattern, repl, jsonDict[key])

        if self.getInputProperty("compositeDataToManyRecords") == True and value.__class__.__name__ == "CompositeDataSupport":
            for key in value.getCompositeType().keySet():
                val = value.get(key)
                if val != None:
                    jsonDict['attribute'] = obj['attribute'] + "." + key
                    self.setupValue(val, jsonDict)
                    self.processData(jsonDict)
        else:
            self.setupValue(value, jsonDict)

        if self.getInputProperty("arrayElementsToRecord"):
            if 'array' in jsonDict:
                i = iter(jsonDict['array'])
                for aobj in i:
                    aobj['jmxurl'] = self.urlstring
                    aobj['@timestamp'] = self.cycle["startdt"]
                    aobj['name'] = obj['name']
                    aobj['attribute'] = obj['attribute']
                    self.processData(aobj)
                return True
            else:
                self.processData(jsonDict)
                return False
        return self.processData(jsonDict)

    def tick(self):
        #TODO: this thing with operations and attributes is a messup, repeated code everywhere: REDO whole class
        i = iter(self.mbeanProbes)
        for obj in i:
            try:
                self.queryJmx(obj)
            #except javax.management.InstanceNotFoundException, e:
            except Exception, ex:
                logger.error("Caught exception getting value: %s", str(obj))
                logger.error(ex)
                try:
                    self.attributes.remove(obj)
                    logger.error("Failed to get instace of request object. Removing %s", str(obj))
                    sys.exit(100) #see TODO: above, handle this and try to recover is it existed sometime in the past
                except ValueError:
                    logger.debug("ValueError")
                    pass # or scream: thing not in some_list!
                except AttributeError:
                    logger.debug("AttributeError")
                    pass # call security, some_list not quacking like a list!

        if (len(self.mbeanProbes) < 1):
            raise "No objects left, quietly leaving work"


        logger.info("tick")