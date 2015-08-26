# Get all MBeans from Weblogic 8.1.x using jython remotely through the administration server

## Files:

### wls81x.py 
Periodically probes weblogic 8.1 objects and outputs their values to stdout in json format

Requires classpath with the following jars: webserviceclient.jar:weblogic.jar:json_simple-1.1.jar:joda-time-1.4.jar:log4j-1.2.17.jar

Gets a json has first argument such as this:
```
{
      "url":"t3://127.0.0.1:7001",
      "username": "weblogic",
      "password": "weblogic",
      "alias": "myproject",
      "queries" : [
        {
          "object_name" : "java.lang:type=JVMRuntime",
          "attributes" : [ "HeapSizeCurrent", "HeapFreeCurrent" ]
        }, {
          "object_name" : "java.lang:type=ServerRuntime",
          "attributes": [ "State", "OpenSocketsCurrentCount", "SocketsOpenedTotalCount" ]
        }, {
          "object_name" : "com.bea:type=ExecuteQueueRuntime",
          "attributes": [ "ServicedRequestTotalCount", "ExecuteThreadCurrentIdleCount",  "ExecuteThreadTotalCount", "PendingRequestCurrentCount", "PendingRequestCurrentCount", "ServicedRequestTotalCount", "StuckExecuteThreads" ]
        }, {
          "object_name" : "com.bea:type=JDBCConnectionPoolRuntime",
          "attributes": ["ActiveConnectionsHighCount", "LeakedConnectionCount", "PrepStmtCacheMissCount", "WaitingForConnectionHighCount", "FailuresToReconnectCount", "WaitSecondsHighCount", "ConnectionDelayTime", "ConnectionsTotalCount", "WaitingForConnectionCurrentCount", "ActiveConnectionsCurrentCount", "MaxCapacity", "CurrCapacity"]
        }
       ],
       "interval": 20
}
```

### wls81x-list_all_mbeans.py
Lists all mbean info and values for a weblogic 8.1, prints to stdout

Requires classpath with the following jars: webserviceclient.jar:weblogic.jar:json_simple-1.1.jar:joda-time-1.4.jar:log4j-1.2.17.jar

Gets a json has first argument such as this:
```
{
      "url":"t3://127.0.0.1:7001",
      "username": "weblogic",
      "password": "weblogic"
}
```

## Running wls81x.py

First and foremost, you"ll need obsolete versions of JAVA and Jython to make this work.

Tests were done with Jython 2.2.1 on java1.4.2_19

Hit runme.sh to test on weblogic:weblogic@localhost:7001

This example will output the attribute values configured in wls81x.json file in JSON to STDOUT, namely some interesting attributes of JVMRuntime, ServerRuntime, ExecuteQueueRuntime and JDBCConnectionPoolRuntime.

The configuration file is self explanatory but you should know that only "type" (as in "java.lang:type=JVMRuntime") will be used to get the mbean list through weblogic.management.Helper.getAdminMBeanHome( user, pwd, url ).getMBeansByType( *type* ):
```
{
      "url":"t3://127.0.0.1:7001",
      "username": "weblogic",
      "password": "weblogic",
      "alias": "myproject",
      "queries" : [
        {
          "object_name" : "java.lang:type=JVMRuntime",
          "attributes" : [ "HeapSizeCurrent", "HeapFreeCurrent" ]
        }, {
          "object_name" : "java.lang:type=ServerRuntime",
          "attributes": [ "State", "OpenSocketsCurrentCount", "SocketsOpenedTotalCount" ]
        }, {
          "object_name" : "com.bea:type=ExecuteQueueRuntime",
          "attributes": [ "ServicedRequestTotalCount", "ExecuteThreadCurrentIdleCount",  "ExecuteThreadTotalCount", "PendingRequestCurrentCount", "PendingRequestCurrentCount", "ServicedRequestTotalCount", "StuckExecuteThreads" ]
        }, {
          "object_name" : "com.bea:type=JDBCConnectionPoolRuntime",
          "attributes": ["ActiveConnectionsHighCount", "LeakedConnectionCount", "PrepStmtCacheMissCount", "WaitingForConnectionHighCount", "FailuresToReconnectCount", "WaitSecondsHighCount", "ConnectionDelayTime", "ConnectionsTotalCount", "WaitingForConnectionCurrentCount", "ActiveConnectionsCurrentCount", "MaxCapacity", "CurrCapacity"]
        }
       ],
       "interval": 20
}


```

The output is intended to be gluable to logstash for indexing.

Output sample (elasticsearch awful but friendly):
```
...
{"name": "somePool", "attribute": "WaitingForConnectionCurrentCount", "number": 0.0, "alias": "myproject.JDBCConnectionPoolRuntime.somePool.WaitingForConnectionCurrentCount", "int": 0, "type": "JDBCConnectionPoolRuntime", "value": "0", "location": "myWeblogicNode1", "@timestamp": "2015-08-24T18:27:22.909Z"}
{"name": "somePool", "attribute": "ActiveConnectionsCurrentCount", "number": 0.0, "alias": "myproject.JDBCConnectionPoolRuntime.somePool.ActiveConnectionsCurrentCount", "int": 0, "type": "JDBCConnectionPoolRuntime", "value": "0", "location": "myWeblogicNode1", "@timestamp": "2015-08-24T18:27:22.923Z"}
{"name": "somePool", "attribute": "MaxCapacity", "number": 25.0, "alias": "myproject.JDBCConnectionPoolRuntime.somePool.MaxCapacity", "int": 25, "type": "JDBCConnectionPoolRuntime", "value": "25", "location": "myWeblogicNode1", "@timestamp": "2015-08-24T18:27:22.936Z"}
{"name": "somePool", "attribute": "CurrCapacity", "number": 1.0, "alias": "myproject.JDBCConnectionPoolRuntime.somePool.CurrCapacity", "int": 1, "type": "JDBCConnectionPoolRuntime", "value": "1", "location": "myWeblogicNode1", "@timestamp": "2015-08-24T18:27:22.948Z"}
{"name": "yetAnotherPool", "attribute": "ActiveConnectionsHighCount", "number": 2.0, "alias": "myproject.JDBCConnectionPoolRuntime.yetAnotherPool.ActiveConnectionsHighCount", "int": 2, "type": "JDBCConnectionPoolRuntime", "value": "2", "location": "myWeblogicNode2", "@timestamp": "2015-08-24T18:27:22.959Z"}
{"name": "yetAnotherPool", "attribute": "LeakedConnectionCount", "number": 0.0, "alias": "myproject.JDBCConnectionPoolRuntime.yetAnotherPool.LeakedConnectionCount", "int": 0, "type": "JDBCConnectionPoolRuntime", "value": "0", "location": "myWeblogicNode2", "@timestamp": "2015-08-24T18:27:22.970Z"}
{"name": "yetAnotherPool", "attribute": "PrepStmtCacheMissCount", "number": 6.0, "alias": "myproject.JDBCConnectionPoolRuntime.yetAnotherPool.PrepStmtCacheMissCount", "int": 6, "type": "JDBCConnectionPoolRuntime", "value": "6", "location": "myWeblogicNode2", "@timestamp": "2015-08-24T18:27:22.982Z"}
{"name": "yetAnotherPool", "attribute": "WaitingForConnectionHighCount", "number": 0.0, "alias": "myproject.JDBCConnectionPoolRuntime.yetAnotherPool.WaitingForConnectionHighCount", "int": 0, "type": "JDBCConnectionPoolRuntime", "value": "0", "location": "myWeblogicNode2", "@timestamp": "2015-08-24T18:27:22.993Z"}
...
```