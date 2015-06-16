# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/



import platform
from random import randint
import atexit
import errno
#import fcntl
import os
import random
import re
import signal
import socket
import subprocess
import sys
import threading
import time

import sys
import logging
logger = logging.getLogger(__name__)

ALIVE = True

class OpenTSDB():
	def __init__(self, config):
		#TODO: eliminate message count ASAP, check work with RabbitMQ features
		global ALIVE
		self.messagecount = 0
		self.config = config
		if "host" in self.config:
			self.host = self.config["host"]
		else:
			self.host = None
		if "port" in self.config:
			self.port = self.config["port"]
		else:
			self.port = None
		if "username" in self.config:
			self.username = self.config["username"]
		else:
			self.username = None
		if "password" in self.config:
			self.password = self.config["password"]
		else:
			self.password = None
		self.tags = []
		if "tags" in self.config:
			self.tags = self.config["tags"]

		self.addresses = []
		if "addresses" in self.config:
			for address in self.config["addresses"]:
				logger.info(address)
				self.addresses.append(address.split(":"))
		if (self.host != None and self.port != None):
			self.addresses.append((self.host, self.port))
			self.host = None;
			self.port = None;

		self.metrics = {}
		if "metrics" in self.config:
			for metric in self.config["metrics"]:
				self.metrics[metric] = 1

		self.tags.append("node=" + platform.node())
		self.initialize();

	#TODO: create blacklist, check tcollector.py
	def pickConnection(self):
		self.host, self.port = self.addresses[randint(0, len(self.addresses) - 1)]
		logger.info('Selected connection: %s:%d', self.host, self.port);

	def blacklistConnection(self):
		return False

	def verifyConnection(self):
		if self.tsd is None:
			return False
		if self.lastVerify > time.time() - 60:
			return True
		if self.reconnectInterval > 0 and self.timeReconnect < time.time() - self.reconnectInterval:
			try:
				self.tsd.close()
			except socket.error, msg:
				pass    # not handling that
			self.timeReconnect = time.time()
			return False
		logger.info("Testing connection life")
		try:
			self.tsd.sendall('version\n')
		except socket.error, msg:
			self.tsd = None
			self.blacklistConnection()
			return False

		bufsize = 4096
		while ALIVE:
			try:
				buf = self.tsd.recv(bufsize)
			except socket.error, msg:
				logger.warning('Socket error %s:%d: %s',self.host, self.port, msg)
				self.tsd = None
				self.blacklistConnection()
				return False
			if len(buf) == bufsize:
				continue
			break

		logger.info("Connection verified")
		self.lastVerify = time.time()
		return True

	def makeConnection(self):
		try_delay = 1
		while ALIVE:
			if self.verifyConnection():
				return True
			try_delay *= 1 + random.random()
			if try_delay > 600:
				try_delay *= 0.5
			logger.info('SenderThread blocking %0.2f seconds', try_delay)
			time.sleep(try_delay)

			self.pickConnection()
			try:
				addresses = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0)
			except socket.gaierror, e:
				if e[0] in (socket.EAI_AGAIN, socket.EAI_NONAME,socket.EAI_NODATA):
					logger.info('DNS resolution failure: %s: %s', self.host, e)
					continue
				raise
			for family, socktype, proto, canonname, sockaddr in addresses:
				try:
					self.tsd = socket.socket(family, socktype, proto)
					self.tsd.settimeout(15)
					self.tsd.connect(sockaddr)
					logger.info('Connection to %s was successful'%(str(sockaddr)))
					break
				except socket.error, msg:
					logger.warning('Connection attempt failed to %s:%d: %s',self.host, self.port, msg)
				self.tsd.close()
				self.tsd = None
			if not self.tsd:
				logger.error('Failed to connect to %s:%d', self.host, self.port)
				self.blacklistConnection()


	def initialize(self):
		self.tsd = None
		self.lastVerify = time.time() - 60
		self.reconnectInterval = 86400
		self.timeReconnect = 0
		return True

	#TODO: handle exceptions on sendall
	def writeDocument(self, data, force):
		self.makeConnection()
		try:
			out = ''
			#out = "".join("put %s\n" % self.add_tags_to_line(line) for line in self.sendq)
			#if it's not a metric, it's a tag
			tags = []
			for key in data:
				if key not in self.metrics:
					if key == "@timestamp":
						continue
					key_str = key + "=" + data[key]
					key_str = key_str.replace(" ", "_")
					key_str = key_str.replace("@", "")
					tags.append(key_str)

			tags_str = " ".join(tags)
			time_str = str(int(time.time() * 1000))
			for key in data:
				if key in self.metrics:
					out = "put probespawner." + key + " " + time_str + " " + str(data[key]) + " " + tags_str + "\n"
					self.tsd.sendall(out)
					self.messagecount = self.messagecount + 1
					logger.info(out)

			if "metric_field" in self.config and "value_field" in self.config:
				if self.config["metric_field"] in data and self.config["value_field"] in data:
					out = "put probespawner." + data[self.config["metric_field"]] + " " + time_str + " " + str(data[self.config["value_field"]]) + " " + tags_str + "\n"
					self.tsd.sendall(out)
					self.messagecount = self.messagecount + 1
					logger.info(out)

		except Exception, ex:
			logger.error("Some error writing document, will retry?")
			logger.error(data)
			raise
			#self.writeDocument(data, force)

	def flush(self):
		logger.info("Flushing. Total messages: %d", self.messagecount)
		return True

	def cleanup(self):
		self.tsd.close()
		self.tsd = None
		return True


