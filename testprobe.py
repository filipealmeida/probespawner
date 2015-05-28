from dummyprobe import DummyProbe

class TestProbe(DummyProbe):
	def tick(self):
		self.processData({ "test": "Yes" })