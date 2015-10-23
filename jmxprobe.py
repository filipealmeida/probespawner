# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

#
# _____ ___  ____   ___    
#|_   _/ _ \|  _ \ / _ \ _ 
 # | || | | | | | | | | (_)
 # | || |_| | |_| | |_| |_ 
 # |_| \___/|____/ \___/(_)
# Redo the JMXProbe, consider make a new one, remember cooljmxprobe?
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
import javax.management.MBeanInfo;

import uuid
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
        self.mbeanDict = {}
        username = self.getInputProperty("username")
        password = self.getInputProperty("password")
        host = self.getInputProperty("host")
        port = self.getInputProperty("port")
        self.queries = None

        if self.getInputProperty("alias") != None:
            self.alias = self.getInputProperty("alias")
        else:
            self.alias = host + "_" + str(port)
        #connect to JMX server
        ad=array(java.lang.String,[username,password])
        n = java.util.HashMap()
        n.put (javax.management.remote.JMXConnector.CREDENTIALS, ad);

        #Jboss initial context: jndi.java.naming.provider.url=jnp://localhost:1099/
        #jndi.java.naming.factory.url=org.jboss.naming:org.jnp.interfaces
        #jndi.java.naming.factory.initial=org.jnp.interfaces.NamingContextFactory
        if self.getInputProperty("factory") != None:
            logger.info("Factory initialized %s = %s", javax.management.remote.JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, self.getInputProperty("factory"))
            n.put(javax.management.remote.JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, self.getInputProperty("factory"))
            n.put(javax.naming.InitialContext.SECURITY_PRINCIPAL, username);
            n.put(javax.naming.InitialContext.SECURITY_CREDENTIALS, password);
        
        if self.getInputProperty("url") != None:
            self.urlstring = self.getInputProperty("url")
        else:
            self.urlstring = "service:jmx:rmi:///jndi/rmi://" + host + ":" + str(port) + "/jmxrmi"
        logger.info("Connecting to %s", self.urlstring)
        self.jmxurl = javax.management.remote.JMXServiceURL(self.urlstring)
        self.testme = javax.management.remote.JMXConnectorFactory.connect(self.jmxurl,n)
        self.connection = self.testme.getMBeanServerConnection()
        self.buildJMXProbesFromQueries()
        self.backwardCompatibilityConfiguration()
        self.computeAliases()
        self.optimizeQueries()
        logger.info("Got %d mbeanProbes", len(self.mbeanProbes))

    def backwardCompatibilityConfiguration(self):
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
                    objuuid = uuid.uuid1()
                    self.mbeanDict[objuuid] = operationObject
                    self.mbeanProbes[len(self.mbeanProbes):] = [operationObject]

    def computeAlias(self, obj):
        #TODO: UGLYYYYYYYYYYYYYY
        if 'object_alias' in obj:
            objtype = "${type}";
            objname = "${name}";
            objlocation = "${objlocation}"
            match = re.search(r'type=([a-zA-Z0-9$.]+)',str(obj['name']), re.I)
            if match:
                objtype = match.group(1)
            match = re.search(r'name=([a-zA-Z0-9$.]+)',str(obj['name']), re.I)
            if match:
                objname = match.group(1)
            match = re.search(r'location=([a-zA-Z0-9$.]+)',str(obj['name']), re.I)
            if match:
                objlocation = match.group(1)
            objalias = re.sub('\${type}', objtype, obj['object_alias'])
            objalias = re.sub('\${name}', objname, objalias)
            objalias = re.sub('\${location}', objlocation, objalias)
            prefix = self.alias + "." + objalias
        else:
            prefix = self.alias + "." + re.sub(r'[a-zA-Z$0-9]+=','.',str(obj['name']))
            prefix = re.sub(r'[:,]','',prefix)
        prefix = re.sub(r'^\.','',prefix)
        suffix = str(obj['attribute'])
        return prefix + "." + suffix

    def computeAliases(self):
        #TODO: handle operations
        #, "alias": str(element.getClassName()) + "." + str(attribute.getName())
        i = iter(self.mbeanProbes)
        for obj in i:
            obj['alias'] = self.computeAlias(obj)

    def optimizeQueries(self):
        logger.info("Optimizing queries.")
        #TODO: handle operations
        #, "alias": str(element.getClassName()) + "." + str(attribute.getName())
        i = iter(self.mbeanProbes)
        for obj in i:
            if obj['type'] == "attribute":
                if obj['name'] not in self.mbeanDict:
                    self.mbeanDict[obj['name']] = {}
                    self.mbeanDict[obj['name']]['name'] = obj['name']
                    self.mbeanDict[obj['name']]['attributes'] = []
                    self.mbeanDict[obj['name']]['parts'] = {}
                    self.mbeanDict[obj['name']]['type'] = 'attribute'
                    extrakeys = re.findall(r'((\w+)=(\w+)),?', obj['name'])
                    for parts in extrakeys:
                        (group, variable, value) = parts
                        self.mbeanDict[obj['name']]["object_" + variable.lower()] = value
                        self.mbeanDict[obj['name']]['parts'][variable.lower()] = value
                self.mbeanDict[obj['name']]['attributes'][len(self.mbeanDict[obj['name']]['attributes']):] = [obj['attribute']]

    def buildJMXProbesFromQueries(self):
        if self.getInputProperty("queries") != None:
            logger.info("Processing configured queries")
            for queryObject in self.getInputProperty("queries"):
                try:
                    self.queryObjectToMbeanProbe(queryObject)
                except:
                    logger.warning("%s Failure grabbing attribute in %s", self.getInputProperty("__inputname__"), queryObject['object_name']);

    #TODO: [{'attribute': 'ObjectPendingFinalizationCount', 'type': 'attribute', 'alias': 'sun.management.MemoryImpl.ObjectPendingFinalizationCount', 'name': 'java.lang:type=Memory'}, {'attribute': 'HeapMemoryUsage', 'type': 'attribute', 'alias': 'sun.management.MemoryImpl.HeapMemoryUsage', 'name': 'java.lang:type=Memory'}, {'attribute': 'NonHeapMemoryUsage', 'type': 'attribute', 'alias': 'sun.management.MemoryImpl.NonHeapMemoryUsage', 'name': 'java.lang:type=Memory'}, {'attribute': 'Verbose', 'type': 'attribute', 'alias': 'sun.management.MemoryImpl.Verbose', 'name': 'java.lang:type=Memory'}, {'attribute': 'ObjectName', 'type': 'attribute', 'alias': 'sun.management.MemoryImpl.ObjectName', 'name': 'java.lang:type=Memory'}, {'attribute': 'StartTime', 'type': 'attribute', 'alias': 'sun.management.RuntimeImpl.StartTime', 'name': 'java.lang:type=Runtime'}, {'attribute': 'Uptime', 'type': 'attribute', 'alias': 'sun.management.RuntimeImpl.Uptime', 'name': 'java.lang:type=Runtime'}, {'attribute': 'CollectionCount', 'type': 'attribute', 'alias': 'sun.management.GarbageCollectorImpl.CollectionCount', 'name': 'java.lang:type=GarbageCollector,name=ConcurrentMarkSweep'}, {'attribute': 'CollectionTime', 'type': 'attribute', 'alias': 'sun.management.GarbageCollectorImpl.CollectionTime', 'name': 'java.lang:type=GarbageCollector,name=ConcurrentMarkSweep'}, {'attribute': 'CollectionCount', 'type': 'attribute', 'alias': 'sun.management.GarbageCollectorImpl.CollectionCount', 'name': 'java.lang:type=GarbageCollector,name=ParNew'}, {'attribute': 'CollectionTime', 'type': 'attribute', 'alias': 'sun.management.GarbageCollectorImpl.CollectionTime', 'name': 'java.lang:type=GarbageCollector,name=ParNew'}, {'attribute': 'Count', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.Count', 'name': 'java.nio:type=BufferPool,name=direct'}, {'attribute': 'TotalCapacity', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.TotalCapacity', 'name': 'java.nio:type=BufferPool,name=direct'}, {'attribute': 'MemoryUsed', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.MemoryUsed', 'name': 'java.nio:type=BufferPool,name=direct'}, {'attribute': 'Name', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.Name', 'name': 'java.nio:type=BufferPool,name=direct'}, {'attribute': 'ObjectName', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.ObjectName', 'name': 'java.nio:type=BufferPool,name=direct'}, {'attribute': 'Count', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.Count', 'name': 'java.nio:type=BufferPool,name=mapped'}, {'attribute': 'TotalCapacity', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.TotalCapacity', 'name': 'java.nio:type=BufferPool,name=mapped'}, {'attribute': 'MemoryUsed', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.MemoryUsed', 'name': 'java.nio:type=BufferPool,name=mapped'}, {'attribute': 'Name', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.Name', 'name': 'java.nio:type=BufferPool,name=mapped'}, {'attribute': 'ObjectName', 'type': 'attribute', 'alias': 'sun.management.ManagementFactoryHelper$1.ObjectName', 'name': 'java.nio:type=BufferPool,name=mapped'}]
    #TODO: duplicate code, solve
    def queryObjectToMbeanProbe(self, queryObject):
        logger.info("Preparing %s", queryObject['object_name'])
        count = 0
        objectList = self.connection.queryMBeans(javax.management.ObjectName(queryObject['object_name']), None)
        for element in objectList:
            info = self.connection.getMBeanInfo(element.getObjectName())
            attrInfo = info.getAttributes()
            for attribute in attrInfo:
                obj = None
                if 'attributes' in queryObject:
                    if attribute.getName() in queryObject['attributes']:
                        logger.info("Match on selected attribute, adding+ %s/%s", element.getObjectName(), attribute.getName())
                        value = self.connection.getAttribute(element.getObjectName(), attribute.getName())
                        obj = { "name" : str(element.getObjectName()), "attribute" : str(attribute.getName()), "type": "attribute" }
                else:
                    logger.info("%s::All attributes selected, adding %s/%s", self.getInputProperty("__inputname__"), element.getObjectName(), attribute.getName())
                    value = self.connection.getAttribute(element.getObjectName(), attribute.getName())
                    obj = { "name" : str(element.getObjectName()), "attribute" : str(attribute.getName()), "type": "attribute" }
                if obj != None:
                    if 'object_alias' in queryObject:
                        obj['object_alias'] = queryObject['object_alias']
                    if 'object_value_to_jmxquery' in queryObject and queryObject['object_value_to_jmxquery'] == True:
                        #com.bea:ServerRuntime=box1,Name=ThreadPoolRuntime,Type=ThreadPoolRuntime
                        value = self.connection.getAttribute(javax.management.ObjectName(obj['name']), obj['attribute'])
                        newQueryObject = {}
                        newQueryObject['object_name'] = str(value)
                        if 'whitelist' in queryObject and len(queryObject['whitelist']) > 0:
                            newQueryObject['attributes'] = queryObject['whitelist']
                        if 'blacklist' in queryObject and len(queryObject['blacklist']) > 0:
                            logger.warning("TODO: implement blacklist")
                        logger.warning(value)
                        logger.warning("trying to add %s", newQueryObject['object_name']);
                        self.queryObjectToMbeanProbe(newQueryObject)
                    else:
                        self.mbeanProbes[len(self.mbeanProbes):] = [obj]
                        count+=1
                #value = self.connection.getAttribute(javax.management.ObjectName(obj['name']), obj['attribute'])
        logger.info("Added %d queries for %s", count, queryObject['object_name'])

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
    def queryJmx(self, key):
        obj = self.mbeanDict[key]
        if "attributes" in obj:
            attributeValues = self.connection.getAttributes(javax.management.ObjectName(key), obj['attributes'])
            for value in attributeValues:
                obj['attribute'] = value.getName(); 
                obj['alias'] = self.computeAlias(obj)
                self.handleResponse(obj, value.getValue())
        elif obj["type"] == "attribute":
            value = self.connection.getAttribute(javax.management.ObjectName(obj['name']), obj['attribute'])
            self.handleResponse(obj, value)
        else:
            value = self.connection.invoke(javax.management.ObjectName(obj['name']), obj['attribute'], obj['params'], obj['signatures'])
            self.handleResponse(obj, value)

    #TODO: redo all class, it has just reached the point where you can't distinguish this from a salad
    def handleResponse(self, obj, value):
        jsonDict = {}
        jsonDict['jmxurl'] = self.urlstring
        jsonDict['@timestamp'] = self.cycle["startdt"]
        jsonDict['name'] = obj['name']
        jsonDict['attribute'] = obj['attribute']
        jsonDict['alias'] = obj['alias']
        if 'parts' in self.mbeanDict[obj['name']]:
            for key in self.mbeanDict[obj['name']]['parts']:
                jsonDict[key] = self.mbeanDict[obj['name']]['parts'][key]
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
                    jsonDict['alias'] = obj['alias'] + "." + key
                    self.setupValue(val, jsonDict)
                    self.processData(jsonDict)
            return True
        else:
            self.setupValue(value, jsonDict)

        if self.getInputProperty("arrayElementsToRecord"):
            if 'array' in jsonDict:
                i = iter(jsonDict['array'])
                for aobj in i:
                    if isinstance(aobj, dict):
                        aobj['jmxurl'] = self.urlstring
                        aobj['@timestamp'] = self.cycle["startdt"]
                        aobj['name'] = obj['name']
                        aobj['attribute'] = obj['attribute']
                        aobj['alias'] = obj['alias']
                        self.processData(aobj)
                    elif isinstance(aobj, str) or isinstance(aobj, unicode):
                        oobj = {}
                        oobj['jmxurl'] = self.urlstring
                        oobj['@timestamp'] = self.cycle["startdt"]
                        oobj['name'] = obj['name']
                        oobj['attribute'] = obj['attribute']
                        oobj['alias'] = obj['alias']
                        oobj['string'] = aobj
                        self.processData(oobj)
                return True
            else:
                self.processData(jsonDict)
                return False
        return self.processData(jsonDict)

    def tick(self):
        #TODO: this thing with operations and attributes is a messup, repeated code everywhere: REDO whole class
        #i = iter(self.mbeanDict)
        for obj in self.mbeanDict:
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