# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

from __future__ import with_statement
import os.path
import threading
import sys
import logging
from logging.config import fileConfig

from java.util.concurrent import Callable
from com.ziclix.python.sql import PyConnection
from com.ziclix.python.sql import zxJDBC

import com.xhaus.jyson.JysonCodec as json
import org.apache.tomcat.jdbc.pool as dbpool
import java.util.Properties as Properties
import org.elasticsearch.common.transport.InetSocketTransportAddress as InetSocketTransportAddress
import org.elasticsearch.client.transport.TransportClient as TransportClient
import org.elasticsearch.common.settings.ImmutableSettings as ImmutableSettings
import org.elasticsearch.client.transport.NoNodeAvailableException as NoNodeAvailableException
import traceback
from jelh import Elasticsearch
from dummyprobe import DummyProbe
import org.joda.time.DateTime as DateTime

logger = logging.getLogger(__name__)

class DatabaseProbe(DummyProbe):
    def initialize(self):
        #Instanciate tomcat's connection pool
        p = dbpool.PoolProperties()
        p.setUrl(self.getInputProperty("url"))
        p.setDriverClassName(self.getInputProperty("driverClassName"))
        p.setUsername(self.getInputProperty("username"))
        p.setPassword(self.getInputProperty("password"))
        #TODO: check encoding and charset select * from nls_database_parameters where parameter='NLS_NCHAR_CHARACTERSET' - {"PARAMETER":"NLS_NCHAR_CHARACTERSET","VALUE":"AL16UTF16"}
        try:
            p.setMinIdle(int(self.getInputProperty("minIdle")))
        except:
            p.setMinIdle(2)
        try:
            p.setMaxIdle(int(self.getInputProperty("maxIdle")))
        except:
            p.setMaxIdle(2)
        try:
            p.setMaxAge(int(self.getInputProperty("maxAge")))
        except:
            p.setMaxAge(86400)
        try:
            p.setValidationQuery(self.getInputProperty("validationQuery"))
        except:
            logger.debug("Dude, no validation query for connection pool")
        try:
            p.setInitSQL(self.getInputProperty("initSQL"))
        except:
            logger.debug("Dude, no initial query for connection pool")

        if self.getInputProperty("dbProperties") != None:
            dbProperties = Properties()
            for prop in self.getInputProperty("dbProperties"):
                value = str(self.getInputProperty("dbProperties")[prop])
                dbProperties.setProperty(prop, value)
                logger.debug("Dude, database property found: %s = %s", prop, value)
            p.setDbProperties(dbProperties)

        self.jdbcPoolProperties = p

        try:
            self.interval = int(self.getInputProperty("interval"))
        except:
            self.interval = 60

        try:
            #open file if exists
            if isinstance(self.getInputProperty("sql"), basestring) and os.path.isfile(self.getInputProperty("sql")):
                with open(self.getInputProperty("sql"), "r") as ins:
                    self.sql = []
                    for line in ins:
                       self.sql.append({ "statement": line.rstrip() })
            else:
                self.sql = self.getInputProperty("sql")
        except:
            self.sql = []
        idx = 0
        for phrase in self.sql:
            if "id" not in phrase:
                phrase["id"] = "q" + str(idx)
            idx += 1

        logger.debug("Dude, queries setup: %s", self.sql)
        logger.debug("Dude, connection pool setup: %s", p)
        logger.debug("Dude, connection pool dbProperties: %s", p.getDbProperties())
        p.setJdbcInterceptors('org.apache.tomcat.jdbc.pool.interceptor.ConnectionState;' + 'org.apache.tomcat.jdbc.pool.interceptor.StatementFinalizer')
        self.datasource = dbpool.DataSource()
        self.datasource.setPoolProperties(self.jdbcPoolProperties)
        self.cycle["queryParameters"] = {}

    def startQueryCycle(self, queryId):
        self.runtime[queryId + "jodaStart"] = DateTime()
        self.cycle["queryParameters"][queryId + "qstart"] = self.runtime[queryId + "jodaStart"].getMillis()
        self.cycle["queryParameters"][queryId + "qstartdt"] = str(self.runtime[queryId + "jodaStart"])

    def finishQueryCycle(self, queryId):
        self.runtime[queryId + "jodaEnd"] = DateTime()
        self.cycle["queryParameters"][queryId + "qend"] = self.runtime[queryId + "jodaEnd"].getMillis()
        self.cycle["queryParameters"][queryId + "qenddt"] = str(self.runtime[queryId + "jodaEnd"])
        self.cycle["queryParameters"][queryId + "qlaststart"] = self.cycle["queryParameters"][queryId + "qstart"]
        self.cycle["queryParameters"][queryId + "qlaststartdt"] = self.cycle["queryParameters"][queryId + "qstartdt"]
        self.cycle["queryParameters"][queryId + "qelapsed"] = self.runtime[queryId + "jodaEnd"].getMillis() - self.runtime[queryId + "jodaStart"].getMillis()
        logger.info("Finished query %s cycle in %d", queryId, self.cycle["queryParameters"][queryId + "qelapsed"])
    
    def getQueryParameter(self, queryId, paramName):
        if queryId + paramName in self.cycle["queryParameters"]:
            return self.cycle["queryParameters"][queryId + paramName]
        else:
            return None

    def tick(self):
        for phrase in self.sql:
            self.startQueryCycle(phrase["id"])
            preparedStatementParams = []
            preparedStatementParamsDict = {}
            logger.info(phrase["statement"])
            numrows = 0
            conn = PyConnection(self.datasource.getConnection())
            try:
                with conn.cursor(1) as cursor:
                    #TODO: review, index out of range very possible
                    if "parameter" in phrase:
                        logger.debug("Dude, got parameters!!")
                        for parameter in phrase["parameter"]:
                            strlist = parameter.split("$cycle.")
                            if len(strlist) > 0:
                                if strlist[1] in ["qend","qstart","qlaststart","qenddt","qstartdt","qlaststartdt","qelapsed"]:
                                    value = self.getQueryParameter(phrase["id"], strlist[1])
                                    preparedStatementParams.append(value)
                                    preparedStatementParamsDict[parameter] = value
                                    logger.debug("Dude, got parameter %s = %s", parameter, value)
                                else:
                                    value = self.getCycleProperty(strlist[1])
                                    if value == None:
                                        value = phrase[strlist[1]]
                                    preparedStatementParams.append(value)
                                    preparedStatementParamsDict[parameter] = value
                                    logger.debug("Dude, got parameter %s = %s", parameter, value)
                                logger.debug(strlist[1])
                    logger.debug("Dude, preparing statement: %s", phrase["id"])
                    query = cursor.prepare(phrase["statement"])
                    logger.debug("Dude, executing statement: %s", phrase["id"])
                    cursor.execute(query, preparedStatementParams)
                    row = None
                    logger.debug("Dude, starting fetch for statement: %s", phrase["id"])
                    if cursor.description != None:
                        fields = [i[0] for i in cursor.description]
                        row = cursor.fetchone()
                    else:
                        fields = []
                        conn.commit()
                        self.processData({ '@timestamp':self.getQueryParameter(phrase["id"], "qstart"), "statement": phrase["statement"], "parameters": preparedStatementParamsDict } )
                        #TODO: process data with commit timestamp and whatnot
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
                        self.processData(rowDict)
                        row = cursor.fetchone()
                    query.close()
                    assert query.closed
            except Exception, ex:
                logger.debug("\n     _           _      _ \n  __| |_   _  __| | ___| |\n / _` | | | |/ _` |/ _ \ |\n| (_| | |_| | (_| |  __/_|\n \__,_|\__,_|\__,_|\___(_)\n")
                logger.debug(ex)
                raise
            finally:
                conn.close()
            self.finishQueryCycle(phrase["id"])
