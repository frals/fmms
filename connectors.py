#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
import os
import subprocess
import time
import shlex

import dbus
import conic

import controller as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

magic = 0xacdcacdc

CONNMODE_UGLYHACK = 1                                                          
CONNMODE_ICDSWITCH = 2                                                         
CONNMODE_FORCESWITCH = 3                                                       
CONNMODE_NULL = 10

class MasterConnector:
	""" handles setting up and (might) take down connection(s) """

	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		self.config = self.cont.config
		self._apn = self.config.get_apn()
		self._apn_nicename = self.config.get_apn_nicename()
		self.lock = fMMSController.Locker(self.config.get_lockfile())
	
	def connect(self, location="0"):
	
		# this is to make sure only one process has passed connect() at a time
		loop = 0
		while 1:
			if self.lock.lock():
				log.info("i acquired lock (%d)" % os.getpid())
				break
			else:
				# wait 2 sec before retrying
				time.sleep(2)
				loop += 1
				if loop == 5:
					log.info("probable deadlock, kill me please!")
				if loop > 30:
					log.info("time to die. bye!")
					raise Exception('Timeout while waiting for lock')
	
		if (self.config.get_connmode() == CONNMODE_UGLYHACK):
			log.info("RUNNING IN UGLYHACK MODE")

			(proxyurl, proxyport) = self.config.get_proxy_from_apn()
			apn = self.config.get_apn_from_osso()
			mmsc1 = self.cont.get_host_from_url(self.config.get_mmsc())
			mmsc2 = self.cont.get_host_from_url(location)
			user = self.config.get_user_for_apn()
			passwd = self.config.get_passwd_for_apn()
			try:
				self.connector = UglyHackHandler(apn, user, passwd, proxyurl, mmsc1, mmsc2)
				self.connector.start()
			except:
				log.exception("Connection failed.")

		elif (self.config.get_connmode() == CONNMODE_ICDSWITCH):
			log.info("RUNNING IN ICDSWITCH MODE")
			self.connector = ICDConnector(self._apn)
			self.connector.connect()
			# TODO: dont sleep this long unless we have to
			time.sleep(15)

		elif (self.config.get_connmode() == CONNMODE_FORCESWITCH):
			log.info("RUNNING IN FORCESWITCH MODE")
			self.connector = ForceConnector(self._apn)
			self.connector.connect()
			# TODO: dont sleep this long unless we have to
			time.sleep(15)
		
		elif (self.config.get_connmode() == CONNMODE_NULL):
			log.info("NOOP CONNMODE")
			self.connector = None
	
	def disconnect(self):
		self.lock.unlock()
		try:
			if self.connector:
				self.connector.disconnect()
		except:
			log.exception("Failed to close connection.")

	def __del__(self):
		try:
			self.lock.unlock()
		except:
			pass
		try:
			self.connector.disconnect()
		except:
			pass

class ICDConnector:
	""" this is the 'nice' autoconnecter, only goes online on
	the mms apn if no other conn is active """

	def __init__(self, apn):
		self.apn = apn
		self.connection = conic.Connection()
		
	def connection_cb(self, connection, event, mgc):
		#log.info("connection_cb(%s, %s, %x)" % (connection, event, mgc))
		pass	
		
	def disconnect(self):
		connection = self.connection
		connection.disconnect_by_id(self.apn)
		log.info("ICDConnector requested disconnect from id: %s", self.apn)

	def connect(self):
		global magic

		# Creates the connection object and attach the handler.
		connection = self.connection
		iaps = connection.get_all_iaps()
		iap = None
		for i in iaps:
			if i.get_id() == self.apn:
				iap = i
		
		if iap:
			connection.disconnect()
			log.info("ICDConnector trying to connect to ID: %s", iap.get_id())
		connection.connect("connection-event", self.connection_cb, magic)
		if iap:
			connection.request_connection_by_id(iap.get_id(), conic.CONNECT_FLAG_NONE)
		else:
			connection.request_connection(conic.CONNECT_FLAG_NONE)
		

