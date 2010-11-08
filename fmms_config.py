#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Sets up the config for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os
import logging
log = logging.getLogger('fmms.%s' % __name__)

import osso

import gconf

CONNMODE_UGLYHACK = 1
CONNMODE_ICDSWITCH = 2
CONNMODE_FORCESWITCH = 3
CONNMODE_NULL = 10

class fMMS_config:

	def __init__(self):
		self._fmmsdir = "/apps/fmms/"
		self.client = gconf.client_get_default()
		# checking if the dir exists takes longer than just creating it...
		self.client.add_dir(self._fmmsdir, gconf.CLIENT_PRELOAD_NONE)
		apn = self.get_apn()
		if apn == None:
			apn = self.create_new_apn()
			self.set_apn(apn)
		pushdir = self.get_pushdir()
		if pushdir == None:
			pushdir = "/home/user/.fmms/push/"
			self.set_pushdir(pushdir)
		mmsdir = self.get_mmsdir()
		if mmsdir == None:
			mmsdir = "/home/user/.fmms/mms/"
			self.set_mmsdir(mmsdir)
		outdir = self.get_outdir()
		if outdir == None:
			outdir = "/home/user/.fmms/sent/"
			self.set_outdir(outdir)
		imgdir = self.get_imgdir()
		if imgdir == None:
			imgdir = "/home/user/.fmms/temp/"
			self.set_imgdir(imgdir)
		lockfile = self.get_lockfile()
		if lockfile == None:
			lockfile = "/var/lock/fmms_dl.lock"
			self.set_lockfile(lockfile)
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
		if not os.path.isdir(pushdir):
			os.makedirs(pushdir)
		
		if not os.path.isdir(mmsdir):
			os.makedirs(mmsdir)

		if not os.path.isdir(outdir):
			os.makedirs(outdir)
			
		if not os.path.isdir(imgdir):
			os.makedirs(imgdir)
		
		if self.get_firstlaunch() == 0:
			self.set_firstlaunch(1)
			self.set_img_resize_width(240)
			self.set_connmode(CONNMODE_ICDSWITCH)

	def get_old_mmsc(self):
		return self.client.get_string(self._fmmsdir + 'mmsc')
	
	def set_connmode(self, val):
		apn = self.get_apn()
		self.client.set_int(self._fmmsdir + "connmode", int(val))
		if val == CONNMODE_UGLYHACK or val == CONNMODE_NULL:
			self.mask_apn_from_icd(apn)
		else:
			self.unmask_apn_from_icd(apn)
			self.switcharoo()
		
	def get_connmode(self):
		return self.client.get_int(self._fmmsdir + "connmode")
		
	def get_last_ui_dir(self):
		return self.client.get_string(self._fmmsdir + "lastuidir")
		
	def set_last_ui_dir(self, path):
		self.client.set_string(self._fmmsdir + "lastuidir", path)
	
	def set_db_path(self, path):
		self.client.set_string(self._fmmsdir + "db", path)
	
	def get_db_path(self):
		return self.client.get_string(self._fmmsdir + "db")

	def set_lockfile(self, path):
		self.client.set_string(self._fmmsdir + "lockfile", path)
	
	def get_lockfile(self):
		return self.client.get_string(self._fmmsdir + "lockfile")

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
		if self.get_apn():
			self.client.unset('/system/osso/connectivity/IAP/' + self.get_apn() + '/fmms')
		self.client.set_string(self._fmmsdir + "apn", apn)
		self.client.set_int('/system/osso/connectivity/IAP/' + apn + '/fmms', 1)
		
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
	
	def set_apn_settings(self, settings, apn=None):
		if not apn:
			apn = self.get_apn()
		if not settings:
			settings = {}
			settings['apn'] = ""
			settings['user'] = ""
			settings['pass'] = ""
			settings['proxy'] = ""
			settings['proxyport'] = "0"
			settings['mmsc'] = ""
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/gprs_accesspointname', settings['apn'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/gprs_username', settings['user'])
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/gprs_password', settings['pass'])
		
		if settings.get('proxy', "") == "" or not settings.get('proxy'):
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/proxytype', "NONE")
			self.client.unset('/system/osso/connectivity/IAP/' + apn + '/proxy_http')
			self.client.unset('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port')
		else:
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/proxytype', "MANUAL")
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/proxy_http', settings['proxy'])
			if settings.get('proxyport', "") == "":
				settings['proxyport'] = 80
			self.client.set_int('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port', int(settings['proxyport']))
		
		if settings.get('name'):
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/name', settings['name'])
		
		self.set_mmsc(settings['mmsc'])
		
	def get_apn_settings(self, apn=None):
		if not apn:
			apn = self.get_apn()
		settings = {}
		settings['apn'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_accesspointname')
		settings['user'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_username')
		settings['pass'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/gprs_password')
		proxytype = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/proxytype')
		if proxytype != "NONE":
			settings['proxy'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/proxy_http')
			settings['proxyport'] = self.client.get_int('/system/osso/connectivity/IAP/' + apn + '/proxy_http_port')
		settings['mmsc'] = self.get_mmsc()
		settings['name'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/name')
		return settings
		
	def set_advanced_apn_settings(self, settings, apn=None):
		if not apn:
			apn = self.get_apn()
		if not settings:
			settings = {}
			settings['pdns'] = "0.0.0.0"
			settings['sdns'] = "0.0.0.0"
			settings['ip'] = "0.0.0.0"
		if settings['pdns']:
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns1', settings['pdns'])
		if settings['sdns']:
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns2', settings['sdns'])
		if settings['ip']:
			self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_address', settings['ip'])
	
	def get_advanced_apn_settings(self, apn=None):
		if not apn:
			apn = self.get_apn()
		settings = {}
		settings['pdns'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns1')
		settings['sdns'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_dns2')
		settings['ip'] = self.client.get_string('/system/osso/connectivity/IAP/' + apn + '/ipv4_address')
		return settings
	
	def create_new_apn(self):
		""" Create a new APN for MMS usage. """
		# gconf_list_all_dirs is pretty random...
		#apn = "0000-0000-0000-0000"
		import uuid
		apn = str(uuid.uuid4())
		self.client.add_dir('/system/osso/connectivity/IAP/' + apn, gconf.CLIENT_PRELOAD_NONE)
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/type", "GPRS")
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/name", "MMS")
		self.client.set_string('/system/osso/connectivity/IAP/' + apn + "/ipv4_type", "AUTO")
		self.client.set_int('/system/osso/connectivity/IAP/' + apn + "/user_added", 1)
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
		
	def get_active_iaps(self):
		# get all IAP's
		dirs = self.client.all_dirs('/system/osso/connectivity/IAP')
		simimsi = self.get_sim_imsi()
		aps = []
		for subdir in dirs:
			_value = self.client.get_string(subdir + "/sim_imsi")
			if _value == simimsi:
				# split it so we can get the id
				(spath, sep, apnid) = subdir.rpartition('/')
				aps.append(apnid)
		return aps

	def get_all_aps(self):
		# get all IAP's
		dirs = self.client.all_dirs('/system/osso/connectivity/IAP')
		stuff = []
		for subdir in dirs:
			(path, sep, iapid) = subdir.rpartition('/')
			tmp = {}
			tmp['FMMS_KEY_NAME'] = (iapid, gconf.VALUE_STRING)
			all_entries = self.client.all_entries(subdir)
			for entry in all_entries:
				(path, sep, shortname) = entry.key.rpartition('/')
				try:
					_type = entry.value.type
				except Exception, exc:
					_type = None
				if _type == gconf.VALUE_STRING:
					_value = entry.value.get_string()
				elif _type == gconf.VALUE_INT:
					_value = entry.value.get_int()
				elif _type == gconf.VALUE_BOOL:
					_value = entry.value.get_bool()
				elif _type == gconf.VALUE_LIST:
					_value = []
					for n in entry.value.get_list():
						_value.append(n.get_int())
				else:
					_value = None
				tmp[shortname] = (_value, _type)
				
			stuff.append(tmp)
			
		return stuff

	def set_settings_for_apn(self, apn, settings):
		for st in settings:
			if not st == 'FMMS_KEY_NAME':
				if settings[st][1] == gconf.VALUE_STRING:
					self.client.set_string('/system/osso/connectivity/IAP/' + apn + '/' + st, settings[st][0])
				elif settings[st][1] == gconf.VALUE_INT:
					self.client.set_int('/system/osso/connectivity/IAP/' + apn + '/' + st, settings[st][0])
				elif settings[st][1] == gconf.VALUE_BOOL:
					self.client.set_bool('/system/osso/connectivity/IAP/' + apn + '/' + st, settings[st][0])
				elif settings[st][1] == gconf.VALUE_LIST:
					self.client.set_list('/system/osso/connectivity/IAP/' + apn + '/' + st, gconf.VALUE_INT, settings[st][0])
				else:
					log.info("failed to insert:", settings[st][0])
		
	def switcharoo(self, force=False):
		# this assumes the only other APN with the same
		# IMSI is the one that should be default for stuff...
		# iaps[0] == MMS APN, iaps[1] == INET
		# when this function returns
		# iaps[0] == INET, iaps[1] == MMS
		self.client.clear_cache()
		iaps = self.get_active_iaps()
		log.info("IAPs: %s" % iaps)
		if len(iaps) > 1:
			primary = iaps[0]
			secondary = iaps[1]
			allaps = self.get_all_aps()
			for sub in allaps:
				if sub['FMMS_KEY_NAME'][0] == iaps[0]:
					primarysettings = sub
				elif sub['FMMS_KEY_NAME'][0] == iaps[1]:
					secondarysettings = sub

			log.info("CURRENT PRIMARY (%s): %s" % (primary, primarysettings))
			log.info("CURRENT SECONDARY (%s): %s" % (secondary, secondarysettings))
			
			primaryiap = self.client.get_int('/system/osso/connectivity/IAP/' + primary + '/fmms')
			if primaryiap or force:
				log.info("Primary is used by fMMS, switching.")
			else:
				log.info("IAPs seems to be in order, moving along")
				return
			
			# clear out the old settings
			self.client.recursive_unset('/system/osso/connectivity/IAP/' + primary, gconf.UNSET_INCLUDING_SCHEMA_NAMES)
			self.client.recursive_unset('/system/osso/connectivity/IAP/' + secondary, gconf.UNSET_INCLUDING_SCHEMA_NAMES)
			# clear gconf cache (seems like a good idea?)
			self.client.clear_cache()
			
			self.set_settings_for_apn(secondary, primarysettings)
			self.set_settings_for_apn(primary, secondarysettings)
			# from this point on, the "secondary"
			# contains the settings from the old "primary"
			allaps = self.get_all_aps()
			for sub in allaps:
				if sub['FMMS_KEY_NAME'][0] == iaps[0]:
					primarysettings = sub
				elif sub['FMMS_KEY_NAME'][0] == iaps[1]:
					secondarysettings = sub
			log.info("NEW PRIMARY (%s): %s" % (primary, primarysettings))
			log.info("NEW SECONDARY (%s): %s" % (secondary, secondarysettings))
			log.info("SETTING MMS TO: %s" % (secondary))
			self.set_apn(secondary)
		else:
			return iaps[0]

	def reset_all_settings(self):
		log.info("removing connectivity settings: /system/osso/connectivity/IAP/%s" % self.get_apn())
		self.client.recursive_unset('/system/osso/connectivity/IAP/' + self.get_apn(), gconf.UNSET_INCLUDING_SCHEMA_NAMES)
		fmmsdir = self._fmmsdir.rstrip('/')
		log.info("removing fmms application settings: %s" % fmmsdir)
		self.client.recursive_unset(fmmsdir, gconf.UNSET_INCLUDING_SCHEMA_NAMES)
		return True
		
if __name__ == '__main__':
	config = fMMS_config()
	config.switcharoo(force=True)