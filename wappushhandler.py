#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Class for handling wap push messages and creating MMS messages

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import sys
import os
import dbus
import urllib2
import httplib
import time
import socket
import array
import subprocess

import dbus
from dbus.mainloop.glib import DBusGMainLoop
import conic

from mms import message
from mms.message import MMSMessage
from mms import mms_pdu
import fmms_config as fMMSconf
import controller as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

magic = 0xacdcacdc

CONNMODE_UGLYHACK = 1
CONNMODE_ICDSWITCH = 2
CONNMODE_FORCESWITCH = 3

_DBG = True

class PushHandler:
	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._apn = self.config.get_apn()
		self._apn_nicename = self.config.get_apn_nicename()
		self._incoming = self.config.get_imgdir() + "/LAST_INCOMING"

	""" handle incoming push over sms """
	def _incoming_sms_push(self, source, src_port, dst_port, wsp_header, wsp_payload):
		dbus_loop = DBusGMainLoop()
		args = (source, src_port, dst_port, wsp_header, wsp_payload)
		
		# TODO: dont hardcode
		if not os.path.isdir(self.config.get_imgdir()):
			os.makedirs(self.config.get_imgdir())
		
		f = open(self._incoming, 'w')
		for arg in args:
		    f.write(str(arg))
		    f.write('\n')
		f.close()

		if(_DBG):
			log.info("SRC: %s:%s", source, src_port)
			log.info("DST: %s", dst_port)
			#print "WSPHEADER: ", wsp_header
			#print "WSPPAYLOAD: ", wsp_payload

		binarydata = []
		# throw away the wsp_header!
		#for d in wsp_header:
		#	data.append(int(d))
		
		for d in wsp_payload:
			binarydata.append(int(d))

		log.info("decoding...")
		
		
		(data, sndr, url, trans_id) = self.cont.decode_mms_from_push(binarydata)
		
		log.info("saving...")
		# Controller should save it
		pushid = self.cont.save_push_message(data)
		log.info("notifying push...")
		# Send a notify we got the SMS Push and parsed it A_OKEY!
		self.notify_mms(dbus_loop, sndr, "SMS Push for MMS received")
		log.info("fetching mms...")
		path = self._get_mms_message(url, trans_id)
		log.info("decoding mms... path: %s", path)
		message = self.cont.decode_binary_mms(path)
		log.info("storing mms...")
		mmsid = self.cont.store_mms_message(pushid, message)
		log.info("notifying mms...")
		self.notify_mms(dbus_loop, sndr, "New MMS", trans_id);
		return 0


	""" handle incoming ip push """
	# TODO: implement this
	def _incoming_ip_push(self, src_ip, dst_ip, src_port, dst_port, wsp_header, wsp_payload):
		if(_DBG):
			log.info("SRC: %s:%s", src_ip, src_port)
			log.info("DST: %s:%s", dst_ip, dst_port)


	""" notifies the user with a org.freedesktop.Notifications.Notify, really fancy """
	def notify_mms(self, dbus_loop, sender, message, path=None):
		bus = dbus.SystemBus()
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = dbus.Interface(proxy,dbus_interface='org.freedesktop.Notifications')
		choices = ['default', 'cancel']
		if path == None:
			interface.Notify('MMS', 0, '', message, sender, choices, {"category": "sms-message", "dialog-type": 4, "led-pattern": "PatternCommunicationEmail", "dbus-callback-default": "se.frals.fmms /se/frals/fmms se.frals.fmms open_gui"}, -1)
		else:
			interface.Notify("MMS", 0, '', message, sender, choices, {"category": "email-message", "dialog-type": 4, "led-pattern": "PatternCommunicationEmail", "dbus-callback-default": "se.frals.fmms /se/frals/fmms se.frals.fmms open_mms string:\"" + path + "\""}, -1)


	def _get_mms_message(self, location, transaction):
		
		connector = MasterConnector()
		connector.connect(location)
				
		try:
			dirname = self.__get_mms_message(location, transaction)
		except:
			log.exception("Something went wrong with getting the message... bailing out")
			connector.disconnect()
			raise
		
		# send acknowledge we got it ok
		try:
			socket.setdefaulttimeout(20)
			ack = self._send_acknowledge(transaction)
			log.info("ack sent")
		except:
			log.exception("sending ack failed")
		
		connector.disconnect()
		
		return dirname
		
			


	""" get the mms message from content-location """
	""" thanks benaranguren on talk.maemo.org for patch including x-wap-profile header """
	def __get_mms_message(self, location, transaction):
		log.info("getting file: %s", location)
		try:
			(proxyurl, proxyport) = self.config.get_proxy_from_apn()
			
			try:
				socket.setdefaulttimeout(20)
				notifyresp = self._send_notify_resp(transaction)
				log.info("notifyresp sent")
			except Exception, e:
				log.exception("notify sending failed: %s %s", type(e), e)
			
			# TODO: configurable time-out?
			timeout = 30
			socket.setdefaulttimeout(timeout)
			
			if proxyurl == "" or proxyurl == None:
				log.info("connecting without proxy")
			else:
				proxyfull = str(proxyurl) + ":" + str(proxyport)
				log.info("connecting with proxy %s", proxyfull)
				proxy = urllib2.ProxyHandler({"http": proxyfull})
				opener = urllib2.build_opener(proxy)
				urllib2.install_opener(opener)

			headers = {'User-Agent' : self.config.get_useragent(), 'x-wap-profile' : 'http://mms.frals.se/n900.rdf'}
			log.info("trying url: %s", location)
			req = urllib2.Request(location, headers=headers)
			mmsdata = urllib2.urlopen(req)
			try:
				log.info("mmsc info: %s", mmsdata.info())
			except:
				pass
			
			mmsdataall = mmsdata.read()
			dirname = self.cont.save_binary_mms(mmsdataall, transaction)
			
			log.info("fetched %s and wrote to file", location)
			

		except Exception, e:
			log.exception("fatal: %s %s", type(e), e)
			bus = dbus.SystemBus()
			proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
			interface = dbus.Interface(proxy,dbus_interface='org.freedesktop.Notifications')
			interface.SystemNoteInfoprint ("fMMS: Failed to download MMS message.")
			raise
		
		return dirname


	def _send_notify_resp(self, transid):
		mms = MMSMessage(True)
		mms.headers['Message-Type'] = "m-notifyresp-ind"
		mms.headers['Transaction-Id'] = transid
		mms.headers['MMS-Version'] = "1.3"
		mms.headers['Status'] = "Deferred"
		
		sender = MMSSender(customMMS=True)
		log.info("sending notify...")
		out = sender.sendMMS(mms)
		log.info("m-notifyresp-ind: %s", out)
		return out
	
	
	def _send_acknowledge(self, transid):
		mms = MMSMessage(True)
		mms.headers['Message-Type'] = "m-acknowledge-ind"
		mms.headers['Transaction-Id'] = transid
		mms.headers['MMS-Version'] = "1.3"
		
		ack = MMSSender(customMMS=True)
		log.info("sending ack...")
		out = ack.sendMMS(mms)
		log.info("m-acknowledge-ind: %s", out)
		return out


