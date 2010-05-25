#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Handles contacts integration for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
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
		
	def get_displayname_from_number(self, sndr):
		sndr = str(sndr).replace("/TYPE=PLMN", "")
		sender = sndr
		senderuid = self.get_uid_from_number(sndr)
		if senderuid != None:
			sender = self.get_displayname_from_uid(senderuid)
		if sender != None:
			sndr = sender
		return sndr
	
	def get_displayname_from_uid(self, uid):
		contact = self.ab.get_contact(str(uid))
		if contact:
			contact = contact.get_name()
		return contact

	def contact_chooser_dialog(self):
		capi = PyGObjectCPAI()
		c_chooser = self.osso_abook.osso_abook_contact_chooser_new(None, "Choose a contact")
		chooser = capi.pygobject_new(c_chooser)
		chooser.run()
		chooser.hide()
		contacts = self.osso_abook.osso_abook_contact_chooser_get_selection(c_chooser)
		for i in self.glist(contacts):
			c_selector = self.osso_abook.osso_abook_contact_detail_selector_new_for_contact(c_chooser, i, 3)
			selector = capi.pygobject_new(c_selector)
			selector.run()
			selector.hide()
			c_field = self.osso_abook.osso_abook_contact_detail_selector_get_selected_field(c_selector)
			get_display_value = self.osso_abook.osso_abook_contact_field_get_display_value
			get_display_value.restype = ctypes.c_char_p
			finalval = self.osso_abook.osso_abook_contact_field_get_display_value(c_field)
			self.glib.g_list_free(contacts)
			return finalval
			
		self.glib.g_list_free(contacts)

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
		class _GList(ctypes.Structure):
			_fields_ = [('data', ctypes.c_void_p),
				    ('next', ctypes.c_void_p)]
		l = addr
		while l:
			if type(l) == int:
				l = _GList.from_address(l)
			else:
				l = _GList.from_address(l.value)
			yield l.data
			l = l.next
		
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
