#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Sets up the config for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import os

try:
	import gnome.gconf as gconf
except:
	import gconf

CONNMODE_UGLYHACK = 1
CONNMODE_ICDSWITCH = 2
CONNMODE_FORCESWITCH = 3

class fMMS_config:


	def __init__(self):
		self._fmmsdir = "/apps/fmms/"
		self.client = gconf.client_get_default()
		self.client.add_dir(self._fmmsdir, gconf.CLIENT_PRELOAD_NONE)
		if self.get_apn() == None:
			self.set_apn("bogus")
		if self.get_pushdir() == None:
			self.set_pushdir("/home/user/.fmms/push/")
		if self.get_mmsdir() == None:
			self.set_mmsdir("/home/user/.fmms/mms/")
		if self.get_outdir() == None:
			self.set_outdir("/home/user/.fmms/sent/")
		if self.get_imgdir() == None:
			self.set_imgdir("/home/user/.fmms/temp/")
		if self.get_mmsc() == None:
			self.set_mmsc("http://")
		if self.get_phonenumber() == None:
			self.set_phonenumber("0")
		if self.get_img_resize_width() == None:
			self.set_img_resize_width(320)
		if self.get_version() == None:
			self.set_version("Unknown")
		if self.get_connmode() == None:
			self.set_connmode(1)
		if self.get_db_path() == None:
			self.set_db_path("/home/user/.fmms/mms.db")
		# Create dirs, for good measures
		if not os.path.isdir(self.get_pushdir()):
			os.makedirs(self.get_pushdir())
		
		if not os.path.isdir(self.get_mmsdir()):
			os.makedirs(self.get_mmsdir())

		if not os.path.isdir(self.get_outdir()):
			os.makedirs(self.get_outdir())
			
		if not os.path.isdir(self.get_imgdir()):
			os.makedirs(self.get_imgdir())
		
	def read_config(self):
		pass
		
	def set_experimental(self, val):
		if (val == True):
			val = 1
		else:
			val = 0
		self.client.set_int(self._fmmsdir + "exp", int(val))
	
	def get_experimental(self):
		return self.client.get_int(self._fmmsdir + "exp")
	
	def set_connmode(self, val):
		self.client.set_int(self._fmmsdir + "connmode", int(val))
		
	def get_connmode(self):
		return self.client.get_int(self._fmmsdir + "connmode")
	
	def set_db_path(self, path):
		self.client.set_string(self._fmmsdir + "db", path)
	
	def get_db_path(self):
		return self.client.get_string(self._fmmsdir + "db")
	
	def get_version(self):
		return self.client.get_string(self._fmmsdir + "version")
	
	def set_version(self, val):
		self.client.set_string(self._fmmsdir + "version", val)
		
	def set_firstlaunch(self, val):
		self.client.set_int(self._fmmsdir + "firstlaunch", val)
		
	def get_firstlaunch(self):
		return self.client.get_int(self._fmmsdir + "firstlaunch")
	
        def set_img_resize_width(self, width):
        	try:
        		width = int(width)
        	except ValueError:
                	width = 0
                self.client.set_int(self._fmmsdir + "img_resize_width", width)

        def get_img_resize_width(self):
                return self.client.get_int(self._fmmsdir + "img_resize_width") 	
	
	def set_phonenumber(self, number):
		self.client.set_string(self._fmmsdir + "phonenumber", number)
	
	def get_phonenumber(self):
		return self.client.get_string(self._fmmsdir + "phonenumber")
	
	def set_pushdir(self, path):
		self.client.set_string(self._fmmsdir + "pushdir", path)
		
	def get_pushdir(self):
		return self.client.get_string(self._fmmsdir + "pushdir")		
		
	def set_mmsdir(self, path):
		self.client.set_string(self._fmmsdir + "mmsdir", path)

	def get_mmsdir(self):
		return self.client.get_string(self._fmmsdir + "mmsdir")
	
	def set_outdir(self, path):
		self.client.set_string(self._fmmsdir + "outdir", path)
	
	def get_outdir(self):
		return self.client.get_string(self._fmmsdir + "outdir")
		
	def set_imgdir(self, path):
		self.client.set_string(self._fmmsdir + "imgdir", path)

	def get_imgdir(self):
		return self.client.get_string(self._fmmsdir + "imgdir")
		
	""" note this takes the *id* from gconf and not the *display name* """
	def set_apn(self, apn):
		#apn = apn.replace(" ", "@32@")
		#self.client.set_string(self._fmmsdir + "apn_nicename", apn)
		self.client.set_string(self._fmmsdir + "apn", apn)
		
	def get_apn_nicename(self):
		#return self.client.get_string(self._fmmsdir + "apn_nicename")
		apn = self.client.get_string(self._fmmsdir + "apn")
		return self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/name')
	
	def get_apn(self):
		return self.client.get_string(self._fmmsdir + "apn")
		
	def set_mmsc(self, mmsc):
		self.client.set_string(self._fmmsdir + "mmsc", mmsc)
	
	def get_mmsc(self):
		return self.client.get_string(self._fmmsdir + "mmsc")
		
	def get_proxy_from_apn(self):
		apn = self.get_apn()
		proxy = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/proxy_http')
		proxyport = self.client.get_int('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port')
		return proxy, proxyport
		
	def get_apn_from_osso(self):
		apn = self.get_apn()
		apnosso = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_accesspointname')
		return apnosso
	
	def get_gprs_apns(self):
		# get all IAP's
		dirs = self.client.all_dirs('/system/osso/connectivity/IAP')
		apnlist = []
		for subdir in dirs:
			# get all sub entries.. this might be costy?
			all_entries = self.client.all_entries(subdir)
			# this is a big loop as well, possible to make it easier?
			# make this faster
			for entry in all_entries:
				(path, sep, shortname) = entry.key.rpartition('/')
				# this SHOULD always be a int
				if shortname == 'type' and entry.value.type == gconf.VALUE_STRING and entry.value.get_string() == "GPRS":	
					# split it so we can get the id
					#(spath, sep, apnid) = path.rpartition('/')
					apname = self.client.get_string(path + '/name')
					apnlist.append(apname)
		
		return apnlist
	
	""" get the gconf alias for the name, be it the real name or
	an arbitrary string """
	def get_apnid_from_name(self, apnname):
		# get all IAP's
		dirs = self.client.all_dirs('/system/osso/connectivity/IAP')
		
		for subdir in dirs:
			# get all sub entries.. this might be costy?
			all_entries = self.client.all_entries(subdir)
			# this is a big loop as well, possible to make it easier?
			for entry in all_entries:
				(path, sep, shortname) = entry.key.rpartition('/')
				
				# this SHOULD always be a string
				if shortname == 'name':				
					if entry.value.type == gconf.VALUE_STRING:
						_value = entry.value.get_string()
					if _value == apnname:
						# split it so we can get the id
						(spath, sep, apnid) = path.rpartition('/')		
						return apnid		
		
		return None
		
		
if __name__ == '__main__':
	config = fMMS_config()
	config.set_connmode(1)