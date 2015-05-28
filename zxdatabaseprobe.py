#          _    __ ___ 
#__      _| |_ / _|__ \
#\ \ /\ / / __| |_  / /
# \ V  V /| |_|  _||_| 
#  \_/\_/  \__|_|  (_) 
#
#TODO: does not implement dummyprobe's "interface" as supposed to, redo in cooldbprobe fashion

from __future__ import with_statement
import os.path
import threading
import sys
import logging
from logging.config import fileConfig
import time
import datetime

from java.util.concurrent import Callable
from com.ziclix.python.sql import PyConnection
from com.ziclix.python.sql import zxJDBC

import com.xhaus.jyson.JysonCodec as json
import org.apache.tomcat.jdbc.pool as dbpool
import org.elasticsearch.common.transport.InetSocketTransportAddress as InetSocketTransportAddress
import org.elasticsearch.client.transport.TransportClient as TransportClient
import org.elasticsearch.common.settings.ImmutableSettings as ImmutableSettings
import org.elasticsearch.client.transport.NoNodeAvailableException as NoNodeAvailableException
import traceback
from jelh import Elasticsearch

logger = logging.getLogger(__name__)

class DatabaseProbe(Callable):
    def __init__(self, input, output):
        self.input = input
        self.output = output
        self.openfiles = {}
        self.elasticsearch = {}
        p = {}
        p["params"] = {}
        p["driverClassName"] = input["driverClassName"]
        p["params"]["url"] = input["url"]
        p["params"]["username"] = input["username"]
        p["params"]["password"] = input["password"]
        #TODO: check encoding and charset select * from nls_database_parameters where parameter='NLS_NCHAR_CHARACTERSET' - {"PARAMETER":"NLS_NCHAR_CHARACTERSET","VALUE":"AL16UTF16"}
        self.pool = p

        try:
            self.interval = int(input["interval"])
        except:
            self.interval = 60

        try:
            #open file if exists
            if isinstance(input["sql"], basestring) and os.path.isfile(input["sql"]):
                with open(input["sql"], "r") as ins:
                    self.sql = []
                    for line in ins:
                       self.sql.append({ "statement": line.rstrip() })
            else:
                self.sql = input["sql"]
        except:
            self.sql = []
        idx = 0
        for phrase in self.sql:
            if "id" not in phrase:
                phrase["id"] = "q" + str(idx)
            idx += 1

        logger.debug("Queries setup: %s", self.sql)
        logger.debug("Connection pool setup: %s", p)
        #p.setJdbcInterceptors('org.apache.tomcat.jdbc.pool.interceptor.ConnectionState;' + 'org.apache.tomcat.jdbc.pool.interceptor.StatementFinalizer')
        self.started = None
        self.completed = None
        self.result = None
        self.thread_used = None
        self.exception = None
        self.datasource = None
        self.running    = False
        #self.datasource = dbpool.DataSource()
        #self.datasource.setPoolProperties(self.jdbcPoolProperties)
        #TODO: optimize these structures, unecessary memory footprint (qstart,qend,....)
        self.cycle = { 
            "start": time.time(),
            "laststart": time.time(),
            "laststartdt": datetime.datetime.fromtimestamp(time.time()).isoformat(' '),
            "end": time.time(), 
            "qstart": {},#last time a given query started
            "qstartdt": {},#last iso8601 formated time a given query started
            "qlaststart": {},#last time a given query started
            "qlaststartdt": {},#last iso8601 formated time a given query started
            "qend": {},#last time a given query ended
            "qenddt": {},#last time a given query ended
            "elapsed": 0,
            "startdt": datetime.datetime.fromtimestamp(time.time()).isoformat(' '),
            "enddt": datetime.datetime.fromtimestamp(time.time()).isoformat(' '), 
            "numCycles": 0,
            "badCycles": 0,
            "goodCycles": 0,
        }

    def __str__(self):
        if self.exception:
             return "[%s] %s dbprobe error %s in %.2fs" % \
                (self.thread_used, self.input, self.exception,
                 self.completed - self.started, ) #, self.result)
        elif self.completed:
            return "[%s] executed" % \
                (self.thread_used) #, self.result)
        elif self.started:
            return "[%s] %s started at %s" % \
                (self.thread_used, self.input, self.started)
        else:
            return "[%s] %s not yet scheduled" % \
                (self.thread_used, self.input)

    def elasticsearchInitialize(self, output):
        if output not in self.elasticsearch: #It's been initialized
            configuration = self.output[output].copy()
            try:
                configuration["indexPrefix"] = self.input["index"]
            except:
                logger.debug("No index prefix in input (backward compatibility)")
            try:
                configuration["indexPrefix"] = self.output["indexPrefix"]
            except:
                logger.debug("No prefix on output definition, going with input")
            try:
                configuration["type"] = self.input["type"]
            except:
                logger.debug("No type")
            try:
                configuration["indexSuffix"] = self.input["indexSuffix"]
            except:
                logger.debug("No indexSuffix")
            try:
                configuration["indexSettings"] = self.input["index_settings"]
            except:
                logger.debug("No index_settings")
            try:
                configuration["typeMapping"] = self.input["type_mapping"]
            except:
                logger.debug("No type mapping")
            
            elasticsearch = Elasticsearch(configuration)
            self.elasticsearch[output] = elasticsearch
        else:
            logger.info("Already initialized output %s", output)
        return True

    def elasticsearchWriteDocument(self, output, data, force):
        es = self.elasticsearch[output]
        es.writeDocument(data, force)
        return True

    # needed to implement the Callable interface;
    # any exceptions will be wrapped as either ExecutionException
    # or InterruptedException
    def call(self):
        self.thread_used = threading.currentThread().getName()
        self.started     = time.time()
        if len(self.sql) <= 0:
            self.completed = time.time()
            return self
        self.running     = True

        for phrase in self.sql:
            self.cycle["qend"][phrase["id"]] = time.time()
            self.cycle["qstart"][phrase["id"]] = time.time()
            self.cycle["qlaststart"][phrase["id"]] = time.time()
            self.cycle["qenddt"][phrase["id"]] = datetime.datetime.fromtimestamp(self.cycle["qend"][phrase["id"]]).isoformat(' ')
            self.cycle["qstartdt"][phrase["id"]] = datetime.datetime.fromtimestamp(self.cycle["qstart"][phrase["id"]]).isoformat(' ')
            self.cycle["qlaststartdt"][phrase["id"]] = datetime.datetime.fromtimestamp(self.cycle["qstart"][phrase["id"]]).isoformat(' ')
            for key in ["qend", "qstart","qlaststart","qenddt","qstartdt","qlaststartdt"]:
                if key in phrase:
                    self.cycle[key][phrase["id"]] = phrase[key]
                    logger.debug("Parameter for query %s initialized from configuration with value %s", phrase["id"], str(phrase[key]))

        while self.running:
            self.cycle["numCycles"] += 1
            self.cycle["start"] = time.time()
            self.cycle["startdt"] = datetime.datetime.fromtimestamp(self.cycle["start"]).isoformat(' ')
            logger.info(datetime.datetime.fromtimestamp(self.cycle["start"]).isoformat(' '))
            try:
                for phrase in self.sql:
                    preparedStatementParams = []
                    logger.info(phrase["statement"])
                    numrows = 0
                    try:
                        #conn = apply(zxJDBC.connectx, (self.pool["driverClassName"],), self.pool["params"])
                        conn = zxJDBC.connect(self.pool["params"]["url"], self.pool["params"]["username"], self.pool["params"]["password"], self.pool["driverClassName"])
                        with conn.cursor(1) as cursor:
                            #initialize outputs
                            for output in self.output:
                                outputType = self.output[output]["class"]
                                if outputType == "file":
                                    filename = self.output[output]["filename"]
                                    self.openfiles[filename] = open(filename, 'ab')
                                if outputType == "elasticsearch":
                                    self.elasticsearchInitialize(output)
                            #prepare dictionary for prepared statement values
                            self.cycle["qstart"][phrase["id"]] = time.time()
                            self.cycle["qstartdt"][phrase["id"]] = datetime.datetime.fromtimestamp(self.cycle["qstart"][phrase["id"]]).isoformat(' ')
                            if "parameter" in phrase:
                                logger.debug("Got parameters!!")
                                for parameter in phrase["parameter"]:
                                    strlist = parameter.split("$cycle.")
                                    if len(strlist) > 0:
                                        if strlist[1].startswith('q'):
                                            preparedStatementParams.append(self.cycle[strlist[1]][phrase["id"]])
                                            logger.debug("Got parameter %s = %s", parameter, self.cycle[strlist[1]][phrase["id"]])
                                        else:
                                            preparedStatementParams.append(self.cycle[strlist[1]])
                                            logger.debug("Got parameter %s = %s", parameter, self.cycle[strlist[1]])
                                        logger.debug(strlist[1])
                            #go for queries
                            logger.debug("Preparing statement: %s", phrase["id"])
                            query = cursor.prepare(phrase["statement"])
                            logger.debug("Executing statement: %s", phrase["id"])
                            cursor.execute(query, preparedStatementParams)
                            row = None
                            logger.debug("Starting fetch for statement: %s", phrase["id"])
                            if cursor.description != None:
                                fields = [i[0] for i in cursor.description]
                                row = cursor.fetchone()
                                #logger.info("Rows to fetch: %d", cursor.rowcount)
                            else:
                                fields = []
                                conn.commit()
                            while row is not None:
                                idx = 0
                                rowDict = {}
                                for field in fields:
                                    if isinstance(row[idx], str):
                                        rowDict[field] = row[idx]
                                    elif isinstance(row[idx], unicode):
                                        rowDict[field] = row[idx]
                                    else:
                                        rowDict[field] = row[idx]
                                    idx = idx + 1
                                for output in self.output:
                                    outputType = self.output[output]["class"]
                                    #TODO: deal with ommited fields
                                    if outputType == "elasticsearch":
                                        self.elasticsearchWriteDocument(output, rowDict, False)
                                    if outputType == "stdout":
                                        codec = self.output[output]["codec"]
                                        if codec == "json_lines":
                                            print(json.dumps(rowDict))
                                    if outputType == "file":
                                        codec = self.output[output]["codec"]
                                        if codec == "json_lines":
                                            self.openfiles[filename].write(json.dumps(rowDict).encode('UTF-8'))
                                            self.openfiles[filename].write("\n")
                                numrows = numrows + 1
                                row = cursor.fetchone()
                            self.cycle["qend"][phrase["id"]] = time.time()
                            self.cycle["qenddt"][phrase["id"]] = datetime.datetime.fromtimestamp(self.cycle["qend"][phrase["id"]]).isoformat(' ')
                            self.cycle["qlaststart"][phrase["id"]] = self.cycle["qstart"][phrase["id"]]
                            self.cycle["qlaststartdt"][phrase["id"]] = self.cycle["qstartdt"][phrase["id"]]
                            logger.debug(self.cycle)
                            #post iteration, flush data, close files
                            if numrows > 0:
                                for output in self.output:
                                    outputType = self.output[output]["class"]
                                    if outputType == "elasticsearch":
                                        self.elasticsearchWriteDocument(output, None, True)
                                    if outputType == "file":
                                        filename = self.output[output]["filename"]
                                        self.openfiles[filename].close()
                            query.close()
                            assert query.closed
                    # statement catcher
                    except Exception, ex:
                        traceback.print_exc()
                        self.exception = ex
                        logger.error(ex)
                        self.running = False
                        self.completed = time.time()
                        #raise
                    finally:
                        conn.close()
            # cycle catcher
            except Exception, ex:
                traceback.print_exc()
                self.exception = ex
                logger.error(ex)
                self.running = False
                self.completed = time.time()
                #raise
            self.cycle["end"] = time.time()
            self.cycle["enddt"] = datetime.datetime.fromtimestamp(self.cycle["end"]).isoformat(' ')
            self.cycle["laststart"] = self.cycle["start"]
            self.cycle["laststartdt"] = self.cycle["startdt"]
            self.cycle["elapsed"] = time.time() - self.cycle["start"]
            sleepTime = self.interval - self.cycle["elapsed"]
            if "maxCycles" in self.input and self.cycle["numCycles"] >= self.input["maxCycles"]:
                logger.info("Max cycles reached %d", self.cycle["numCycles"])
                sleepTime = 0
                self.running = False
            if (sleepTime < 0):
                sleepTime = 0
            logger.info("End of cycle: sleeping for %d seconds", sleepTime)
            time.sleep(sleepTime);
        #TODO: cleanup, make sure outputs have closed and whatnot
        self.completed = time.time()
        return self