from dummyprobe import DummyProbe
import subprocess

class ExecProbe(DummyProbe):
	def tick(self):
		stream = subprocess.Popen(self.getInputProperty("command"), shell=True, stdout=subprocess.PIPE)
		for line in stream.stdout:
			line = line.rstrip()
			self.processData({ "@timestamp": self.getCycleProperty("startdt"), "value" : stream.stdout.readline() })