class ForceConnector:
	""" this is the 'force switch' autoconnecter """
	# credits to Stuart Hopkins for implementing this as
	# a shell script and submitting as a patch
	
	def __init__(self, apn):
		self.apn = apn
		self.current_connection()
		self.connection = conic.Connection()
		
	def current_connection(self):
		bus = dbus.SystemBus()
		proxy = bus.get_object('com.nokia.icd', '/com/nokia/icd')
		icd = dbus.Interface(proxy, 'com.nokia.icd')
		try:
			(iapid, arg, arg1, arg2, arg3, arg4, arg5) = icd.get_statistics()
		except:
			iapid = None
		self.previousconn = iapid
		log.info("ForceConnector saved previous connection. ID: %s", iapid)
		
	def connection_cb(self, connection, event, mgc):
		#log.info("connection_cb(%s, %s, %x)" % (connection, event, mgc))
		pass
		
	""" restore connection to previous """
	def disconnect(self):
		log.info("ForceConnector restoring connection...")
		self.connect(self.previousconn)
	
	""" actually disconnects from the current iap before connecting """
	def connect(self, apn=None):
		global magic
		
		args = "DISCONNECT"
		subprocess.call(["/opt/fmms/fmms_magic", args])
		log.info("ForceConnector disconnecting from active connection.")

		if apn == None:
			apn = self.apn
	
		# Creates the connection object and attach the handler.
		connection = self.connection
		iaps = connection.get_all_iaps()
		iap = None
		for i in iaps:
			if i.get_id() == apn:
				iap = i
		
		if iap:		
			log.info("ForceConnector trying to connect to: ID: %s" % iap.get_id())
		connection.connect("connection-event", self.connection_cb, magic)
		
		if iap:
			connection.request_connection_by_id(iap.get_id(), conic.CONNECT_FLAG_NONE)
		else:
			connection.request_connection(conic.CONNECT_FLAG_NONE)


class UglyHackHandler:
	""" the ugly-hack autoconnector """
	
	def __init__(self, apn, username="", password="", proxy="0", mmsc1="0", mmsc2="0"):
		self.apn = apn
		self.username = username
		self.password = password
		if proxy == None:
			proxy = 0
		self.proxyip = proxy
		self.mmsc1 = mmsc1
		self.mmsc2 = mmsc2
		self.rx = 0
		self.tx = 0
		log.info("UglyHackHandler UP!\nAPN: %s user: %s pass: %s proxyip: %s mmsc1: %s mmsc2: %s" % (self.apn, self.username, self.password, self.proxyip, self.mmsc1, self.mmsc2))
		self.conn = None

	def start(self):
		try:
			self.conn = self.connect()
			args = "START %s %s %s %s %s %s" % (self.iface, self.ipaddr, self.mmsc1, self.mmsc2, self.dnsip, self.proxyip)
			retcode = subprocess.call(["/opt/fmms/fmms_magic", args])
			log.info("fmms_magic retcode: %s" % retcode)
		except:
			log.exception("connect/fmms_magic failed")
		
	def connect(self):
		if self.mmsc2 == "0":
			args = "/usr/bin/dbus-send --type=signal /se/frals/fmms/statusmenu se.frals.fmms.statusmenu.Show boolean:true string:'Sending'"
		else:
			args = "/usr/bin/dbus-send --type=signal /se/frals/fmms/statusmenu se.frals.fmms.statusmenu.Show boolean:true string:'Downloading'"

		try:
			args = shlex.split(args)
			subprocess.Popen(args)
		except:
			pass
	
		bus = dbus.SystemBus()
		gprs = dbus.Interface(bus.get_object("com.nokia.csd", "/com/nokia/csd/gprs"), "com.nokia.csd.GPRS")
		obj = gprs.QuickConnect(self.apn, "IP", self.username, self.password)
		conn = dbus.Interface(bus.get_object("com.nokia.csd", obj), "com.nokia.csd.GPRS.Context")
		(apn, ctype, self.iface, self.ipaddr, connected, tx, rx) = conn.GetStatus()
		
		tmp = bus.get_object("com.nokia.csd.GPRS", obj)
		props = dbus.Interface(tmp, "org.freedesktop.DBus.Properties")
		self.dnsip = props.Get("com.nokia.csd.GPRS.Context", "PDNSAddress")
		
		return conn
		
	def disconnect(self):
		log.info("UglyHackHandler running disconnect")
		args = "/usr/bin/dbus-send --type=signal /se/frals/fmms/statusmenu se.frals.fmms.statusmenu.Show boolean:false"
		try:
			args = shlex.split(args)
			subprocess.Popen(args)
		except:
			pass
		
		(apn, ctype, self.iface, self.ipaddr, connected, self.tx, self.rx) = self.conn.GetStatus()
		args = "STOP %s" % self.iface
		retcode = subprocess.call(["/opt/fmms/fmms_magic", args])
		log.info("disconnecting connection. rx: %s tx: %s" % (self.rx, self.tx))
		self.conn.Disconnect()