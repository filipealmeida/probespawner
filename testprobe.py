# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/
from dummyprobe import DummyProbe

class TestProbe(DummyProbe):
	def tick(self):
		self.processData({ "test": "Yes" })