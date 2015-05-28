from dummyprobe import DummyProbe
import subprocess
import re
import platform
import org.joda.time.DateTime as DateTime

import logging
logger = logging.getLogger(__name__)

class LinuxNetstatS(DummyProbe):
	def initialize(self):
		self.regexClass = re.compile(r'^([a-zA-Z0-9]+):$')
		self.regexSubClass = re.compile(r'([a-zA-Z0-9 ,]+):$')
		self.regexValueColon = re.compile(r'^[\t ]+(\w+):[\t ]+(\d+)')
		self.regexValueAtStart = re.compile(r'^[\t ]+(\d+)[\t ]+(.*)')
		self.regexMatchDigits = re.compile(r'(\d+)')
		if (self.getInputProperty("command") != None):
			self.cmd = self.getInputProperty("command")
		else:
			self.cmd = "netstat -s"

	def tick(self):
		stream = subprocess.Popen(self.cmd, shell=True, bufsize=0, stdout=subprocess.PIPE)
		dt = str(DateTime())
		ps = 0 #parser state
		fields = []
		state = 0
		out = {}
		nowStr = self.getCycleProperty("startdt")
		for line in stream.stdout:
			line = line.rstrip()
			out["@timestamp"] = nowStr
			out["host"] = platform.node()
			matchClass = re.search(self.regexClass, line)
			if (matchClass):
				logger.debug("Matched stats group")
				out["class"] = matchClass.group(1).lstrip()
				nowStr = str(DateTime())
				state = 10
				logger.debug(out)
			elif (state == 10):
				out["value"] = None
				matchColon = re.search(self.regexValueColon, line)
				if (matchColon):
					out["metric"] = matchColon.group(1).lstrip()
					out["value"] = float(matchColon.group(2))
				else:
					matchValueAtStart = re.search(self.regexValueAtStart, line)
					if (matchValueAtStart):
						out["value"] = float(matchValueAtStart.group(1))
						out["metric"] = matchValueAtStart.group(2).lstrip()
					else:
						matchValueAnywhere = re.search(self.regexMatchDigits, line)
						if (matchValueAnywhere):
							out["value"] = float(matchValueAnywhere.group(1))
							out["metric"] = re.sub(self.regexMatchDigits, "", line).lstrip()
				if (out["value"] != None):
					self.processData(out)





