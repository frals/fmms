#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Class for handling wap push messages and creating MMS messages

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import sys
import os
import dbus
import urllib2
import urllib
import httplib
import conic
import time
import socket
import array

from dbus.mainloop.glib import DBusGMainLoop

from mms import message
from mms.message import MMSMessage
from mms import mms_pdu
import fmms_config as fMMSconf
import controller as fMMSController

magic = 0xacdcacdc

_DBG = True

class PushHandler:
	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		# TODO: get all this from controller instead of config
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._apn = self.config.get_apn()
		self._apn_nicename = self.config.get_apn_nicename()
		self._incoming = '/home/user/.fmms/temp/LAST_INCOMING'
		
		if not os.path.isdir(self._mmsdir):
			print "creating dir", self._mmsdir
			os.makedirs(self._mmsdir)
		if not os.path.isdir(self._pushdir):
			print "creating dir", self._pushdir
			os.makedirs(self._pushdir)

	""" handle incoming push over sms """
	def _incoming_sms_push(self, source, src_port, dst_port, wsp_header, wsp_payload):
		dbus_loop = DBusGMainLoop()
		args = (source, src_port, dst_port, wsp_header, wsp_payload)
		
		# TODO: dont hardcode
		if not os.path.isdir('/home/user/.fmms/temp'):
			print "creating dir /home/user/.fmms/temp"
			os.makedirs("/home/user/.fmms/temp")
		
		f = open(self._incoming, 'w')
		for arg in args:
		    f.write(str(arg))
		    f.write('\n')
		f.close()

		if(_DBG):
			print "SRC: ", source, ":", src_port
			print "DST: ", dst_port
			#print "WSPHEADER: ", wsp_header
			#print "WSPPAYLOAD: ", wsp_payload

		binarydata = []
		# throw away the wsp_header!
		#for d in wsp_header:
		#	data.append(int(d))
		
		for d in wsp_payload:
			binarydata.append(int(d))

		print "decoding..."
		
		
		(data, sndr, url, trans_id) = self.cont.decode_mms_from_push(binarydata)
		
		print "saving..."
		# Controller should save it
		pushid = self.cont.save_push_message(data)
		print "notifying push..."
		# Send a notify we got the SMS Push and parsed it A_OKEY!
		self.notify_mms(dbus_loop, sndr, "SMS Push for MMS received")
		print "fetching mms..."
		path = self._get_mms_message(url, trans_id)
		print "decoding mms... path:", path
		message = self.cont.decode_binary_mms(path)
		print "storing mms..."
		mmsid = self.cont.store_mms_message(pushid, message)
		print "notifying mms..."
		self.notify_mms(dbus_loop, sndr, "New MMS", trans_id);
		return 0


	""" handle incoming ip push """
	# TODO: implement this
	def _incoming_ip_push(self, src_ip, dst_ip, src_port, dst_port, wsp_header, wsp_payload):
		if(_DBG):
			print "SRC: " + src_ip + ":" + src_port + "\n"
			print "DST: " + dst_ip + ":" + dst_port + "\n"
			print "WSPHEADER: " + wsp_header + "\n"
			print "WSPPAYLOAD: " + wsp_payload + "\n"
			print


	""" notifies the user with a org.freedesktop.Notifications.Notify, really fancy """
	def notify_mms(self, dbus_loop, sender, message, path=None):
		bus = dbus.SystemBus()
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = dbus.Interface(proxy,dbus_interface='org.freedesktop.Notifications')
		choices = ['default', 'cancel']
		if path == None:
			interface.Notify('MMS', 0, '', message, sender, choices, {"category": "sms-message", "dialog-type": 4, "led-pattern": "PatternCommunicationEmail", "dbus-callback-default": "se.frals.fmms /se/frals/fmms se.frals.fmms open_gui"}, -1)
		else:
			# TODO: callback should open fMMS gui
			interface.Notify("MMS", 0, '', message, sender, choices, {"category": "email-message", "dialog-type": 4, "led-pattern": "PatternCommunicationEmail", "dbus-callback-default": "se.frals.fmms /se/frals/fmms se.frals.fmms open_mms string:\"" + path + "\""}, -1)


	""" get the mms message from content-location """
	""" thanks benaranguren on talk.maemo.org for patch including x-wap-profile header """
	def _get_mms_message(self, location, transaction):
		print "getting file: ", location
		try:
			# TODO: remove hardcoded sleep
			con = ConnectToAPN(self._apn_nicename)
			#time.sleep(6)
			con.connect()
			
			try:
				notifyresp = self._send_notify_resp(transaction)
				print "notifyresp sent"
			except:
				print "notify sending failed..."
			
			# TODO: configurable time-out?
			timeout = 60
			socket.setdefaulttimeout(timeout)
			(proxyurl, proxyport) = self.config.get_proxy_from_apn()
			
			if proxyurl == "" or proxyurl == None:
				print "connecting without proxy"
			else:
				proxyfull = str(proxyurl) + ":" + str(proxyport)
				print "connecting with proxy", proxyfull	
				proxy = urllib2.ProxyHandler({"http": proxyfull})
				opener = urllib2.build_opener(proxy)
				urllib2.install_opener(opener)
				
			#headers = {'x-wap-profile': 'http://mms.frals.se/n900.rdf'}
			#User-Agent: NokiaN95/11.0.026; Series60/3.1 Profile/MIDP-2.0 Configuration/CLDC-1.1 
			headers = {'User-Agent' : 'NokiaN95/11.0.026; Series60/3.1 Profile/MIDP-2.0 Configuration/CLDC-1.1', 'x-wap-profile' : 'http://mms.frals.se/n900.rdf'}
			req = urllib2.Request(location, headers=headers)
			mmsdata = urllib2.urlopen(req)
			try:
				print mmsdata.info()
			except:
				pass
			
			mmsdataall = mmsdata.read()
			dirname = self.cont.save_binary_mms(mmsdataall, transaction)
			
			if(_DBG):
				print "fetched ", location, " and wrote to file"
				
			# send acknowledge we got it ok
			try:
				ack = self._send_acknowledge(transaction)
				print "ack sent"
			except:
				print "sending ack failed"
			
			con.disconnect()			
			
		except Exception, e:
			print e, e.args
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
		
		print "setting up notify sender"
		sender = MMSSender(customMMS=True)
		print "sending notify..."
		out = sender.sendMMS(mms)
		print "m-notifyresp-ind:", out
		return out
	
	
	def _send_acknowledge(self, transid):
		mms = MMSMessage(True)
		mms.headers['Message-Type'] = "m-acknowledge-ind"
		mms.headers['Transaction-Id'] = transid
		mms.headers['MMS-Version'] = "1.3"
		
		print "setting up ack sender"
		ack = MMSSender(customMMS=True)
		print "sending ack..."
		out = ack.sendMMS(mms)
		print "m-acknowledge-ind:", out
		return out

       
