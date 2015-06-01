from dummyprobe import DummyProbe
import subprocess
import platform
import re
import com.xhaus.jyson.JysonCodec as json

import logging
logger = logging.getLogger(__name__)

class ExecProbe(DummyProbe):
	def initialize(self):
		if self.getInputProperty("regex") != None:
			self.groupRe = re.compile(self.getInputProperty("regex"))
			#self.groupRe = re.compile(r'^([\t ]+?)(\d+)')
			logger.info(self.groupRe)
		else:
			self.groupRe = None

		self.metrics = {}
		if self.getInputProperty("metrics") != None:
			for metric in self.getInputProperty("metrics"):
				self.metrics[metric] = 1

	def tick(self):
		stream = subprocess.Popen(self.getInputProperty("command"), shell=True, bufsize=0, stdout=subprocess.PIPE)
		for line in stream.stdout:
			line = line.rstrip()
			out = {}
			if self.groupRe == None:
				self.processData({ "@timestamp": self.nowDt(), "value" : line })
			else:
				out["@timestamp"] = self.nowDt()
				out["command"] = self.getInputProperty("command")
				out["host"] = platform.node()
				matches = re.match(self.groupRe, line)
				metrics = {}
				if matches:
					for key in matches.groupdict():
						if key in self.metrics:
							metrics[key] = matches.group(key)
						else:
							out[key] = matches.group(key)
					for key in metrics:
						#TODO: check if string or numeric, deal accordingly
						out["metric"] = key
						out["value"] = float(metrics[key])
						self.processData(out)
				else:
					logger.debug("Discarding line \"%s\", no match", line)


