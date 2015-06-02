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
			logger.info("Got regex for parsing: %s", self.getInputProperty("regex"))
			self.groupRe = re.compile(self.getInputProperty("regex"))
		else:
			self.groupRe = None

		self.metrics = {}
		if self.getInputProperty("metrics") != None:
			for metric in self.getInputProperty("metrics"):
				self.metrics[metric] = 1
		self.terms = {}
		if self.getInputProperty("terms") != None:
			for term in self.getInputProperty("terms"):
				self.terms[term] = 1

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
				out["class"] = "exec"
				matches = re.match(self.groupRe, line)
				metrics = {}
				terms = {}
				if matches:
					for key in matches.groupdict():
						if key in self.metrics:
							metrics[key] = matches.group(key)
						elif key in self.terms:
							terms[key] = matches.group(key)
						else:
							out[key] = matches.group(key)
					self.processData(out)
					for key in metrics:
						try:
							out["metric"] = key
							if self.getInputProperty("decimalMark"):
								metrics[key] = metrics[key].replace(self.getInputProperty("decimalMark"), ".")
							out["value"] = float(metrics[key])
							self.processData(out)
						except Exception, ex:
							logger.warning("Failure to parse %s as float for metric %s", key, metrics[key])
						self.processData(out)
					if 'value' in out:
						del out['value']
					for key in terms:
						out["metric"] = key
						out["term"] = str(terms[key])
						self.processData(out)
				else:
					logger.debug("Discarding line \"%s\", no match", line)


