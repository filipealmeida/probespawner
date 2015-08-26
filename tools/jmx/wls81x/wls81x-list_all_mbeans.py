
import javax.management.ObjectName as ObjectName
import javax.management.MBeanInfo as MBeanInfo
import javax.management.MBeanAttributeInfo as MBeanAttributeInfo
import weblogic.management.runtime.ServerRuntimeMBean
import weblogic.management.Helper
import java.util.Set
import org.json.simple.JSONValue as JSONValue
import re
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

localHome = weblogic.management.Helper.getAdminMBeanHome( user, pwd, url );
remote = localHome.getMBeanServer()
print(remote)
objectList = localHome.getAllMBeans();
mbeanIterator = objectList.iterator();
while (mbeanIterator.hasNext()):
    print "=============================================="
    mbean = mbeanIterator.next()
    print (mbean)
    name = mbean.getObjectName()
    print (name)
    info = mbean.getMBeanInfo()
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