""" class for sending an mms """    	    
class MMSSender:
	def __init__(self, number=None, subject=None, message=None, attachment=None, sender=None, customMMS=None, setupConn=False):
		self.customMMS = customMMS
		self.config = fMMSconf.fMMS_config()
		self.cont = fMMSController.fMMS_controller()
		self.setupConn = setupConn
		if customMMS == None:
			self.number = number
			self.subject = subject
			self.message = message
			self.attachment = attachment
			self._mms = None
			self._sender = sender
			self.createMMS()
			if self.setupConn == True:
				self.connector = MasterConnector()
				self.connector.connect()
				
	    
	def createMMS(self):
		slide = message.MMSMessagePage()
		if self.attachment != None:
			slide.addImage(self.attachment)
		slide.addText(self.message)

		self._mms = message.MMSMessage()
		self._mms.headers['Subject'] = self.subject
		if "@" in self.number:
			self._mms.headers['To'] = str(self.number)
		else:
			self._mms.headers['To'] = str(self.number) + '/TYPE=PLMN'
		self._mms.headers['From'] = str(self._sender) + '/TYPE=PLMN'
		self._mms.addPage(slide)
	
	def sendMMS(self, customData=None):
		mmsid = None
		if customData != None:
			log.info("using custom mms")
			self._mms = customData
	
		mmsc = self.config.get_mmsc()
		
		(proxyurl, proxyport) = self.config.get_proxy_from_apn()
		mms = self._mms.encode()
		
		headers = {'Content-Type':'application/vnd.wap.mms-message', 'User-Agent' : self.config.get_useragent(), 'x-wap-profile' : 'http://mms.frals.se/n900.rdf'}
		#headers = {'Content-Type':'application/vnd.wap.mms-message'}
		if proxyurl == "" or proxyurl == None:
			print "connecting without proxy"
			mmsc = mmsc.lower()
			mmsc = mmsc.replace("http://", "")
			mmsc = mmsc.rstrip('/')
			mmsc = mmsc.partition('/')
			mmschost = mmsc[0]
			path = "/" + str(mmsc[2])
			log.info("mmschost: %s path: %s pathlen: %s", mmschost, path, len(path))
			conn = httplib.HTTPConnection(mmschost)
			conn.request('POST', path , mms, headers)
		else:
			log.info("connecting via proxy %s:%s", proxyurl, str(proxyport))
			log.info("mmschost: %s", mmsc)
			conn = httplib.HTTPConnection(proxyurl + ":" + str(proxyport))
			conn.request('POST', mmsc, mms, headers)

		if customData == None:			
			cont = fMMSController.fMMS_controller()
			path = cont.save_binary_outgoing_mms(mms, self._mms.transactionID)
			message = cont.decode_binary_mms(path)
			mmsid = cont.store_outgoing_mms(message)	
			
		res = conn.getresponse()
		log.info("MMSC STATUS: %s %s", res.status, res.reason)
		out = res.read()
		parsed = False
		try:
			decoder = mms_pdu.MMSDecoder()
			data = array.array('B')
			for b in out:
				data.append(ord(b))
			outparsed = decoder.decodeResponseHeader(data)
			parsed = True
			
			if mmsid != None:
				pushid = cont.store_outgoing_push(outparsed)
				cont.link_push_mms(pushid, mmsid)
				
		except Exception, e:
			print type(e), e
			outparsed = out
			
		log.info("MMSC RESPONDED: %s", outparsed)

		if self.setupConn == True:
			try:
				self.connector.disconnect()
			except:
				log.exception("Failed to close connection.")
		
		return res.status, res.reason, outparsed, parsed