class ConnectToAPN:
	def __init__(self, apn):
	    self._apn = apn
	    self.connection = conic.Connection()
	    
	def connection_cb(self, connection, event, magic):
	    print "connection_cb(%s, %s, %x)" % (connection, event, magic)

	
	def disconnect(self):
		connection = self.connection
		connection.disconnect_by_id(self._apn)
	
	def connect(self):
		global magic

		# Creates the connection object and attach the handler.
		connection = self.connection
		iaps = connection.get_all_iaps()
		iap = None
		for i in iaps:
			if i.get_name() == self._apn:
		  		iap = i
		
		connection.disconnect()
		connection.connect("connection-event", self.connection_cb, magic)

		# The request_connection method should be called to initialize
		# some fields of the instance
		if not iap:
			assert(connection.request_connection(conic.CONNECT_FLAG_NONE))
		else:
		#print "Getting by iap", iap.get_id()
			assert(connection.request_connection_by_id(iap.get_id(), conic.CONNECT_FLAG_NONE))
			return False
    	    
""" class for sending an mms """    	    
class MMSSender:
	def __init__(self, number=None, subject=None, message=None, attachment=None, sender=None, customMMS=None):
		print "GOT SENDER:", sender
		print "customMMS:", customMMS
		self.customMMS = customMMS
		self.config = fMMSconf.fMMS_config()
		if customMMS == None:
			self.number = number
			self.subject = subject
			self.message = message
			self.attachment = attachment
			self._mms = None
			self._sender = sender
			self.createMMS()
	    
	def createMMS(self):
		slide = message.MMSMessagePage()
		if self.attachment != None:
			slide.addImage(self.attachment)
		slide.addText(self.message)

		self._mms = message.MMSMessage()
		self._mms.headers['Subject'] = self.subject
		self._mms.headers['To'] = str(self.number) + '/TYPE=PLMN'
		self._mms.headers['From'] = str(self._sender) + '/TYPE=PLMN'
		self._mms.addPage(slide)
	
	def sendMMS(self, customData=None):
		mmsid = None
		if customData != None:
			print "using custom mms"
			self._mms = customData
	
		mmsc = self.config.get_mmsc()
		
		(proxyurl, proxyport) = self.config.get_proxy_from_apn()
		mms = self._mms.encode()
		
		headers = {'Content-Type':'application/vnd.wap.mms-message', 'User-Agent' : 'NokiaN95/11.0.026; Series60/3.1 Profile/MIDP-2.0 Configuration/CLDC-1.1', 'x-wap-profile' : 'http://mms.frals.se/n900.rdf'}
		#headers = {'Content-Type':'application/vnd.wap.mms-message'}
		if proxyurl == "" or proxyurl == None:
			print "connecting without proxy"
			mmsc = mmsc.lower()
			mmsc = mmsc.replace("http://", "")
			mmsc = mmsc.rstrip('/')
			mmsc = mmsc.partition('/')
			mmschost = mmsc[0]
			path = "/" + str(mmsc[2])
			print "mmschost:", mmschost, "path:", path, "pathlen:", len(path)
			conn = httplib.HTTPConnection(mmschost)
			conn.request('POST', path , mms, headers)
		else:
			print "connecting via proxy " + proxyurl + ":" + str(proxyport)
			print "mmschost:", mmsc
			conn = httplib.HTTPConnection(proxyurl + ":" + str(proxyport))
			conn.request('POST', mmsc, mms, headers)

		if customData == None:			
			cont = fMMSController.fMMS_controller()
			path = cont.save_binary_outgoing_mms(mms, self._mms.transactionID)
			message = cont.decode_binary_mms(path)
			mmsid = cont.store_outgoing_mms(message)	
			
		res = conn.getresponse()
		print "MMSC STATUS:", res.status, res.reason
		out = res.read()
		try:
			decoder = mms_pdu.MMSDecoder()
			data = array.array('B')
			for b in out:
				data.append(ord(b))
			outparsed = decoder.decodeResponseHeader(data)
			
			if mmsid != None:
				pushid = cont.store_outgoing_push(outparsed)
				cont.link_push_mms(pushid, mmsid)
				
		except Exception, e:
			print type(e), e
			outparsed = out
			
		print "MMSC RESPONDED:", outparsed
		return res.status, res.reason, outparsed