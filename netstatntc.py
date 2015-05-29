# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

from dummyprobe import DummyProbe
import subprocess
import re
import platform
import org.joda.time.DateTime as DateTime

import logging
logger = logging.getLogger(__name__)
#qActive Internet connections (w/o servers)
#Proto Recv-Q Send-Q Local Address           Foreign Address         State   
class LinuxNetstatNTC(DummyProbe):
	def initialize(self):
		self.regexHeader = re.compile(r'^Proto[\t ]+Recv-Q[\t ]+Send-Q[\t ]+Local Address[\t ]+Foreign Address[\t ]+State')
		self.regexActiveHeader = re.compile(r'^Active (\w+)')
		self.regexBoundary = re.compile(r'[\t ]+')
		self.regexIpSplit  = re.compile(r'(.*):(.+)$') 
		self.fields = ['protocol', 'receive-q', 'send-q', 'local', 'foreign', 'state', 'user', 'inode']
		if (self.getInputProperty("command") != None):
			self.cmd = self.getInputProperty("command")
		else:
			self.cmd = "netstat -ntc"

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
			matchActiveHeader = re.search(self.regexActiveHeader, line)
			if (matchActiveHeader):
				out = {}
				if (matchActiveHeader.group(1) == 'Internet'):
					state = 5
				else:
					state = 0
			elif (state == 5):
				matchHeader = re.search(self.regexHeader, line)
				if (matchHeader):
					state = 10
					out["@timestamp"] = nowStr
					out["host"] = platform.node()
					out["class"] = "tcpconnections"
			elif (state == 10):
				idx = 0
				values = re.split(self.regexBoundary, line)
				for value in values:
					field = self.fields[idx]
					if ((field == 'receive-q') or (field == 'send-q')):
						values[idx] = float(value)
					elif (field == 'local'):
						pair = re.search(self.regexIpSplit, value)
						out['localip'] = pair.group(1)
						out['localport'] = float(pair.group(2))
					elif (field == 'foreign'):
						pair = re.search(self.regexIpSplit, value)
						out['foreignip'] = pair.group(1)
						out['foreignport'] = float(pair.group(2))
					out[field] = values[idx]
					idx+=1
				self.processData(out)