""" handles setting up and (might) take down connection(s) """
class MasterConnector:

	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		self.config = fMMSconf.fMMS_config()
		self._apn = self.config.get_apn()
		self._apn_nicename = self.config.get_apn_nicename()
	
	
	def connect(self, location="0"):
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
			self.connector = ICDConnector(self._apn_nicename)
			self.connector.connect()
			# TODO: dont sleep this long unless we have to
			time.sleep(15)

		elif (self.config.get_connmode() == CONNMODE_FORCESWITCH):
			log.info("RUNNING IN FORCESWITCH MODE")
			self.connector = ForceConnector(self._apn_nicename)
			self.connector.connect()
			# TODO: dont sleep this long unless we have to
			time.sleep(15)
	
	
	def disconnect(self):
		try:
			self.connector.disconnect()
		except:
			log.exception("Failed to close connection.")
	



""" this is the 'nice' autoconnecter, only goes online on
the mms apn if no other conn is active """
class ICDConnector:
	
	def __init__(self, apn):
		self.apn = apn
		self.connection = conic.Connection()
		
	def connection_cb(self, connection, event, magic):
		#log.info("connection_cb(%s, %s, %x)" % (connection, event, magic))
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
			if i.get_name() == self.apn:
				iap = i

		connection.disconnect()
		log.info("ICDConnector trying to connect to: %s", iap.get_name())
		connection.connect("connection-event", self.connection_cb, magic)

		if iap:
			connection.request_connection_by_id(iap.get_id(), conic.CONNECT_FLAG_NONE)
		else:
			connection.request_connection(conic.CONNECT_FLAG_NONE)
		
		
		

