#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Handles contacts integration for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
from operator import itemgetter
from locale import setlocale, strxfrm, LC_ALL, strcoll
import time

import evolution
import gtk

import logging
log = logging.getLogger('fmms.%s' % __name__)

class ContactHandler:
	
	
	""" wouldnt mind some nice patches against this """
	def __init__(self):
		self.ab = evolution.ebook.open_addressbook("default")
		self.contacts = self.ab.get_all_contacts()
		self.phonedict = {}
		t1 = time.clock()
		for c in self.contacts:
			#print c.get_name(), c.get_property('mobile-phone')
			#print c.get_property('other-phone')
			# this was a pretty clean solution as well, but oh so wrong!
			mb = c.get_property('mobile-phone')
			cp = c.get_property('other-phone')
			nrlist = (mb, cp)
			fname =	c.get_name()
			# TODO: this is _really_ slow... look at integration with c please
			#nrlist = self.get_numbers_from_name(fname)
			self.phonedict[fname] = nrlist
		t2 = time.clock()
		log.info("phonedict loaded: %s in %s" % (len(self.phonedict), round(t2-t1, 5)))
	
	""" returns all the numbers from a name, as a list """
	def get_numbers_from_uid(self, uid):
		res = self.ab.get_contact(uid)
		# would've been nice if this got all numbers, but alas, it dont.
		"""props = ['assistant-phone', 'business-phone', 'business-phone-2', 'callback-phone', 'car-phone', 'company-phone', 'home-phone', 'home-phone-2', 'mobile-phone', 'other-phone', 'primary-phone']
		nrlist = []
		for p in props:
			nr = res.get_property(p)
			if nr != None:
				nrlist.append(nr)"""
		# creative use of processing power? *cough*
		nrlist = {}
		vcardlist = res.get_vcard_string().replace('\r', '').split('\n')
		for line in vcardlist:
			if line.startswith("TEL"):
				nr = line.split(":")[1]
				ltype = line.split(":")[0].split("=")
				phonetype = "Unknown"
				try:
					for type in ltype:
						rtype = type.replace(";TYPE", "")
						if rtype != "TEL" and rtype != "VOICE":
							phonetype = rtype	
				except:
					pass
				if nr != None:
					nrlist[nr] = phonetype
			if line.startswith("EMAIL"):
				nr = line.split(":")[1]
				ltype = line.split(":")[0].split("=")
				phonetype = "Email"
				try:
					for type in ltype:
						rtype = type.replace(";TYPE", "")
						if rtype != "EMAIL":
							phonetype = rtype	
				except:
					pass
				if nr != None:
					nrlist[nr] = phonetype				
		return nrlist
		
	
	""" wrapper to get from uid """
	def get_numbers_from_name(self, fname):
		search = self.ab.search(fname)
		res = search[0].get_uid()
		return self.get_numbers_from_uid(res)
		
	def get_contacts_as_dict(self):
		retlist = {}
		for contact in self.contacts:
			cn = contact.get_name()
			uid = contact.get_uid()
			if cn != None:
				retlist[cn] = uid
		return retlist
	
	""" returns all contact names sorted by name """
	def get_contacts_as_list(self):
		retlist = self.get_contacts_as_dict()

		# call setlocale to init current locale
		setlocale(LC_ALL, "")
		tmplist = sorted(retlist.iteritems(), cmp=strcoll, key=itemgetter(0), reverse=False)
		return tmplist

	
	""" takes a number on international format (ie +46730111111) """
	def get_name_from_number(self, number):
		### do some voodoo here
		# match against the last 7 digits
		numberstrip = number[-7:]
		for person in self.phonedict:
			for cbnr in self.phonedict[person]:
				if cbnr != None:
					cbnr = cbnr.replace(" ", "")
					cbnr = cbnr[-7:]
					if (cbnr == number or numberstrip.endswith(cbnr) or number.endswith(cbnr)) and len(cbnr) >= 7:
						return person
		return None
	
	# TODO: get from uid instead of name
	def get_photo_from_name(self, pname, imgsize):
		res = self.ab.search(pname)
		### do some nice stuff here
		l = [x.get_name() for x in res]
		#log.info("search for: %s gave: %s (%s) (length: %s)", pname, l, l.__class__, len(l))
		if res != None and res.__class__ == list and len(res) > 0:
			img = res[0].get_photo(imgsize)
			if img == None:
				vcardlist = res[0].get_vcard_string().replace('\r', '').split('\n') # vcard for first result
				for line in vcardlist:
					if line.startswith("PHOTO;VALUE=uri:file://"):
						imgstr = line.replace("PHOTO;VALUE=uri:file://", "")
						img = gtk.gdk.pixbuf_new_from_file(imgstr)
						height = img.get_height()
						if height != imgsize:
							newheight = imgsize
							newwidth = int(newheight * img.get_width() / height)
							img = img.scale_simple(newwidth, newheight, gtk.gdk.INTERP_BILINEAR)
			return img
		else:
			return None
		
		
if __name__ == '__main__':
	cb = ContactHandler()
