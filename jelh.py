# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

#Jython Elasticsearch Little Helper
#import org.apache.tomcat.jdbc.pool as dbpool
import org.elasticsearch.common.transport.InetSocketTransportAddress as InetSocketTransportAddress
import org.elasticsearch.client.transport.TransportClient as TransportClient
import org.elasticsearch.common.settings.ImmutableSettings as ImmutableSettings
import org.elasticsearch.client.transport.NoNodeAvailableException as NoNodeAvailableException
import org.elasticsearch.indices.IndexAlreadyExistsException as IndexAlreadyExistsException
import traceback
import time
import datetime
import com.xhaus.jyson.JysonCodec as json
import threading

import sys
import logging
logger = logging.getLogger(__name__)

class Elasticsearch():
    def __init__(self, config):
    	if isinstance(config, basestring):
            self.config = json.loads(config.decode('utf-8'))
    	else:
            self.config = config
        self.runtime = {}
        #TODO: ugly ugly initialization all around, review, make it sane
        clusterName = "elasticsearch"
        host = "localhost"
        port = 9300

        if "host" in self.config:
            host = self.config["host"]
        else:
            host = "localhost"
        if "port" in self.config:
            port = self.config["port"]
        else:
            port = "9300"
        if "bulkActions" not in self.config:
            self.config["bulkActions"] = 1000 
        if "bulkSize" not in self.config:
            self.config["bulkSize"] = 107374182400
        if "flushInterval" not in self.config:
            self.config["flushInterval"] = 60000
        if "concurrentRequests" not in self.config:
            self.config["concurrentRequests"] = 1
        if "actionRetryTimeout" not in self.config:
            self.config["actionRetryTimeout"] = 5
        if "type" not in self.config:
            self.config["type"] = "logs"
        if "indexPrefix" not in self.config:
            self.config["indexPrefix"] = "sampleindex"
        if "indexSuffix" not in self.config:
            self.config["indexSuffix"] = "-%Y.%m.%d"
        logger.debug("Initializing elasticsearch output %s: %s", self.config["indexPrefix"], json.dumps("self.config"))
        self.config["settings"] = ImmutableSettings.settingsBuilder();
        if "options" not in self.config:
            self.config["options"] = {}
            if "cluster" in self.config:
                self.config["options"]["cluster.name"] = self.config["cluster"]
            else:
                self.config["options"]["cluster.name"] = "elasticsearch"
        else:
            if "cluster.name" not in self.config["options"]:
                if "cluster" in self.config:
                    self.config["options"]["cluster.name"] = self.config["cluster"]
                else:
                    self.config["options"]["cluster.name"] = "elasticsearch"

        for setting in self.config["options"]:
            value = self.config["options"][setting]
            logger.info("Setting Elasticsearch options: %s = %s", setting, value)
            self.config["settings"].put(setting, value)

        self.config["settings"].build()
        self.runtime["client"] = TransportClient(self.config["settings"])
        if "host" in self.config:
            self.runtime["client"].addTransportAddress(InetSocketTransportAddress(host, port))
        if "hosts" in self.config:
            for hostport in self.config["hosts"]:
                host, port = hostport.split(":")
                logger.info("Setting Elasticsearch host: %s = %s", host, port)
                self.runtime["client"].addTransportAddress(InetSocketTransportAddress(str(host), int(port)))
        
        self.readyBulk()
        self.runtime["indices"] = {}

    def createIndex(self, indexName):
        if indexName not in self.runtime["indices"]:
            if self.runtime["client"].admin().indices().prepareExists(indexName).execute().actionGet().exists:
                logger.debug("Index \"%s\" already exists", indexName)
                self.runtime["indices"][indexName] = time.time()
                return False
            else:                
                logger.info("Creating index %s", indexName)
                if "index_settings" in self.config:
                    self.config["indexSettings"] = self.config["index_settings"]
                if "type_mapping" in self.config:
                    self.config["typeMapping"] = self.config["type_mapping"]
                try:
                    if "indexSettings" in self.config:
                        settingsJsonStr = json.dumps(self.config["indexSettings"])
                        logger.info("Index settings: %s", settingsJsonStr)
                        self.runtime["client"].admin().indices().prepareCreate(indexName).setSettings(settingsJsonStr).execute().actionGet()
                    else:
                        self.runtime["client"].admin().indices().prepareCreate(indexName).execute().actionGet()
                except IndexAlreadyExistsException, ex:
                    logger.warning(ex)
                    logger.warning("Index %s already exists, this should be harmless", indexName)
                if "typeMapping" in self.config:
                    mappingJsonStr = json.dumps(self.config["typeMapping"])
                    logger.info("Setting mapping for %s/%s - %s", indexName, self.config["type"], mappingJsonStr)
                    self.runtime["client"].admin().indices().preparePutMapping().setIndices(indexName).setType(self.config["type"]).setSource(mappingJsonStr).execute().actionGet()

            self.runtime["indices"][indexName] = time.time()
            logger.debug("Created index: \"%s\"", indexName)
            return True
        logger.debug("Index already initialized: \"%s\"", indexName)
        return False

    def writeDocument(self, data, force):
        bulkRequest = self.runtime["bulkRequest"]
        client = self.runtime["client"]
        if data != None:
            indexName = self.getIndexName(data)
            bulkRequest.add(client.prepareIndex(indexName, self.config["type"]).setSource(json.dumps(data)))
            self.runtime["requestsPending"] = self.runtime["requestsPending"] + 1
        #TIME TO FLUSH
        if (self.runtime["requestsPending"] > 0) and ((self.runtime["requestsPending"] >= self.config["bulkActions"]) or (force == True)):
            logger.info("Flushing %d records", self.runtime["requestsPending"])
            #TODO: handle failure: org.elasticsearch.client.transport.NoNodeAvailableException
            #TODO: use JodaTime instead of jython's datetime/time
            bulkReady = False
            while not bulkReady:
                try:
                    bulkResponse = bulkRequest.execute().actionGet();
                    bulkReady = True
                except NoNodeAvailableException, ex:
                    logger.error(ex)
                    logger.warning("Bad bulk response, sleeping %d seconds before retrying, execution paused", self.config["actionRetryTimeout"])
                    time.sleep(self.config["actionRetryTimeout"]);
                    raise
            if bulkResponse.hasFailures():
                logger.warning("Failures indexing!")
                logger.warning(bulkResponse.buildFailureMessage())
            self.readyBulk()
        return True

    def readyBulk(self):
        self.runtime["bulkRequest"] = self.runtime["client"].prepareBulk()
        self.runtime["requestsPending"] = 0

    def getIndexName(self):
        return self.config["indexPrefix"]

    def getIndexName(self, data):
        indexName = self.config["indexPrefix"]
        if "indexSuffix" in self.config:
            indexSuffix = self.config["indexSuffix"]
            if indexSuffix in data:
                indexSuffixStr = ""
                logger.debug("Index suffix is a fieldname: %s, %s", indexSuffix, data[indexSuffix])
                #TODO: deal with the timezone
                try:
                    dateobj = datetime.datetime.strptime(data[indexSuffix], "%Y-%m-%d")
                    indexSuffixStr = dateobj.strftime("%Y.%m.%d")
                except Exception, e:
                    indexSuffixStr = data[indexSuffix].lower()
                indexName = indexName + "-" + indexSuffixStr
            else:
                logger.debug("Index suffix is will be treated as datetime format: %s", indexSuffix)
                indexName = indexName + datetime.datetime.utcnow().strftime(indexSuffix)
        logger.debug("Going for index creation: %s", indexName)
        #TODO: handle other failures
        indexReady = False
        while not indexReady:
            try:
                self.createIndex(indexName)
                indexReady = True
            except NoNodeAvailableException, ex:
                logger.error(ex)
                logger.warning("Failed to initialize index, sleeping a %d seconds before retrying, execution paused", self.config["actionRetryTimeout"])
                time.sleep(self.config["actionRetryTimeout"])
        return indexName
