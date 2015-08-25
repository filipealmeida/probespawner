
from org.apache.log4j import *

import javax.management.ObjectName as ObjectName
import javax.management.MBeanInfo as MBeanInfo
import javax.management.MBeanAttributeInfo as MBeanAttributeInfo
import weblogic.management.runtime.ServerRuntimeMBean
import weblogic.management.Helper
import java.util.Set
from urlparse import urljoin
from cmd import Cmd
import inspect
import org.joda.time.DateTime as DateTime
import org.json.simple.JSONValue as JSONValue
import re
import sys
import time
import os

def setupValue(value, jsonDict):
    if (value.__class__.__name__ == "wtf"):
        return jsonDict
    elif (value.__class__.__name__ == "CompositeDataSupport"):
        for key in value.getCompositeType().keySet():
            val = value.get(key)
            if val != None:
                jsonDict[str(key)] = setupValue(val, {})
        return jsonDict
    elif (value.__class__.__name__ == "array"):
        data = []
        dataType = "array"
        i = iter(value)
        for obj in i:
            data.append(setupValue(obj, {}))
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

logger = Logger.getLogger(__name__)
if os.path.isfile(sys.path[0] + "/log4j.properties"):
    PropertyConfigurator.configure(sys.path[0] + "/log4j.properties")
else:
    PropertyConfigurator.configure("log4j.properties")

logger.info(__name__)

try:
    H = open(sys.argv[1], 'rb')
    json_string = ""
    for buf in H:
        json_string = json_string + buf
    H.close()
except EnvironmentError, err:
    print "Failed opening " + sys.argv[1]
    print str(err)
    usage()
    sys.exit(3)

config=JSONValue.parse(json_string);
if ("alias" in config):
    aliasPrefix = config['alias'] + "."
else:
    aliasPrefix = ""
user = config.get("username")
pwd = config.get("password")
url = config.get("url")
sleepTime = config.get("interval")
#print pwd
localHome = weblogic.management.Helper.getAdminMBeanHome( user, pwd, url );
remote = localHome.getMBeanServer()

mbeanProbes = []

for query in config.get("queries"):
    if 'object_name' not in query:
        logger.warn("Bad configuration, missing 'object_name'")
        continue
    match = re.search(r'type=([a-zA-Z0-9$.]+)', query['object_name'], re.I)
    if match:
        objtype = match.group(1)
        objectList = localHome.getMBeansByType(objtype)
        mbeanIterator = objectList.iterator();
        while (mbeanIterator.hasNext()):
            mbean = mbeanIterator.next()
            info = mbean.getMBeanInfo()
            if 'attributes' in query:
                attributes = query['attributes']
            else:
                attributes = info.getAttributes()
            for attribute in attributes:
                try:
                    if (attribute.__class__.__name__ == "weblogic.management.tools.AttributeInfo"):
                        attributeName = attribute.getName()
                    else:
                        attributeName = attribute
                    logger.info("Setting up: " + attributeName + " for " + str(mbean))
                    value = mbean.getAttribute(attributeName)
                    mbeanProbes[len(mbeanProbes):] = [{ 'mbean':mbean, 'attribute': attributeName, 'objtype':objtype }]
                except Exception, ex:
                    logger.warn(ex)
    else:
        logger.warn("No dice for " + query['object_name'])

if (len(mbeanProbes) <= 0):
    logger.error("No probes, exiting...")
    sys.exit(1000)
#main loop
while (True):
    start = time.time()
    for query in mbeanProbes:
        mbean = query['mbean']
        attribute = query['attribute']
        value = mbean.getAttribute(attribute)
        obj = { '@timestamp': str(DateTime()), 'value': value, 'attribute': attribute }
        #obj['location'] = mbean.getLocation()
        obj['location'] = mbean.getObjectName().getLocation()
        obj['name'] = mbean.getName()
        obj['type'] = mbean.getType()
        obj['shipper'] = "wls81x"
        obj['alias'] = aliasPrefix + obj['type'] + "." + obj['name'] + "." + attribute
        setupValue(value, obj)
        #print JSONValue.toJSONString(obj);#encases keys and string in single quotes, bad bad JSON
        out = []
        extrakeys = re.findall(r'((\w+)=(\w+)),?', obj['name'])
        for parts in extrakeys:
            (group, variable, value) = parts
            out[variable.lower()] = value
        for key in obj:
            val = obj[key]
            if isinstance(val, str) or isinstance(val, unicode):
                val = '"' + val + '"'
            out[len(out):] = ['"' + key + '":' + str(val)]
        print "{" + ",".join(out) + "}"
    elapsed = time.time() - start
    effectiveSleepTime = sleepTime - elapsed
    logger.info("Sleeping for " + str(effectiveSleepTime) + "s")
    if effectiveSleepTime > 0:
        time.sleep(effectiveSleepTime)

sys.exit(0)
