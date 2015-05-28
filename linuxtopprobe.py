from dummyprobe import DummyProbe
import subprocess
import re
import platform
import org.joda.time.DateTime as DateTime


#top - 19:39:32 up 2 days, 21:42,  7 users,  load average: 1,99, 1,34, 0,92
#Threads: 811 total,   2 running, 776 sleeping,   0 stopped,  33 zombie
#%Cpu(s):  5,7 us,  3,8 sy,  0,0 ni, 89,4 id,  1,0 wa,  0,0 hi,  0,2 si,  0,0 st
#KiB Mem:   3071096 total,  2722196 used,   348900 free,    11716 buffers
#KiB Swap:  3111932 total,   680060 used,  2431872 free.   438492 cached Mem
#
#  PID  PPID nTH USER      PR  NI    VIRT    RES    SHR   SWAP S %CPU P %MEM     TIME+ WCHAN      COMMAND
# 2165  2092   7 fra       20   0  770068 108952  17272 107068 R  4,3 0  3,5  93:38.70 wait_seqno cinnamon
import logging
logger = logging.getLogger(__name__)

class LinuxTopProbe(DummyProbe):
	def initialize(self):
		#top - 10:55:53 up 40 min,  3 users,  load average: 1,79, 1,06, 0,82
		self.regexHeader = re.compile(r'^top\ +-\ +(\d+:\d+:\d+)')
		self.regexLoad = re.compile(r'(\d+)[\t ]+users,[\t ]+load average:[\t ]+(\d+[.,]?\d+),[\t ]+(\d+[.,]?\d+),[\t ]+(\d+[.,]?\d+)')
		self.regexEmptyline = re.compile(r'^$')
		self.regexTasks = re.compile(r'^Tasks:')
		self.regexThreads = re.compile(r'^Threads:')
		self.regexCpu = re.compile(r'^%?Cpu')
		self.regexMemory = re.compile(r'Mem:')
		self.regexSwap = re.compile(r'Swap:')
		self.regexFields = re.compile(r'PID|PPID|USER|COMMAND')
		self.regexCommaBoundary = re.compile(r',[\t ]+')
		self.regexComma = re.compile(r',')
		self.regexColon = re.compile(r':')
		self.regexLtrim = re.compile(r'^[\t ]+')
		self.regexRtrim = re.compile(r'[\t ]+$')
		self.regexBoundary = re.compile(r'[\t %]+')
		self.regexHeaderDesc = re.compile(r'.+:')
		self.processMetrics = {'TIME+':1, '%MEM':1, 'SHR':1, 'NI':1, 'RES':1, 'SWAP':1, 'VIRT':1, 'P':1, '%CPU':1, 'CODE':1, 'DATA':1, 'USED':1, 'nDRT':1, 'nMaj':1, 'nMin':1, 'nTH':1, 'vMj':1, 'vMn':1, 'CPU':1, 'MEM':1}
		if (self.getInputProperty("command") != None):
			self.cmd = self.getInputProperty("command")
		else:
			self.cmd = "top -Hbi -n20 -d5 -w512"

	def computeValue(self, value):
		if (isinstance(value, str)):
			if (value[-1] == 'k'):
				value = float(value[:-1]) * 1024
			elif (value[-1] == 'm'):
				value = float(value[:-1]) * 1024 * 1024
			elif (value[-1] == 'g'):
				value = float(value[:-1]) * 1024 * 1024 * 1024
			elif (value[-1] == '%'):
				value = float(value[:-1])
			else:
				value = float(value)
		return value


	def storeHeaderLine(self, line, out):
		data = {}
		line = re.sub(self.regexHeaderDesc, "", line)
		line = re.sub(self.regexLtrim, "", line)
		line = re.sub(self.regexRtrim, "", line)
		pairs = re.split(self.regexCommaBoundary, line)
		for pair in pairs:
			values = re.split(self.regexBoundary, pair)
			val = float(self.computeValue(re.sub(self.regexComma, ".", values[0])));
			key = values[1]
			for k in out:
				data[k] = out[k]
			data["metric"] = key
			data["value"] = val
			self.processData(data)

	def tick(self):
		stream = subprocess.Popen(self.cmd, shell=True, bufsize=0, stdout=subprocess.PIPE)
		#stream = subprocess.Popen('cat top.command.out.txt', shell=True, bufsize=0, stdout=subprocess.PIPE)
		dt = str(DateTime())
		ps = 0 #parser state
		fields = []
		state = 0
		nowStr = self.getCycleProperty("startdt")
		for line in stream.stdout:
			line = line.rstrip()
			out = {}
			out["@timestamp"] = nowStr
			out["host"] = platform.node()
			matchHeader = re.match(self.regexHeader, line)
			if (matchHeader):
				logger.debug("Matched header")
				matchLoad = re.search(self.regexLoad, line)
				out["class"] = "Uptime"
				nowStr = str(DateTime())
				if (matchLoad):
					self.processData({ "@timestamp": out['@timestamp'], "host": out["host"], "class": out["class"], "metric": "users", "value": float(re.sub(self.regexComma, ".", matchLoad.group(1))) })
					self.processData({ "@timestamp": out['@timestamp'], "host": out["host"], "class": out["class"], "metric": "load1", "value": float(re.sub(self.regexComma, ".", matchLoad.group(2))) })
					self.processData({ "@timestamp": out['@timestamp'], "host": out["host"], "class": out["class"], "metric": "load5", "value": float(re.sub(self.regexComma, ".", matchLoad.group(3))) })
					self.processData({ "@timestamp": out['@timestamp'], "host": out["host"], "class": out["class"], "metric": "load15", "value": float(re.sub(self.regexComma, ".", matchLoad.group(4))) })
				state = 10
			if (state == 10):
				matchTasks = re.match(self.regexTasks, line)
				if (matchTasks):
					logger.debug("Matched Tasks")
					out["class"] = "Tasks"
					self.storeHeaderLine(line, out)
					state = 20
			if (state == 10):
				matchThreads = re.match(self.regexThreads, line)
				if (matchThreads):
					logger.debug("Matched Threads")
					out["class"] = "Threads"
					self.storeHeaderLine(line, out)
					state = 20
			if (state == 20):
				matchCpu = re.match(self.regexCpu, line)
				if (matchCpu):
					logger.debug("Matched Cpu")
					out["class"] = "Cpu"
					self.storeHeaderLine(line, out)
					state = 30
			elif (state == 30):
				matchMem = re.search(self.regexMemory, line)
				if (matchMem):
					logger.debug("Matched Memory")
					out["class"] = "Memory"
					self.storeHeaderLine(line, out)
					state = 40
			elif (state == 40):
				matchSwap = re.search(self.regexSwap, line)
				if (matchSwap):
					logger.debug("Matched Swap")
					out["class"] = "Swap"
					line = re.sub(r'free\.', "free,", line)
					self.storeHeaderLine(line, out)
					state = 50
			elif (state == 50):
				matchFields = re.search(self.regexFields, line)
				if (matchFields):
					logger.debug("Matched Fields")
					line = re.sub(self.regexLtrim, "", line)
					fields = re.split(self.regexBoundary, line)
					state = 60
			elif (state == 60):
				if (re.match(self.regexEmptyline, line)):
					logger.debug("Empty line found")
				else:
					line = re.sub(self.regexLtrim, "", line)
					values = re.split(self.regexBoundary, line)
					idx = 0
					data = {}
					out["class"] = "Process"
					logger.debug(fields)
					for field in fields:
						if (field not in self.processMetrics):
							out[field] = values[idx]
						else:
							if (field == 'TIME+'):
								value = 0
								parts = re.split(self.regexColon, re.sub(self.regexComma, ".", values[idx]))
								multiplier = 1
								while (len(parts) > 0):
									seconds = float(parts.pop())
									value = value + seconds * multiplier
									multiplier = multiplier * 60
								data[field] = value
							else:
								data[field] = self.computeValue(re.sub(self.regexComma, ".", values[idx]))
						idx += 1
					for metric in data:
						out["metric"] = metric
						out["value"] = float(data[metric])
						self.processData(out)


