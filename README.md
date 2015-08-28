# Credit where it's due
Please read the "Dependencies" chapter below.  
Probespawner uses a number of great software and it depends directly on a number of them. 
Links are provided for every of them.
Some packages, namely jar files, are available here for convenience but you should upgrade them should you use this project.

All the probespawner's source is public domain - [see LICENSE.md file](https://github.com/filipealmeida/probespawner/blob/master/INSTALL.windows.md)

# Installing probespawner

Below you'll find the instructions to install and use Probespawner in a *NIX environment.  
[Click here to check instruction on how to install and use in Windows] (https://github.com/filipealmeida/probespawner/blob/master/INSTALL.windows.md)  
  
1. Download `java` (1.7+) - https://java.com/en/download/
2. Install `java`
3. Download Jython - http://www.jython.org/downloads.html
4. Have `java` on your path (1.7+)
5. Install Jython: `java -jar jython-installer-2.7.0.jar -s -d targetDirectory`
6. Grab probespawner from github or download it from where's available - https://github.com/filipealmeida/probespawner/
7. Expand the tarball/zip you’ve downloaded.
8. Enter probespawner's directory
9. Have `jython` on your path
10. Run `./probespawner.sh <YOURCONFIG.json>` if in linux/mac or `probespawner.bat <YOURCONFIG.json>` if with windows

[YOURCONFIG.json example here](https://github.com/filipealmeida/probespawner/blob/master/example.json)

# What’s probespawner
Probespawner is a small jython program initially designed to repeat JDBC queries periodically and write it’s output to an Elasticsearch cluster.  
Now it's kind of a crossbreed of a logshipper with crontable.  
It can periodically perform JDBC queries, JMX queries and operations and/or command executions, outputting it's parsed data (usually as JSON) to Elasticsearch, RabbitMQ/AMQP queues, OpenTSDB, files and/or STDOUT.  
It's no substitute of a log shipper but comes in handy and packs a number of interesting examples in jython on how to achieve just that.  
Tough immature and not production ready, it's kind of easy to adapt/extend and it already has been real useful for monitoring and troubleshooting systems, databases and java applications (so far).  

# Why probespawner
The simple answer is "just because".  
Probespawner got written initally to perform some tasks that [elasticsearch-river-jdbc](https://github.com/jprante/elasticsearch-river-jdbc) feeder did not address and to come around the bugs and difficulties if setting up one such river/feeder (plus rivers are apparently now deprecated).  
Other work extended from there to help troubleshooting, monitoring and performance statistics on the OS and applications.  
See the examples folder for some practical uses.  
An effort do document some of the things done using probespawner will be made but some are:
* Collect AWR from OracleDB, DMV data from Microsoft SQL Server and performance schema data from MySQL's.  <br /> Index data on Elasticsearch. Insight through kibana.  
[SQLServer DMVs example here.](https://github.com/filipealmeida/probespawner/blob/master/docs/004.monitoring.SQLServer.DMV.with.elasticsearch.md)
* Collect netstat information periodically, send through RabbitMQ to Elasticsearch. D3JS to perform force directed graphs from the information with brush date/time interval selector. This animates the graph of the network conversations as you slide throught a time interval.  
[Example here.](https://github.com/filipealmeida/probespawner/blob/master/docs/001.netstat.to.elasticsearch.qbana.force.directed.graph.md)
* Collect top information, ship through pipeline to Elasticsearch. Kibana dashboard allows for quick browse trough the processes history, correlate with machine resources, document blocking conditions and wait events.  
[Example here.](https://github.com/filipealmeida/probespawner/blob/master/docs/002.linux.metrics.top.iostat.netstat.top.to.elasticsearch.md)
* Collect stack traces periodically from application servers while monitoring resources of a JVM using JMXProbe. Data shipped through pipeline (RabbitMQ) made available for performance engineers, application testers, master troubleshooters and developers for the many reasons you might imagine.  
[Example here.](https://github.com/filipealmeida/probespawner/blob/master/docs/003.java.jmx.to.rabbitmq.elasticsearch.md)
* Collect vmstat info, write metrics to OpenTSDB via socket

# How does probespawner work

Probespawner reads a JSON configuration file stating a list of inputs and the outputs, much like [logstash](https://www.elastic.co/products/logstash).
The inputs provided are either JMX (probing a JVM), JDBC (querying a database) or execution of programs in different platforms.  
Each is called a probe.  
The data acquired cyclically from these input sources are sent to Elasticsearch, RabbitMQ, OpenTSDB, stdout or file.
![](https://github.com/filipealmeida/probespawner/blob/master/docs/probespawner.overview.png)  

Basically, for each input you have defined, probespawner will launch a (java) thread as illustrated in the concurrency manual of jython.  
Each thread is an instance of a probe that performs:
* Periodical acquisition of records from a database, writes these to an Elasticsearch cluster (using Elasticsearch’s JAVA api).
* Periodical acquisition of JMX attributes from a JVM instance, outputs to an index of your choice on your Elasticsearch cluster and to a file on your filesystem.
* Periodical top command parse, sends data to a RabbitMQ queue
* Send metrics data from command execution to OpenTSDB
* Periodically executes any task you designed for your own probe and do whatever you want with the results, for instance, write them to STDOUT.

# Dependencies
1. Jython 2.5.3+ - http://www.jython.org/downloads.html
2. Jyson 1.0.2+ - http://opensource.xhaus.com/projects/jyson
3. JodaTime 2.7+ - https://github.com/JodaOrg/joda-time

## Optional but real useful
1. Tomcat’s 7.0.9+ (connection pool classes) - http://tomcat.apache.org/download-70.cgi
2. Elasticsearch 1.5.0+ - https://www.elastic.co/downloads
3. RabbitMQ 3.5.3+ - https://www.rabbitmq.com

## JDBC drivers you need for your queries, some common ones for your reference:
1. Mysql - http://dev.mysql.com/downloads/connector/j/
2. Oracle - http://www.oracle.com/technetwork/apps-tech/jdbc-112010-090769.html
3. MSSQL - http://www.microsoft.com/en-us/download/details.aspx?displaylang=en&id=11774, http://go.microsoft.com/fwlink/?LinkId=245496

About the use of Tomcat’s connection pool, zxJDBC could’ve been used to attain the same objective.
Since some code was around using it, so it stood.

# Probespawner package contents

The package contains the following files:

1. **dummyprobe.py** - Do not be mistaken judging by the name that this is a dummy probe. It’s been a poor choice of name but this is immature code so it’s staying like that. This is the class from which the other inherit and it’s the real skeleton for probes.
2. **cooldbprobe.py** - Same as databaseprobe.py but uses JodaTime for time parameters, timestamp is in milliseconds, datetime strings are ISO8601 format looking like “2015-11-21T15:14:15.912+05:00”.
3. **jelh.py** - Jython’s Elasticsearch Little Helper, the module responsible for the bulk requests to elasticsearch. 
4. **jmxprobe.py** - This probe executes JMX requests in a JVM and reports it’s results to the outputs configured in the JSON setup. NOTE: It discards bad objects/attributes in case of failure but keeps working if it happens. Adjust to your needs (find out the try/except in the “tick” method)
5. **probespawner.ini** - Logging configuration.
6. **probespawner.py** - It’s the croupier, it reads and delivers the configuration for the probes. Lastly, it instantiates all of them and wait’s for them to finish. It’s a simple threadpool but it would be great if it dealt with interrupts and failures from it’s workers.
7. **probespawner.sh** - Launches probespawner with it’s argument as configuration.
8. **probespawner.bat** - Launches probespawner with it’s argument as configuration in case you’re using Microsoft Windows.
9. **testprobe.py** - The real dummy probe, it merely states that is a test and sends a sample dictionary to the outputs configured.
10. **example.json** - Sample JSON configuration for a JDBC, a JMX input, any input. [Click here for contents](https://github.com/filipealmeida/probespawner/blob/master/example.json)
11. **zxdatabaseprobe.py** - Same as databaseprobe.py but dispensing the use of Tomcat’s connection pool (uses zxJDBC)
12. **databaseprobe.py** - Amazingly, this does not depend from “dummyprobe.py”, it was the initial code of a more monolitic probe that existed in the past. This probe executes any given query in a database and reports it’s results (if any) to the outputs configured in the JSON setup. It's here for legacy reasons, you should ignore this probe.
13. **execprobe.py** - Executes “command” every cycle and reports it’s output
14. **linuxtopprobe.py** - Executes top command on linux boxes every cycle, parses and reports it’s output in an elasticsearch friendly fashion
15. **netstats.py** - Executes “netstat -s” command on linux boxes every cycle, parses and reports it’s output in an elasticsearch friendly fashion.
16. **netstatntc.py** - Executes “netstat -ntce” command on linux boxes every cycle, parses and reports it’s output in an elasticsearch friendly fashion.
17. **rmqlh.py** - Jython’s RabbitMQ Little Helper, the module responsible for pushing to RabbitMQ queues. 
18. **opentsdblh.py** - Jython’s OpenTSDB (time-series database) Little Helper, the module responsible for pushing to such backend. 

# Configuring
**Instead of reading this section** you can refer to the file [example.json](https://github.com/filipealmeida/probespawner/blob/master/example.json) file in the repo/zip.
There you'll find examples of most configurations.  

Where omitted a description of a field it means it has no action.  
The list of possible fields for inputs and outputs is shown below:

## Inputs (the probes)

### Common fields for inputs
Field | Description
--- | --- 
description | Small description of your input, it'll be used to name it's JAVA thread
probemodule | Dictionary with “module” and “name” keys specifying the module and name to import as the probe for one input
module | The jython module that contains the probe, e.g.: databaseprobe
name | The name to import that will be used by probespawner to instantiate the thread, e.g.: DatabaseProbe
output | List of outputs to write the acquired data, e.g.: [“elasticsearchJMXoutput”]. See “outputs” below
interval |Interval in seconds to wait for the next iteration. The time spent in the execution of a cycle is subtracted to this value in every iteration
maxCycles | How many cycles before exiting the thread
storeCycleState | Stores parameters and information about cycles, like number of cycles, start and end times, etc. e.g.: "storeCycleState": { "enabled": true, "filename": "sincedb.json"}
transform | Transformation of message to a string e.g.: “jmx.$data.attribute $cycle.laststart $data.number host=suchhost“

### JDBC input specific parameters
There are two possible modules, “cooldbprobe”, “databaseprobe” and “zxdatabaseprobe”  
First two use Tomcat’s JDBC connection pool.

Field | Description
--- | ---
url | Connection URL, e.g.: jdbc:mysql://mysqlhost:3306/INFORMATION_SCHEMA
driverClassName | The driver classname, must be in the CLASSPATH, e.g.: com.mysql.jdbc.Driver
username | Username to connect to the database
password | Password to connect to the database
dbProperties | Property dictionary with JDBC driver specific properties. Overrides the database properties passed into the Driver.connect(String, Properties) method (see setDbProperties method from Tomcat’s connection pool)
minIdle | See Tomcat’s connection pool documentation (number of minimum idle connections)
maxIdle | See Tomcat’s connection pool documentation
maxAge | See Tomcat’s connection pool documentation
validationQuery | See Tomcat’s connection pool documentation (validation query, everytime a handle is obtained from the pool)
initSQL | See Tomcat’s connection pool documentation (initial SQL when creating a connection)
sql | List of query objects
.. statement | The statement itself
.. parameter | Parameters for the query, see “Statement parameters” table below
.. id | Id for your query, useful for debugging
.. parameter | Initial setup of the parameters, see “Statement parameters” table below

#### Statement parameters
Parameters you can use for your prepared statements (`?` in the `statement` definition, see [example.json](https://github.com/filipealmeida/probespawner/blob/master/example.json)).

Field | Description
--- | ---
start | Unix timestamp in your script environment timezone at your cycle start (see python’s time.time() function), e.g.: 1427976119.921
laststart | Unix timestamp of your previous cycle start
end | Unix timestamp of the end of last cycle
numCycles | Number of cycles started
qstart | Unix timestamp of a given query start
qlaststart | Unix timestamp of a the last time a given query started
qend | Unix timestamp of a the last time a given query ended
startdt | Same as start but a ISO8601 datetime, e.g.: “2015-04-02 12:00:00.000000”. Every parameter with suffix dt is a date in such format
laststartdt | Same as laststart in ISO8601
enddt | Same as end in ISO8601
qstartdt | Same as qstart in ISO8601
qlaststartdt | Same as qlaststart in ISO8601
qenddt | Same as qend in ISO8601

#### “cooldbprobe” input extra parameters for queries
cooldbprobe packs a few extras and has some differences from the above:

Field | Description
--- | --- 
start | Unix timestamp in milliseconds in your script environment timezone at your cycle start (see python’s time.time() function), e.g.: 1427976119921, the getTimeMillis() from JodaTime
laststart | Unix timestamp in milliseconds of your previous cycle start
end | Unix timestamp in milliseconds of the end of last cycle
numCycles | Number of cycles started
qstart | Unix timestamp in milliseconds of a given query start
qlaststart | Unix timestamp in milliseconds of a the last time a given query started
qend | Unix timestamp in milliseconds of a the last time a given query ended
startdt | Same as start but a ISO8601 datetime, e.g.: “2014-11-22T12:13:03.991+05:00”. Every parameter with suffix “dt” is a date in such format
laststartdt | Same as laststart in ISO8601, e.g.: “2014-11-22T12:13:03.991+05:00”
enddt | Same as end in ISO8601, e.g.: “2014-11-22T12:13:03.991+05:00”
qstartdt | Same as qstart in ISO8601, e.g.: “2014-11-22T12:13:03.991+05:00”
qlaststartdt | Same as qlaststart in ISO8601, e.g.: “2014-11-22T12:13:03.991+05:00”
qenddt | Same as qend in ISO8601, e.g.: “2014-11-22T12:13:03.991+05:00”
qelapsed | Elapsed time in milliseconds from start of execution until resultset traversal and insert in the outputs
*anyother* | If you specify in your input queries any other field you can get it as a parameter on your query, e.g.: { “statement“: “select ?“, “parameter“: [“$cycle.myparameter“], “myparameter“: “testparameter“ }

### JMX input specific parameters
Field | Description
--- | --- 
host | JMX host
port | JMX port
username | Username for JMX connection
password | Password for JMX connection
attributes | List of metrics to obtain from JXM, e.g.: ["java.lang:type=Memory/HeapMemoryUsage", "java.lang:type=Runtime/Uptime"]
operations | List of operations to execute via JMX, e.g: [{ "name": "java.lang:type=Threading/dumpAllThreads", "params": [ true, true ], "signatures": [ "boolean", "boolean" ] },  { "name": "java.lang:type=Threading/findDeadlockedThreads" } ]
arrayElementsToRecord | Set this to true to expand an array if such is returned to your request 
"queries" | array of queries in logstash fashion, [see logstash configuration example](https://www.elastic.co/guide/en/logstash/current/plugins-inputs-jmx.html)
"alias" | prefix for metric names
"compositeDataToManyRecords" | true or false, splits return object in many; for otsdb output preferred value is true

### ExecProbe specific
Field | Description
--- | --- 
command | Set this to the command you want to execute every cycle
regexp | Named groups regex, python style, to parse and name your fields
metrics | List of group names which are metrics. A document/JSON entry per metric will be generated. Every metric value will be converted to a float.
terms | Same as metrics but values won't be converted to floats
decimalMark | Decimal mark separator for number parsing
### Top specific
Field | Description
--- | --- 
command | Set this to change the “top -Hbi -n20 -d5 -w512” command that gets executed every cycle.

### NetstatS specific
Field | Description
--- | --- 
command | Set this to change the “netstat -s” command that gets executed every cycle.

### NetstatNTC specific
Field | Description
--- | --- 
command | Set this to change the “netstat -ntc” command that gets executed every cycle.

## Outputs
### Common fields
Field | Description
--- | --- 
class | The class of your output, one of “elasticsearch”, “rabbitmq”, “file” or “stdout”
outputmodule | Alike the input, your module and name to import e.g.: `{ "module": "jelh", "name" : "Elasticsearch" }` or `{ "module": "rmqlh", "name" : "RabbitMQ" }`
codec | Transformations to the data, e.g.: `json_lines` (see rabbitMQ example)
messageTemplate | A dictionary to append to be sent/added in the output message
### Elasticsearch (jelh.py)
Field | Description
--- | --- 
cluster | A string with the clustername, defaults to “elasticsearch”
outputmodule | `{ "module": "jelh", "name" : "Elasticsearch" }`
hosts | List of hosts:ports, e.g.: [“10.0.0.1:9300”, “10.0.0.2:9300”] If host and port are also specified, it’ll be added to this list
host | Hostname/IP of node (defaults to “localhost”)
port | Port for transport, defaults to 9300
options |Any options you want to add to the elasticsearch client configuration, e.g.: { "cluster.name": "fuckup", "client.transport.ping_timeout": "5s", "client.transport.nodes_sampler_interval": "5s", "client.transport.ignore_cluster_name": false, “client.transport.sniff": true,  } Overrides cluster name (“cluster”)
indexPrefix | Index name prefix, defaults to “sampleindex”
indexSuffix | Defaults to “-%Y.%m.%d” but can be a JDBC fieldname. If the fieldname parses as a ISO8601 date string it’ll use it’s info and suffix with “%Y.%m.%d”
type | Document type, e.g.: “jdbc”
indexSettings | Elasticsearch JSON for index settings
typeMapping | Elasticsearch type mapping, e.g.: "jdbc": { "properties" : { "@timestamp" : { "type" : "date" } } }
index_settings | Overrides indexSettings
time_mapping | Overrides typeMapping
bulkActions | Number of documents to keep before flushing data
bulkSize | *ignored for the time being*
flushInterval | *ignored for the time being*
concurrentRequests | *ignored for the time being*
actionRetryTimeout | Number of seconds to sleep before re-executing the elasticsearch action in progress
concurrentRequests | *ignored for the time being*

### RabbitMQ (rmqlh.py)
Field | Description
--- | --- 
outputmodule | `{ "module": "rmqlh", "name" : "RabbitMQ" }`
queue_name | queue to write to
addresses | list of addresses (for failover) e.g.: `["suchhost:5672", "suchhost:5672"]`
host | your RabbitMQ host
port | your AMQP port
virtualhost | your known virtualhost
username | your username
password | your password
uri | all of the above, overrides all, e.g.: `amqp://myuser:mypassword@suchhost:5672/vhost`
networkRecoveryInterval | Sets connection recovery interval. Default is 5000.
automaticRecoveryEnabled | if true, enables connection recovery
topologyRecoveryEnabled | Enables or disables topology recovery
routingKey | routing key for your data
exchange | an exchange name if any

### OpenTSDB (opentsdblh.py)
Field | Description
--- | --- 
outputmodule | `{ "module": "opentsdblh", "name" : "OpenTSDB" }`
queue_name | queue to write to
addresses | list of addresses (for failover) e.g.: `["suchhost:5672", "suchhost:5672"]`
host | your OpenTSDB host
port | your OpenTSDB port
metricPrefix | prefix to add to your OTSDB metrics, defaults to "probespawner"
metric_field | field with your metric name
value_field | field with the value for your metric
metrics | list of fields that are metrics to be stored
blacklist | list of blacklisted tags (keys to remove from metric push)
tags | array of extra tags for metrics e.g.: [ "sometag=somevalue", "othertag=othervalue" ]

### STDOUT
Field | Description
--- | --- 
codec | “json_lines”, no other available.

### File
Field | Description
--- | --- 
codec | “json_lines”, no other available.
filename | The filename to write the information to in the format established by the codec.

# Putting it all together
Now you need to assemble a JSON file indicating which inputs are to be spawned, what probes are to be launched.
Hence the “input” field.  
This field indicates probespawner which inputs are to be processed by the probe threads.  

Field | Description
--- | --- 
input | List of inputs to be launched by probespawner, e.g.: [“JMXInput”, “JDBCInput”]

Refer to the file [example.json](https://github.com/filipealmeida/probespawner/blob/master/example.json).  
There you will find an example with many combinations of the above options.  
That should suffice for most everything you have in mind for recipes with probespawner.

# Running probespawner

## Export the classpath:
`export CLASSPATH=/home/suchuser/opt/apache-tomcat-7.0.59/lib/tomcat-jdbc.jar:/home/suchuser/opt/apache-tomcat-7.0.59/bin/tomcat-juli.jar:/home/suchuser/var/lib/java/jyson-1.0.2/lib/jyson-1.0.2.jar:/home/suchuser/opt/elasticsearch-1.5.0/lib/lucene-core-4.10.4.jar:/home/suchuser/opt/elasticsearch-1.5.0/lib/elasticsearch-1.5.0.jar:/home/suchuser/var/lib/java/mysql-connector-java-5.1.20-bin.jar:/home/suchuser/var/lib/java/sqljdbc_4.0/enu/sqljdbc4.jar:/home/suchuser/var/lib/java/sqljdbc_4.0/enu/sqljdbc.jar:/home/suchuser/opt/rabbitmq-java-client-bin-3.5.3/rabbitmq-client.jar`

## Run the jython code:
`jython probespawner.py --configuration=example.json`

## Shell script launcher
This one calls “find” in the CWD and adds all *jar files to the classpath before calling jython.  
`probespawner.sh example.json`

## Batch file launcher
The batch file lists all jars in the “jars” directory and adds them to the classpath before calling jython.  
`probespawner.bat example.json`

# Developing other probes
Just in case you want to develop a probe for your convenience, be warned: this is immature code with no support.
Having said that, take a look at the “testprobe.py” file.

## Produce your data: override the “tick” method
This is the minimum probe, the only thing it does is writing the `{ ‘test’: ‘yes’ }` dictionary to the configured outputs in your JSON file.
For that to be accomplished, your class must override the “tick” method which is called at every cycle, meaning every “interval” seconds you defined in your input.

## Get your configuration and initialize your probe: override the “initialize” method
The method “initialize” is another popular overridden one, called before the probe starts cycling. 
It’s usually in this method you get the configuration keys from the JSON file, set up and initialize your probe.

## Getting a property:
`username = self.getInputProperty("username")`  
This grabs the “username” content of your defined input in the JSON file and returns it’s value (or None).


