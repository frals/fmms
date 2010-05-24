#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Class for handling wap push messages and creating MMS messages

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os
import sys
import urllib2
import httplib
import time
import socket
import array
import subprocess

import dbus
import pynotify

from mms import message
from mms.message import MMSMessage
from mms import mms_pdu
import fmms_config as fMMSconf
import controller as fMMSController
import contacts as ContactH
import connectors

import logging
log = logging.getLogger('fmms.%s' % __name__)


class PushHandler:
	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._apn = self.config.get_apn()
		self._apn_nicename = self.config.get_apn_nicename()
		self._incoming = self.config.get_imgdir() + "/LAST_INCOMING"

	def _incoming_sms_push(self, source, src_port, dst_port, wsp_header, wsp_payload):
		""" handle incoming push over sms """
		log.info("Incoming SMS Push!")
		args = (source, src_port, dst_port, wsp_header, wsp_payload)
		
		if not os.path.isdir(self.config.get_imgdir()):
			os.makedirs(self.config.get_imgdir())
		
		f = open(self._incoming, 'w')
		for arg in args:
		    f.write(str(arg))
		    f.write('\n')
		f.close()

		log.info("SRC: %s:%s", source, src_port)
		log.info("DST: %s", dst_port)

		binarydata = []
		# throw away the wsp_header!
		#for d in wsp_header:
		#	data.append(int(d))
		
		for d in wsp_payload:
			binarydata.append(int(d))

		log.info("decoding...")
		
		(data, sndr, url, trans_id) = self.cont.decode_mms_from_push(binarydata)
		
		
		ch = ContactH.ContactHandler()
		sndr = ch.get_displayname_from_number(sndr)
		
		log.info("saving...")
		# Controller should save it
		pushid = self.cont.save_push_message(data)
		try:
			log.info("fetching mms...")
			path = self._get_mms_message(url, trans_id)
		except:
			log.info("failed to fetch - notifying push...")
			# Send a notify we got the SMS Push and parsed it A_OKEY!
			self.notify_mms(sndr, "SMS Push for MMS received")
			log.info("notified...")
			raise
		log.info("decoding mms... path: %s", path)
		message = self.cont.decode_binary_mms(path)
		log.info("storing mms...")
		self.cont.store_mms_message(pushid, message, transactionId=trans_id)
		log.info("notifying mms...")
		self.notify_mms(sndr, "New MMS", trans_id)
		log.info("done, returning!")
		return 0

	# TODO: implement this
	def _incoming_ip_push(self, src_ip, dst_ip, src_port, dst_port, wsp_header, wsp_payload):
		""" handle incoming ip push """
		log.info("SRC: %s:%s", src_ip, src_port)
		log.info("DST: %s:%s", dst_ip, dst_port)

	def notify_mms(self, sender, msg, path=None):
		""" notifies the user with a org.freedesktop.Notifications.Notify, really fancy """
		pynotify.init("fMMS")
		note = pynotify.Notification(sender, msg, "fmms")
		note.set_urgency(pynotify.URGENCY_CRITICAL)
		note.set_hint("led-pattern", "PatternCommunicationEmail")
		if path:
			note.set_hint("dbus-callback-default", "se.frals.fmms /se/frals/fmms se.frals.fmms open_mms string:\"" + path + "\"")
		else:
			note.set_hint("dbus-callback-default", "se.frals.fmms /se/frals/fmms se.frals.fmms open_gui")
		# we have to fake being an email for vibra/sound... oh well!
		bus = dbus.SessionBus()
		proxy = bus.get_object('com.nokia.HildonSVNotificationDaemon', '/com/nokia/HildonSVNotificationDaemon')
		interface = dbus.Interface(proxy,dbus_interface='com.nokia.HildonSVNotificationDaemon')
		interface.PlayEvent({'time': 0, 'category': 'email-message'}, "fmms")
		note.show()

	def _get_mms_message(self, location, transaction):
		# this method should be a critical section
		connector = connectors.MasterConnector()
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
			self._send_acknowledge(transaction)
			log.info("ack sent")
		except:
			log.exception("sending ack failed")
		
		connector.disconnect()
		
		return dirname
		
	def __get_mms_message(self, location, transaction):
		""" get the mms message from content-location """
		# thanks benaranguren on talk.maemo.org for patch including x-wap-profile header
		log.info("getting file: %s", location)
		try:
			(proxyurl, proxyport) = self.config.get_proxy_from_apn()
			
			try:
				socket.setdefaulttimeout(20)
				notifyresp = self._send_notify_resp(transaction)
				log.info("notifyresp sent")
			except:
				log.exception("notify sending failed")
			
			# TODO: configurable time-out?
			timeout = 30
			socket.setdefaulttimeout(timeout)
			
			if proxyurl == "" or proxyurl == None:
				log.info("connecting without proxy")
			else:
				proxyfull = "%s:%s" % (str(proxyurl), str(proxyport))
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
			interface = dbus.Interface(proxy, dbus_interface='org.freedesktop.Notifications')
			interface.SystemNoteInfoprint ("Failed to download MMS message.")
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

    	    
class MMSSender:
	""" class for sending an mms """
	
	def __init__(self, number=None, subject=None, msg=None, attachment=None, sender=None, customMMS=None, setupConn=False):
		self.customMMS = customMMS
		self.config = fMMSconf.fMMS_config()
		self.cont = fMMSController.fMMS_controller()
		self.setupConn = setupConn
		if customMMS == None:
			self.number = number
			self.subject = subject
			self.message = msg
			self.attachment = attachment
			self._mms = None
			self._sender = sender
			self.createMMS()
			if self.setupConn == True:
				self.connector = connectors.MasterConnector()
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
		if self._sender == '0':
			self._mms.headers['From'] = ''
		else:
			self._mms.headers['From'] = str(self._sender) + '/TYPE=PLMN'
		
		self._mms.addPage(slide)
	
	def sendMMS(self, customData=None):
		try:
			(status, reason, outparsed, parsed) = self._sendMMS(customData)
		except:
			log.exception("Failed to send message.")
			raise
		finally:
			if self.setupConn == True:
				try:
					self.connector.disconnect()
				except:
					log.exception("Failed to close connection.")
		
		return status, reason, outparsed, parsed
	
	def _sendMMS(self, customData=None):
		mmsid = None
		if customData != None:
			log.info("using custom mms")
			self._mms = customData
	
		mmsc = self.config.get_mmsc()
		
		(proxyurl, proxyport) = self.config.get_proxy_from_apn()
		mms = self._mms.encode()
		
		socket.setdefaulttimeout(120)
		
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
			
			if mmsid and "Response-Status" in outparsed:
				if outparsed['Response-Status'] == "Ok":
					pushid = cont.store_outgoing_push(outparsed)
					cont.link_push_mms(pushid, mmsid)
				
		except Exception, e:
			print type(e), e
			outparsed = out
			
		log.info("MMSC RESPONDED: %s", outparsed)
		
		return res.status, res.reason, outparsed, parsed


if __name__ == '__main__':
	source = sys.argv[1]
	srcport = sys.argv[2]
	dstport = sys.argv[3]
	header = sys.argv[4]
	payload = sys.argv[5]
	push = PushHandler()
	print source, srcport, dstport, header, payload
	try:
		push._incoming_sms_push(source, srcport, dstport, eval(header), eval(payload))
	except:
		pass
