# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/

import com.rabbitmq.client.ConnectionFactory as ConnectionFactory
import com.rabbitmq.client.Connection as Connection
import com.rabbitmq.client.Channel as Channel
import com.rabbitmq.client.Address as Address

import traceback

import sys
import logging
logger = logging.getLogger(__name__)

class RabbitMQ():
	def __init__(self, config):
		#TODO: eliminate message count ASAP, check work with RabbitMQ features, remove spaghetti logic
		self.messagecount = 0
		self.config = config
		if "queue_name" in self.config:
			self.queue_name = self.config["queue_name"];
		else:
			self.queue_name = None
		if "routingKey" in self.config:
			self.routingKey = self.config["routingKey"];
		else:
			self.routingKey = ""
		if "host" in self.config:
			self.host = self.config["host"]
		else:
			self.host = "localhost"
		if "port" in self.config:
			self.port = self.config["port"]
		else:
			self.port = 5672
		if "username" in self.config:
			self.username = self.config["username"]
		else:
			self.username = None
		if "password" in self.config:
			self.password = self.config["password"]
		else:
			self.password = None
		if "virtualhost" in self.config:
			self.virtualhost = self.config["virtualhost"]
		else:
			self.virtualhost = None
		if "uri" in self.config:
			self.uri = self.config["uri"]
		else:
			self.uri = None
		if "networkRecoveryInterval" in self.config:
			self.networkRecoveryInterval = self.config["networkRecoveryInterval"]
		else:
			self.networkRecoveryInterval = None
		if "automaticRecoveryEnabled" in self.config:
			self.automaticRecoveryEnabled = self.config["automaticRecoveryEnabled"]
		else:
			self.automaticRecoveryEnabled = None
		if "topologyRecoveryEnabled" in self.config:
			self.topologyRecoveryEnabled = self.config["topologyRecoveryEnabled"]
		else:
			self.topologyRecoveryEnabled = None
		if "exchange" in self.config:
			self.exchange = self.config["exchange"]
		else:
			self.exchange = ""

		self.addresses = []
		if "addresses" in self.config:
			for address in self.config["addresses"]:
				logger.info(address)
				self.addresses.append(Address.parseAddress(address))

		self.initialize();

	def initialize(self):
		self.factory = ConnectionFactory()
		if self.networkRecoveryInterval != None:
			self.factory.setNetworkRecoveryInterval(self.networkRecoveryInterval)
		if self.automaticRecoveryEnabled != None:
			self.factory.setAutomaticRecoveryEnabled(self.automaticRecoveryEnabled)
		if self.topologyRecoveryEnabled != None:
			self.factory.setTopologyRecoveryEnabled(self.topologyRecoveryEnabled)
		if self.uri != None:
			logger.info("Initializing RabbitMQ with uri: %s", self.uri)
			self.factory.setUri(self.uri)
			self.connection = self.factory.newConnection()
		else:
			logger.info("Initializing RabbitMQ")
			self.addresses.append(Address(self.host, self.port))
			if (self.username != None):
				self.factory.setUsername(self.username)
			if (self.password != None):
				self.factory.setPassword(self.password)
			if (self.virtualhost != None):
				self.factory.setVirtualHost(self.virtualhost)
			self.connection = self.factory.newConnection(self.addresses)

		self.channel = self.connection.createChannel()
		if (self.queue_name != None):
			self.channel.queueDeclare(self.queue_name, False, False, False, None)

	def writeDocument(self, data, force):
		self.messagecount += 1
		if (isinstance(data,dict)):
			#TODO: this is complete chaos, rethink on how to deal with dictionaries, for now, will send only values, keys will be ignored
			for k, v in data.items():
				if self.queue_name != None:
					logger.debug("Publishing to rabbit queue %s: %s", self.queue_name, v)
					self.channel.basicPublish(self.exchange, self.queue_name, None, str(v))
				else:
					logger.debug("Writing to rabbit exchange %s: %s", self.exchange, v)
					self.channel.basicPublish(self.exchange, self.routingKey, None, str(v))
		else:
			if self.queue_name != None:
				logger.debug("Publishing to rabbit queue %s: %s", self.queue_name, data)
				self.channel.basicPublish(self.exchange, self.queue_name, None, data)
			else:
				logger.debug("Writing to rabbit exchange %s: %s", self.exchange, data)
				self.channel.basicPublish(self.exchange, self.routingKey, None, data)

	def flush(self):
		logger.info("Flushing. Total messages: %d", self.messagecount)
		return True

	def cleanup(self):
		self.channel.close()
		self.connection.close()


