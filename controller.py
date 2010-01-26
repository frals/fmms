#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Useful functions that shouldn't be in the UI code


And, yes, I know this is not really a controller.

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import os
import array

import dbus
from dbus.mainloop.glib import DBusGMainLoop

import fmms_config as fMMSconf
import dbhandler as DBHandler
from mms.message import MMSMessage
from mms import mms_pdu

#TODO: constants.py?
MSG_DIRECTION_IN = 0
MSG_DIRECTION_OUT = 1
MSG_UNREAD = 0
MSG_READ = 1

class fMMS_controller():
	
	def __init__(self):
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._outdir = self.config.get_outdir()
		self.store = DBHandler.DatabaseHandler()
	
	
	def decode_mms_from_push(self, binarydata):
		decoder = mms_pdu.MMSDecoder()
		wsplist = decoder.decodeCustom(binarydata)

		sndr, url, trans_id = None, None, None
		bus = dbus.SystemBus()
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = dbus.Interface(proxy,dbus_interface='org.freedesktop.Notifications')

		try:
			url = wsplist["Content-Location"]
			print "content-location:", url
			trans_id = wsplist["Transaction-Id"]
			trans_id = str(trans_id)
			print "transid:", trans_id
		except Exception, e:
			print "no content-location/transid in push; aborting...", type(e), e
			interface.SystemNoteInfoprint ("fMMS: Failed to parse SMS PUSH.")
			raise
		try:
			sndr = wsplist["From"]
			print "Sender:", sndr
		except Exception, e:
			print "No sender value defined", type(e), e
			sndr = "Unknown sender"

		self.save_binary_push(binarydata, trans_id)
		return (wsplist, sndr, url, trans_id)
	
	
	def save_binary_push(self, binarydata, transaction):
		data = array.array('B')
		for b in binarydata:
			data.append(b)
		# TODO: move to config?
		if not os.path.isdir(self._pushdir):
			os.makedirs(self._pushdir)
		try:
			fp = open(self._pushdir + transaction, 'wb')
			fp.write(data)
			print "saved binary push", fp
			fp.close()
		except Exception, e:
			print "failed to save binary push:", type(e), e
			raise
	
	def save_push_message(self, data):
		""" Gets the decoded data as a list (preferably from decode_mms_from_push)
		"""
		pushid = self.store.insert_push_message(data)
		return pushid
	
	
	def get_push_list(self, types=None):
		return self.store.get_push_list()
		
	
	def is_fetched_push_by_transid(self, transactionid):
		return self.store.is_mms_downloaded(transactionid)
	
	
	def read_push_as_list(self, transactionid):
		return self.store.get_push_message(transactionid)
	
	
	def save_binary_mms(self, data, transaction):
		dirname = self._mmsdir + transaction
		if not os.path.isdir(dirname):
			os.makedirs(dirname)
		
		fp = open(dirname + "/message", 'wb')
		fp.write(data)
		print "saved binary mms", fp
		fp.close()
		return dirname
		
	def save_binary_outgoing_mms(self, data, transaction):
		transaction = str(transaction)
		dirname = self._outdir + transaction
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		fp = open(dirname + "/message", 'wb')
		fp.write(data)
		print "saved binary mms", fp
		fp.close()
		return dirname
	
	def decode_binary_mms(self, path):
		""" decodes and saves the binary mms"""
		# Decode the specified file
		# This also creates all the parts as files in path
		print "decode_binary_mms running"
		try:
			message = MMSMessage.fromFile(path + "/message")
		except Exception, e:
			print type(e), e
			raise
		print "returning message!"
		return message
	
	
	def is_mms_read(self, transactionid):
		if self.store.is_message_read(transactionid) == True:
			return "Read"
		else:
			return "Unread"
	
	
	def store_mms_message(self, pushid, message):
		mmsid = self.store.insert_mms_message(pushid, message)
		return mmsid
	
	def store_outgoing_mms(self, message):
		mmsid = self.store.insert_mms_message(0, message, DBHandler.MSG_DIRECTION_OUT)
		return mmsid
		
	def store_outgoing_push(self, wsplist):
		pushid = self.store.insert_push_send(wsplist)
		return pushid
		
	def link_push_mms(self, pushid, mmsid):
		self.store.link_push_mms(pushid, mmsid)
	
	def get_direction_mms(self, transid):
		return self.store.get_direction_mms(transid)
	
	def get_mms_from_push(self, transactionid):
		plist = self.store.get_push_message(transactionid)
		trans_id = plist['Transaction-Id']
		pushid = plist['PUSHID']
		url = plist['Content-Location']
		
		from wappushhandler import PushHandler
		p = PushHandler()
		path = p._get_mms_message(url, trans_id)
		print "decoding mms..."
		message = self.cont.decode_binary_mms(path)
		print "storing mms..."
		mmsid = self.cont.store_mms_message(pushid, message)
		
		
	def get_mms_attachments(self, transactionid, allFiles=False):
		return self.store.get_mms_attachments(transactionid, allFiles)
	
	def get_mms_headers(self, transactionid):
		return self.store.get_mms_headers(transactionid)
	
	def delete_mms_message(self, fname):
		fullpath = self._mmsdir + fname
		print fullpath
		if os.path.isdir(fullpath):
			print "starting deletion of", fullpath
			filelist = self.get_mms_attachments(fname, allFiles=True)
			if filelist == None:
				filelist = []
			filelist.append("message")
                        filelist.append("headers")
			for fn in filelist:
				try:
					fullfn = fullpath + "/" + fn
					os.remove(fullfn)
				except:
					print "failed to remove", fullfn
			try:
				print "trying to remove", fullpath
				os.rmdir(fullpath)
			except OSError, e:
				print "failed to remove dir:", type(e), e
				raise
		self.store.delete_mms_message(fname)
		
	def delete_push_message(self, fname):
		fullpath = self._pushdir + fname
		print fullpath
		if os.path.isfile(fullpath):
			print "removing", fullpath
			try:
				os.remove(fullpath)
			except Exception, e:
				raise
		self.store.delete_push_message(fname)
		
	def wipe_message(self, transactionid):
		self.delete_mms_message(transactionid)
		self.delete_push_message(transactionid)
	
	""" DEPRECATED AS OF 0.2.10
	gets a mms from a previously received push """
	""" this function requires the fname to be the fullpath """
	# TODO: dont require fullpath
	"""def get_mms_from_push(self, fname):
		
		plist = self.read_push_as_list(fname)
		try:
			sndr = plist['From']
		except:
			sndr = "Unknown"
		url = plist['Content-Location']
		print url
		trans_id = plist['Transaction-Id']
		print trans_id
		
		from wappushhandler import PushHandler
		push = PushHandler()
		path = push._get_mms_message(url, trans_id)
		Push.decodeMMS(path)
		
		return 0"""
	
	""" Old function relying on files... Deprecated as of 0.2.10
	def is_fetched_push(self, filename):
		this function takes the FILENAME, not the full path
		path = self._mmsdir + filename
		if os.path.isdir(path):
			if os.path.isfile(self._mmsdir + filename + "/message"):
				return True
		else:
		return False"""
	
	
	"""def read_push_as_list(self, fname):
			# reads a saved push message into a dict
			fp = open(fname, 'r')
			pdict = {}
			for line in fp:
				line = line.replace("\n", "")
				lsplit = line.partition(" ")
				pdict[lsplit[0]] = lsplit[2]
			fp.close()
		return pdict"""
	
if __name__ == '__main__':
	c = fMMS_controller()
	pass