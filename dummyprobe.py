# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

from __future__ import with_statement
import os.path
import threading
import sys
import logging
from logging.config import fileConfig
import time
import datetime

from java.util.concurrent import Callable

import org.joda.time.DateTime as DateTime
import com.xhaus.jyson.JysonCodec as json
import traceback

logger = logging.getLogger(__name__)

class DummyProbe(Callable):
    def __init__(self, input, output):
        self.input = input
        self.output = output
        self.openfiles = {}
        self.outplugin = {}
        self.runtime = {}
        self.started = None
        self.completed = None
        self.result = None
        self.thread_used = None
        self.exception = None
        self.datasource = None
        self.running    = False
        try:
            self.interval = int(input["interval"])
        except:
            self.interval = 60
        self.runtime["jodaStart"] = DateTime()
        self.runtime["jodaEnd"] = DateTime()
        self.cycle = { 
            "start": self.runtime["jodaStart"].getMillis(),
            "laststart": self.runtime["jodaStart"].getMillis(),
            "laststartdt": str(self.runtime["jodaEnd"]),
            "end": self.runtime["jodaStart"].getMillis(), 
            "elapsed": 0,
            "startdt": str(self.runtime["jodaEnd"]),
            "enddt": str(self.runtime["jodaEnd"]), 
            "numCycles": 0,
            "badCycles": 0,
            "goodCycles": 0,
        }

    def __str__(self):
        if self.exception:
             return "[%s] %s DummyProbe error %s in %.2fs" % \
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

    def getClassByName(self, module, className):
        if not module:
            if className.startswith("services."):
                className = className.split("services.")[1]
            l = className.split(".")
            m = __services__[l[0]]
            return getClassByName(m, ".".join(l[1:]))
        elif "." in className:
            l = className.split(".")
            m = getattr(module, l[0])
            return getClassByName(m, ".".join(l[1:]))
        else:
            return getattr(module, className)

    def outputInitialize(self, output):
        if output not in self.outplugin: #It's been initialized
            configuration = self.output[output].copy()
            self.outplugin[output] = {}
            self.outplugin[output]["config"] = configuration
            module = configuration['outputmodule']['module']
            name = configuration['outputmodule']['name']
            outputmodule = __import__(module, globals(), locals(), [''], -1)
            outputclass = self.getClassByName(outputmodule, name)
            self.outplugin[output]["object"] = outputclass
            outputInstance = self.outplugin[output]["object"](configuration)
            self.outplugin[output]["instance"] = outputInstance
            if "codec" not in configuration:
                self.outplugin[output]["codec"] = "plain"
        else:
            logger.debug("Already initialized output %s", output)

        return True

    def outputWriteDocument(self, output, data, force):
        if "codec" in self.outplugin[output]["config"]:
            codec = self.outplugin[output]["config"]["codec"]
            if codec == "json_lines":
                data = json.dumps(data).encode('UTF-8')
        return self.outplugin[output]["instance"].writeDocument(data, force)

    def outputFlush(self, output):
        return self.outplugin[output]["instance"].flush()

    def outputCleanup(self, output):
        self.outplugin[output]["instance"].cleanup()
        self.outplugin[output] = {}
        return True

    def startOutput(self):
        for output in self.output:
            if "outputmodule" in self.output[output]:
                outputType = "plugin"
            else:
                outputType = self.output[output]["class"]
            if outputType == "plugin":
                return self.outputInitialize(output)
            if outputType == "file":
                filename = self.output[output]["filename"]
                self.openfiles[filename] = open(filename, 'ab')

    def stopOutput(self):
        for output in self.output:
            if "outputmodule" in self.output[output]:
                outputType = "plugin"
            else:
                outputType = self.output[output]["class"]
            #TODO: review this, decoupling messed this class somewhat
            if outputType == "plugin":
                self.outputFlush(output)
            if outputType == "file":
                filename = self.output[output]["filename"]
                self.openfiles[filename].close()

    def processData(self, data):
        logger.debug(data)
        for output in self.output:
            if "outputmodule" in self.output[output]:
                outputType = "plugin"
            else:
                outputType = self.output[output]["class"]
            #TODO: deal with ommited fields
            if outputType == "plugin":
                self.outputWriteDocument(output, data, False)
            if outputType == "stdout":
                codec = self.output[output]["codec"]
                if codec == "json_lines":
                    print(json.dumps(data))
            if outputType == "file":
                codec = self.output[output]["codec"]
                if codec == "json_lines":
                    filename = self.output[output]["filename"]
                    self.openfiles[filename].write(json.dumps(data).encode('UTF-8'))
                    self.openfiles[filename].write("\n")

    def startCycle(self):
        self.cycle["numCycles"] += 1
        self.runtime["jodaStart"] = DateTime()
        self.cycle["start"] = self.runtime["jodaStart"].getMillis()
        self.cycle["startdt"] = str(self.runtime["jodaStart"])
        logger.info("Started cycle at %s", self.cycle["startdt"])

    def finishCycle(self):
        self.runtime["jodaEnd"] = DateTime()
        self.cycle["end"] = self.runtime["jodaEnd"].getMillis()
        self.cycle["enddt"] = str(self.runtime["jodaEnd"])
        self.cycle["laststart"] = self.cycle["start"]
        self.cycle["laststartdt"] = self.cycle["startdt"]
        self.cycle["elapsed"] = self.runtime["jodaEnd"].getMillis() - self.cycle["start"]
        logger.info("Finished cycle at %s", self.cycle["enddt"])

    def tick(self):
        self.processData({ "time": time.time() })

    def initialize(self):
        logger.info("Initializing probe before cycling")

    def cleanup(self):
        logger.info("Cleaning up after cycling")
        for output in self.output:
            if "outputmodule" in self.output[output]:
                outputType = "plugin"
            else:
                outputType = self.output[output]["class"]
            if outputType == "plugin":
                self.outputCleanup(output)

    def getCycleProperty(self, name):
        if name in self.cycle:
            return self.cycle[name]
        else:
            return None

    def getInputProperty(self, name):
        if name in self.input:
            return self.input[name]
        else:
            return None

    def setInputProperty(self, name, value):
        self.input[name] = value

    def getOutputProperty(self, output, name):
        if name in self.output[output]:
            return self.output[output][name]
        else:
            return None

    def setOutputProperty(self, output, name, value):
        self.output[output][name] = value

    def getRuntimeProperty(self, name):
        if name in self.runtime:
            return self.runtime[name]
        else:
            return None

    def setRuntimeProperty(self, name, value):
        self.runtime[name] = value

    def saveCycleState(self):
        storeCycleState = self.getInputProperty("storeCycleState")
        if storeCycleState == None:
            return False
        elif "enabled" in storeCycleState and storeCycleState["enabled"] == True:
            if "filename" in storeCycleState:
                configurationFile = storeCycleState["filename"]
            else:
                configurationFile = "probespawnerDB.json"
            logger.info("Saving cycle state to file %s", configurationFile)
            json_data = json.dumps(self.cycle)
            try:
                with open(configurationFile, "w") as data_file:
                    data_file.write(json_data)
            except Exception, ex:
                logger.warning("Unable to write cycle state to file %s", configurationFile)
        return True

    def loadCycleState(self):
        storeCycleState = self.getInputProperty("storeCycleState")
        if storeCycleState != None and "enabled" in storeCycleState and storeCycleState["enabled"] == True:
            if "filename" in storeCycleState:
                configurationFile = storeCycleState["filename"]
            else:
                configurationFile = "probespawnerDB.json"
            logger.info("Loading cycle state from file %s", configurationFile)
            try:
                with open(configurationFile) as data_file:
                    json_string = data_file.read()
                self.cycle = json.loads(json_string)
            except Exception, ex:
                logger.warning("Unable to read cycle state from file %s", configurationFile)
            
    # needed to implement the Callable interface;
    # any exceptions will be wrapped as either ExecutionException
    # or InterruptedException
    def call(self):
        self.thread_used = threading.currentThread().getName()
        self.started     = time.time()
        self.running     = True
        self.initialize()
        self.loadCycleState()

        while self.running:
            try:
                self.startCycle()
                self.startOutput()
                self.tick()
                self.stopOutput()

            # cycle catcher
            except Exception, ex:
                traceback.print_exc()
                self.exception = ex
                logger.error(ex)
                self.running = False
                self.completed = time.time()
            #TODO: remember finally

            self.finishCycle()
            self.saveCycleState()
            sleepTime = self.interval - self.cycle["elapsed"] / 1000
            if "maxCycles" in self.input and self.cycle["numCycles"] >= self.input["maxCycles"]:
                logger.info("Max cycles reached %d", self.cycle["numCycles"])
                sleepTime = 0
                self.running = False
            if (sleepTime < 0):
                sleepTime = 0
            logger.info("End of cycle: sleeping for %d seconds", sleepTime)
            time.sleep(sleepTime);
        #TODO: cleanup, make sure outputs have closed and whatnot
        self.cleanup()
        self.completed = time.time()
        return self