#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Sets up the config for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os

import osso

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
		apn = self.get_apn()
		if apn == None:
			apn = self.create_new_apn()
			self.set_apn(apn)
		# if its not our APN we copy settings to ours
		if apn != "z_fMMS-APN":
			settings = self.get_apn_settings()
			advsettings = self.get_advanced_apn_settings()
			apn = self.create_new_apn()
			self.set_apn(apn)
			self.set_apn_settings(settings)
			self.set_advanced_apn_settings(advsettings)
			self.set_mmsc(self.get_old_mmsc())
		if self.get_pushdir() == None:
			self.set_pushdir("/home/user/.fmms/push/")
		if self.get_mmsdir() == None:
			self.set_mmsdir("/home/user/.fmms/mms/")
		if self.get_outdir() == None:
			self.set_outdir("/home/user/.fmms/sent/")
		if self.get_imgdir() == None:
			self.set_imgdir("/home/user/.fmms/temp/")
		if self.get_mmsc() == None:
			self.set_mmsc("")
		if self.get_phonenumber() == None:
			self.set_phonenumber("0")
		if self.get_img_resize_width() == None:
			self.set_img_resize_width(240)
		if self.get_version() == None:
			self.set_version("Unknown")
		if self.get_connmode() == None:
			self.set_connmode(CONNMODE_ICDSWITCH)
		if self.get_db_path() == None:
			self.set_db_path("/home/user/.fmms/mms.db")
		if not self.get_useragent():
			self.set_useragent("NokiaN95/11.0.026; Series60/3.1 Profile/MIDP-2.0 Configuration/CLDC-1.1")
		# Create dirs, for good measures
		if not os.path.isdir(self.get_pushdir()):
			os.makedirs(self.get_pushdir())
		
		if not os.path.isdir(self.get_mmsdir()):
			os.makedirs(self.get_mmsdir())

		if not os.path.isdir(self.get_outdir()):
			os.makedirs(self.get_outdir())
			
		if not os.path.isdir(self.get_imgdir()):
			os.makedirs(self.get_imgdir())
		
		if self.get_firstlaunch() == 0:
			self.set_firstlaunch(1)
			self.set_img_resize_width(240)
			self.set_connmode(CONNMODE_ICDSWITCH)

	def get_old_mmsc(self):
		return self.client.get_string(self._fmmsdir + 'mmsc')
	
	def set_connmode(self, val):
		apn = self.get_apn()
		self.client.set_int(self._fmmsdir + "connmode", int(val))
		if val == CONNMODE_UGLYHACK:
			self.mask_apn_from_icd(apn)
		else:
			self.unmask_apn_from_icd(apn)
		
	def get_connmode(self):
		return self.client.get_int(self._fmmsdir + "connmode")
	
	def set_db_path(self, path):
		self.client.set_string(self._fmmsdir + "db", path)
	
	def get_db_path(self):
		return self.client.get_string(self._fmmsdir + "db")

	def get_useragent(self):
		return self.client.get_string(self._fmmsdir + "useragent")
	
	def set_useragent(self, val):
		self.client.set_string(self._fmmsdir + "useragent", val)
	
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
		apn = self.client.get_string(self._fmmsdir + "apn")
		return apn

	def set_mmsc(self, mmsc):
		apn = self.get_apn()
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/mmsc', mmsc)
	
	def get_mmsc(self):
		apn = self.get_apn()
		mmsc = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/mmsc')
		if not mmsc:
			mmsc = ""
		return mmsc

	def get_proxy_from_apn(self):
		apn = self.get_apn()
		proxy = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/proxy_http')
		proxyport = self.client.get_int('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port')
		return proxy, proxyport
		
	def get_apn_from_osso(self):
		apn = self.get_apn()
		apnosso = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_accesspointname')
		return apnosso
	
	def get_user_for_apn(self):
		apn = self.get_apn()
		user = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_username')
		if user:
			return user
		else:
			return ""

	def get_passwd_for_apn(self):
		apn = self.get_apn()
		passwd = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_password')
		if passwd:
			return passwd
		else:
			return ""
			
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
	
	def set_apn_settings(self, settings):
		apn = self.get_apn()
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/gprs_accesspointname', settings['apn'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/gprs_username', settings['user'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/gprs_password', settings['pass'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/proxy_http', settings['proxy'])
		self.client.set_int('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port', int(settings['proxyport']))
		self.set_mmsc(settings['mmsc'])
		
	def get_apn_settings(self):
		apn = self.get_apn()
		settings = {}
		settings['apn'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_accesspointname')
		settings['user'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_username')
		settings['pass'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_password')
		settings['proxy'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/proxy_http')
		settings['proxyport'] = self.client.get_int('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port')
		settings['mmsc'] = self.get_mmsc()
		
		return settings
		
	def set_advanced_apn_settings(self, settings):
		apn = self.get_apn()
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns1', settings['pdns'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns2', settings['sdns'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_address', settings['ip'])
	
	def get_advanced_apn_settings(self):
		apn = self.get_apn()
		settings = {}
		settings['pdns'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns1')
		settings['sdns'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns2')
		settings['ip'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_address')
		return settings
	
	def create_new_apn(self):
		""" Create a new APN for MMS usage. """
		# Name it z_fMMS as auto-connect *might* 
		# search gconf keys in alphabetical order...
		apn = "z_fMMS-APN"
		self.client.add_dir('/system/osso/connectivity/IAP/' + apn, gconf.CLIENT_PRELOAD_NONE)
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/type", "GPRS")
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/name", "MMS")
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/ipv4_type", "AUTO")
		self.client.set_int('/system/osso/connectivity/IAP/' + apn + "/user_added", 2)
		self.unmask_apn_from_icd(apn)
		return apn
		
	def get_sim_imsi(self):
		osso_c = osso.Context('fMMSconfig', '1.0', False)
		rpc = osso.Rpc(osso_c)
		imsi = rpc.rpc_run('com.nokia.phone.SIM', '/com/nokia/phone/SIM', 'Phone.Sim', 'get_imsi', (), True, True)
		return imsi
		
	def mask_apn_from_icd(self, apn):
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/sim_imsi", "masked")
		
	def unmask_apn_from_icd(self, apn):
		simimsi = self.get_sim_imsi()
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/sim_imsi", simimsi)
		
		
if __name__ == '__main__':
	config = fMMS_config()