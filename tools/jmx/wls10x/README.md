# Get all MBeans from Weblogic 10.x+ using jython remotely through the administration server

```
CLASSPATH=wlclient.jar:wljmxclient.jar:json_simple-1.1.jar jython wls10x-list_all_mbeans.py wls10x.json
weblogic.management.remote
javax.management.remote.rmi.RMIConnector$RemoteMBeanServerConnection@8b586a
==============================================
weblogic.diagnostics.archive.DataRetirementTaskImpl[com.bea:ServerRuntime=myNode1,Name=ScheduledDataRetirement_3620,Location=myNode1,Type=DataRetirementTaskRuntime]
com.bea:ServerRuntime=myNode1,Name=ScheduledDataRetirement_3620,Location=myNode1,Type=DataRetirementTaskRuntime
javax.management.modelmbean.ModelMBeanInfoSupport[description=<p>Exposes monitoring information about a potentially long-running request for the data retirement task. Remote clients, as well as clients running within a server, can access this information.</p> <p> , attributes=[ModelMBeanAttributeInfo: Parent ; Description: <p>Return the immediate parent for this MBean</p>  ; Types: javax.management.ObjectName ; isReadable: true ; isWritable: true ; Descriptor: com.bea.description=<p>Return the immediate parent for this MBean</p> , com.bea.relationship=reference, com.bea.unharvestable=(true), descriptorType=Attribute, displayName=Parent, interfaceclassname=weblogic.management.WebLogicMBean, Name=Parent, ModelMBeanAttributeInfo: Description ; Description:   ; Types: java.lang.String ; isReadable: true ; isWritable: false ; Descriptor: com.bea.description= , descriptorType=Attribute, displayName=Description, Name=Description, ModelMBeanAttributeInfo: Type ; Description: <p>Returns the type of the MBean.</p>  ; Types: java.lang.String ; isReadable: true ; isWritable: false ; Descriptor: com.bea.description=<p>Returns the type of the MBean.</p> , com.bea.unharvestable=(true), descriptorType=Attribute, displayName=Type, Name=Type, ModelMBeanAttributeInfo: Running ; Description:   ; Types: java.lang.Boolean ; isRead (...)
(...)
```