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
		#ConnectionFactory factory = new ConnectionFactory();
		#factory.setHost("localhost");
		#Connection connection = factory.newConnection();
		#Channel channel = connection.createChannel();
		#channel.queueDeclare(QUEUE_NAME, false, false, false, null);
		#String message = "Hello World!";
		#channel.basicPublish("", QUEUE_NAME, null, message.getBytes());
		#System.out.println(" [x] Sent '" + message + "'");
		#channel.close();
		#connection.close();
		self.config = config
		self.queue_name = self.config["queue_name"];
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
		self.channel.queueDeclare(self.queue_name, False, False, False, None)

	def writeDocument(self, data, force):
		self.channel.basicPublish("", self.queue_name, None, data)

	def cleanup(self):
		self.channel.close()
		self.connection.close()


