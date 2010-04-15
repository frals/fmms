#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Useful functions that shouldn't be in the UI code

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import logging
import logging.config
import StringIO

logging.config.fileConfig('/opt/fmms/logger.conf')
log = logging.getLogger('fmms.%s' % __name__)

import os
import array
import re
import time
import urlparse

import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gtk

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
	
	def get_primary_font(self):
		return self.get_font_desc('SystemFont')
		
	def get_secondary_font(self):
		return self.get_font_desc('SmallSystemFont')
		
	def get_active_color(self):
		return self.get_color('ActiveTextColor')
	
	def get_primary_color(self):
		return self.get_color('ButtonTextColor')
		
	def get_secondary_color(self):
		return self.get_color('SecondaryTextColor')
	
	# credits to gpodder for this
	def get_font_desc(self, logicalfontname):
		settings = gtk.settings_get_default()
		font_style = gtk.rc_get_style_by_paths(settings, logicalfontname, \
							None, None)
		font_desc = font_style.font_desc
		return font_desc
	
	# credits to gpodder for this
	def get_color(self, logicalcolorname):
		settings = gtk.settings_get_default()
		color_style = gtk.rc_get_style_by_paths(settings, 'GtkButton', \
							'osso-logical-colors', gtk.Button)
		return color_style.lookup_color(logicalcolorname)
	
	
	def get_host_from_url(self, url):
		if not url.startswith("http://"):
			url = "http://%s" % url

		ret = urlparse.urlparse(url)
		ret = ret[1].split(":")[0]
		
		return ret
	
	""" from http://snippets.dzone.com/posts/show/655 """
	def image2pixbuf(self, im):
		file1 = StringIO.StringIO()
		try:
			im.save(file1, "ppm")
			contents = file1.getvalue()
			file1.close()
			loader = gtk.gdk.PixbufLoader("pnm")
			loader.write(contents, len(contents))
			pixbuf = loader.get_pixbuf()
			loader.close()
			return pixbuf
		except IOError, e:
			log.exception("Failed to convert")
			im.save(file1, "gif")
			contents = file1.getvalue()
			file1.close()
			loader = gtk.gdk.PixbufLoader()
			loader.write(contents, len(contents))
			pixbuf = loader.get_pixbuf()
			loader.close()
			return pixbuf
			
		
	
	
	def convert_timeformat(self, intime, format, hideToday=False):
		mtime = intime
		try:
			mtime = time.strptime(mtime)
		except ValueError, e:
			#log.info("timeconversion stage1 failed: %s %s", type(e), e)
			try:
				mtime = time.strptime(mtime, "%Y-%m-%d %H:%M:%S")
			except ValueError, e:
				#log.info("timeconversion stage2 failed: %s %s", type(e), e)
				pass
		except Exception, e:
			#log.exception("Could not convert timestamp: %s %s", type(e), e)
			pass
		
		# TODO: check if hideToday == true
		# TODO: remove date if date == today
		try:
			mtime = time.strftime("%Y-%m-%d | %H:%M", mtime)
		except:
			log.info("stftime failed: %s %s", type(e), e)
			mtime = intime
		
		return mtime
	
	
	def decode_mms_from_push(self, binarydata):
		decoder = mms_pdu.MMSDecoder()
		wsplist = decoder.decodeCustom(binarydata)

		sndr, url, trans_id = None, None, None
		bus = dbus.SystemBus()
		proxy = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		interface = dbus.Interface(proxy,dbus_interface='org.freedesktop.Notifications')

		try:
			url = wsplist["Content-Location"]
			log.info("content-location: %s", url)
			trans_id = wsplist["Transaction-Id"]
			trans_id = str(trans_id)
			log.info("transid: %s", trans_id)
		except Exception, e:
			log.exception("no content-location/transid in push; aborting: %s %s", type(e), e)
			interface.SystemNoteInfoprint ("fMMS: Failed to parse SMS PUSH.")
			raise
		try:
			sndr = wsplist["From"]
			log.info("Sender: %s", sndr)
		except Exception, e:
			log.exception("No sender value defined: %s %s", type(e), e)
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
			log.info("saved binary push: %s", fp)
			fp.close()
		except Exception, e:
			log.exception("failed to save binary push: %s %s", type(e), e)
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
		log.info("saved binary mms %s", fp)
		fp.close()
		return dirname
		
	def save_binary_outgoing_mms(self, data, transaction):
		transaction = str(transaction)
		dirname = self._outdir + transaction
		if not os.path.isdir(dirname):
			os.makedirs(dirname)

		fp = open(dirname + "/message", 'wb')
		fp.write(data)
		log.info("saved binary mms %s", fp)
		fp.close()
		return dirname
	
	def decode_binary_mms(self, path):
		""" decodes and saves the binary mms"""
		# Decode the specified file
		# This also creates all the parts as files in path
		log.info("decode_binary_mms running")
		try:
			message = MMSMessage.fromFile(path + "/message")
		except Exception, e:
			log.exception("decode binary failed:", type(e), e)
			raise
		log.info("returning message!")
		return message
	
	
	def is_mms_read(self, transactionid):
		return self.store.is_message_read(transactionid)

	
	def mark_mms_read(self, transactionid):
		self.store.mark_message_read(transactionid)
	
	
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
		
	def get_replyuri_from_transid(self, transid):
		uri = self.store.get_replyuri_from_transid(transid)
		try:
			uri = uri.replace("/TYPE=PLMN", "")
			return uri
		except Exception, e:
			log.exception("failed to get replyuri, got: %s (%s)", uri, uri.__class__)
			return ""
	
	def get_mms_from_push(self, transactionid):
		plist = self.store.get_push_message(transactionid)
		trans_id = plist['Transaction-Id']
		pushid = plist['PUSHID']
		url = plist['Content-Location']
		
		from wappushhandler import PushHandler
		p = PushHandler()
		path = p._get_mms_message(url, trans_id)
		log.info("decoding mms... %s", trans_id)
		message = self.decode_binary_mms(path)
		log.info("storing mms...%s", trans_id)
		mmsid = self.store_mms_message(pushid, message)
		
		
	def get_mms_attachments(self, transactionid, allFiles=False):
		return self.store.get_mms_attachments(transactionid, allFiles)
	
	def get_mms_headers(self, transactionid):
		return self.store.get_mms_headers(transactionid)
	
	def delete_mms_message(self, fname):
		fullpath = self.store.get_filepath_for_mms_transid(fname)
		if fullpath:
			fullpath = fullpath.replace("/message", "")
		else:
			fullpath = self._mmsdir + fname

		log.info("fullpath: %s", fullpath)
		if os.path.isdir(fullpath):
			log.info("starting deletion of %s", fullpath)
			filelist = self.get_mms_attachments(fname, allFiles=True)
			if filelist == None:
				filelist = []
			filelist.append("message")
                        filelist.append("headers")
                        log.info("removing: %s", filelist)
			for fn in filelist:
				try:
					fullfn = fullpath + "/" + fn
					os.remove(fullfn)
				except:
					log.info("failed to remove: %s", fullfn)
			try:
				log.info("trying to remove: %s", fullpath)
				os.rmdir(fullpath)
			except OSError, e:
				log.exception("failed to remove: %s %s", type(e), e)
				raise
		self.store.delete_mms_message(fname)
		
	def delete_push_message(self, fname):
		fullpath = self.store.get_filepath_for_push_transid(fname)
		if not fullpath:
			fullpath = self._pushdir + fname

		log.info("fullpath: %s", fullpath)
		if os.path.isfile(fullpath):
			log.info("removing: %s", fullpath)
			try:
				os.remove(fullpath)
			except Exception, e:
				log.exception("%s %s", type(e), e)
				raise
		self.store.delete_push_message(fname)
		
	def wipe_message(self, transactionid):
		self.delete_mms_message(transactionid)
		self.delete_push_message(transactionid)
	

	def validate_phonenumber_email(self, nr):
		nr = str(nr)
		nr = nr.replace("+", "")
		nr = nr.replace(" ", "")
		if re.search(r"(\D)+", nr) == None or "@" in nr:
			return True
		else:
		 	return False
		
		
	
if __name__ == '__main__':
	c = fMMS_controller()
	pass