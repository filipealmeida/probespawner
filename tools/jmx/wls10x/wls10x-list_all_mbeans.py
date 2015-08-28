
import javax.management.ObjectName as ObjectName
import javax.management.MBeanInfo as MBeanInfo
import javax.management.MBeanAttributeInfo as MBeanAttributeInfo
import javax.management.remote.JMXConnector

import javax.management.MBeanServerConnection;

import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;


import java.util.Map
import org.json.simple.JSONValue as JSONValue
from array import array
import sys

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

user = config.get("username")
pwd = config.get("password")
url = config.get("url")
factory = config.get("factory")
print factory
ad=array(java.lang.String,[user,pwd])
n = java.util.HashMap()
n.put(javax.management.remote.JMXConnector.CREDENTIALS, ad);
n.put(javax.management.remote.JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, factory)
n.put(javax.naming.InitialContext.SECURITY_PRINCIPAL, user);
n.put(javax.naming.InitialContext.SECURITY_CREDENTIALS, pwd);
jmxurl = javax.management.remote.JMXServiceURL(url)
localHome = javax.management.remote.JMXConnectorFactory.connect(jmxurl, n)
remote = localHome.getMBeanServerConnection()
print(remote)
objectList = remote.queryMBeans(None, None);
mbeanIterator = objectList.iterator();
while (mbeanIterator.hasNext()):
    print "=============================================="
    mbean = mbeanIterator.next()
    print (mbean)
    name = mbean.getObjectName()
    print (name)
    info = remote.getMBeanInfo(name)
    print (info)
    attributes = info.getAttributes()
    for attribute in attributes:
        name = attribute.getName()
        print " + " + name
        print attribute
        try:
            value = mbean.getAttribute(attribute.getName())
            print " +- " + str(value)
        except:
            print " +- failed getting value for attribute: " + name
    operations = info.getOperations()