""" this is the 'force switch' autoconnecter """
""" credits to Stuart Hopkins for implementing this as
a shell script and submitting as a patch """
class ForceConnector:
	
	def __init__(self, apn):
		self.apn = apn
		self.current_connection()
		self.connection = conic.Connection()
		
	def current_connection(self):
		bus = dbus.SystemBus()
		proxy = bus.get_object('com.nokia.icd', '/com/nokia/icd')
		icd = dbus.Interface(proxy, 'com.nokia.icd')
		(iapid, arg, arg1, arg2, arg3, arg4, arg5) = icd.get_statistics()
		self.previousconn = iapid
		log.info("ForceConnector saved previous connection. ID: %s", iapid)
		
	def connection_cb(self, connection, event, magic):
		#log.info("connection_cb(%s, %s, %x)" % (connection, event, magic))
		pass
		
	""" restore connection to previous """
	def disconnect(self):
		log.info("ForceConnector restoring connection...")
		self.connect(self.previousconn)
	
	""" actually disconnects from the current iap before connecting """
	def connect(self, apn=None):
		global magic
		
		args = "DISCONNECT"
		retcode = subprocess.call(["/opt/fmms/fmms_magic", args])
		log.info("ForceConnector disconnecting from active connection.")

		if apn == None:
			apn = self.apn
	
		# Creates the connection object and attach the handler.
		connection = self.connection
		iaps = connection.get_all_iaps()
		iap = None
		for i in iaps:
			if i.get_name() == apn or i.get_id() == apn:
				iap = i
		
		log.info("ForceConnector trying to connect to: ID: %s Name: %s" % (iap.get_id(), iap.get_name()))
		connection.connect("connection-event", self.connection_cb, magic)
		
		if iap:
			connection.request_connection_by_id(iap.get_id(), conic.CONNECT_FLAG_NONE)
		else:
			connection.request_connection(conic.CONNECT_FLAG_NONE)


""" the ugly-hack autoconnector """
class UglyHackHandler:
	
	def __init__(self, apn, username="", password="", proxy="0", mmsc1="0", mmsc2="0"):
		self.apn = apn
		self.username = username
		self.password = password
		self.proxyip = proxy
		self.mmsc1 = mmsc1
		self.mmsc2 = mmsc2
		self.rx = 0
		self.tx = 0
		log.info("UglyHackHandler UP!\nAPN: %s user: %s pass: %s proxyip: %s mmsc1: %s mmsc2: %s" % (self.apn, self.username, self.password, self.proxyip, self.mmsc1, self.mmsc2))
		self.conn = self.connect()

	def start(self):
		args = "START %s %s %s %s %s %s" % (self.iface, self.ipaddr, self.mmsc1, self.mmsc2, self.dnsip, self.proxyip)
		retcode = subprocess.call(["/opt/fmms/fmms_magic", args])
		log.info("fmms_magic retcode: %s" % retcode)
		
	def connect(self):
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
		(apn, ctype, self.iface, self.ipaddr, connected, self.tx, self.rx) = self.conn.GetStatus()
		args = "STOP %s" % self.iface
		retcode = subprocess.call(["/opt/fmms/fmms_magic", args])
		log.info("disconnecting connection. rx: %s tx: %s" % (self.tx, self.rx))
		self.conn.Disconnect()