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
import ctypes

import evolution
import gtk
import osso

import logging
log = logging.getLogger('fmms.%s' % __name__)

class ContactHandler:

	def __init__(self):
		""" Load the evolution addressbook and prepare ctypes for ossoabook. """
		self.ab = evolution.ebook.open_addressbook("default")
		self.contacts = self.ab.get_all_contacts()
		t1 = time.clock()
		self.osso_ctx = osso.Context("fMMS_CONTACTS", "0.1")
		self.osso_abook = ctypes.CDLL('libosso-abook-1.0.so.0')
		empty = ""
		argv_type = ctypes.c_char_p * len(empty)
		argv = argv_type(*empty)
		argc = ctypes.c_int(len(empty))
		self.osso_abook.osso_abook_init(ctypes.byref(argc), ctypes.byref(argv), hash(self.osso_ctx))
		self.ebook = ctypes.CDLL('libebook-1.2.so.5')
		err = ctypes.c_void_p()
		self.c_book = self.ebook.e_book_new_default_addressbook(ctypes.byref(err))
		self.glib = ctypes.CDLL('libglib-2.0.so.0')
		t2 = time.clock()
		log.info("loaded contacthandler in %s s" % round(t2-t1, 5))
	
	def get_numbers_from_uid(self, uid):
		""" Returns all the numbers from a name, as a list. """
		res = self.ab.get_contact(str(uid))
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

	def get_displayname_from_uid(self, uid):
		contact = self.ab.get_contact(uid)
		return contact.get_name()
	
	def get_contacts_as_dict(self):
		retlist = {}
		for contact in self.contacts:
			cn = contact.get_name()
			uid = contact.get_uid()
			if cn != None:
				retlist[cn] = uid
		return retlist
	
	def get_contacts_as_list(self):
		""" returns all contact names sorted by name """
		retlist = self.get_contacts_as_dict()

		# call setlocale to init current locale
		setlocale(LC_ALL, "")
		tmplist = sorted(retlist.iteritems(), cmp=strcoll, key=itemgetter(0), reverse=False)
		return tmplist

	def get_uid_from_number(self, number):
		""" Gets the contacts UID from a given phonenumber.
		
		Thanks lizardo for the great example how to implement this.
		"""
		if not self.ebook.e_book_open(self.c_book, 1, 0):
			raise TypeError("Could not open ebook")
		
		# The '1' means fuzzy matching is active
		c_query = self.osso_abook.osso_abook_query_phone_number(number, 1)

		contacts = ctypes.c_void_p()
		if not self.ebook.e_book_get_contacts(self.c_book, c_query, ctypes.byref(contacts), 0):
			raise TypeError("Failed to get query results.")

		for i in self.glist(contacts):
			E_CONTACT_UID = 1
			e_contact_get_const = self.ebook.e_contact_get_const
			e_contact_get_const.restype = ctypes.c_char_p
			uid = e_contact_get_const(i, E_CONTACT_UID)
			self.glib.g_list_free(contacts)
			return uid

		self.glib.g_list_free(contacts)
		return None
		
	def glist(self, addr):
		""" Implementation of GList. """
		size = self.glib.g_list_length(addr)
		class _GList(ctypes.Structure):
			_fields_ = [('data', ctypes.c_void_p)]
		for i in xrange(0, size):
			item = self.glib.g_list_nth(addr, i)
			yield _GList.from_address(item).data
		
	def get_photo_from_uid(self, uid, imgsize):
		contact = self.ab.get_contact(str(uid))
		img = contact.get_photo(imgsize)
		if img == None:
			vcardlist = contact.get_vcard_string().replace('\r', '').split('\n') # vcard for first result
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


# ctypes wrapper for pygobject_new(), based on code snippet from
# http://faq.pygtk.org/index.py?req=show&file=faq23.041.htp
class _PyGObject_Functions(ctypes.Structure):
	_fields_ = [
		('register_class',
		    ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p,
		    ctypes.c_int, ctypes.py_object, ctypes.py_object)),
		('register_wrapper',
		    ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.py_object)),
		('register_sinkfunc',
		    ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_void_p)),
		('lookupclass',
		    ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_int)),
		('newgobj',
		    ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_void_p)),
	]

class PyGObjectCPAI(object):
	def __init__(self):
		import gobject
		py_obj = ctypes.py_object(gobject._PyGObject_API)
		addr = ctypes.pythonapi.PyCObject_AsVoidPtr(py_obj)
		self._api = _PyGObject_Functions.from_address(addr)

	def pygobject_new(self, addr):
		return self._api.newgobj(addr)


if __name__ == '__main__':
	cb = ContactHandler()
