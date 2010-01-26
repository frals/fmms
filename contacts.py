#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Handles contacts integration for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import evolution
import gtk
	
class ContactHandler:
	
	
	""" wouldnt mind some nice patches against this """
	def __init__(self):
		self.ab = evolution.ebook.open_addressbook("default")
		self.contacts = self.ab.get_all_contacts()
		self.phonedict = {}
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
			self.phonedict[c.get_name()] = nrlist
	
	""" returns all the numbers from a name, as a list """
	def get_numbers_from_name(self, fname):
		search = self.ab.search(fname)
		res = search[0]
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
				#print line
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
		return nrlist
		
	
	""" returns all contact names sorted by name """
	def get_contacts_as_list(self):
		retlist = []
		for contact in self.contacts:
			cn = contact.get_name()
			if cn != None:
				retlist.append(cn)
		retlist.sort(key=str.lower)
		return retlist
	
	""" takes a number on international format (ie +46730111111) """
	def get_name_from_number(self, number):
		### do some voodoo here
		# ugly way of removing country code since this
		# can be 2 or 3 chars we remove 4 just in case
		# 3 and the + char = 4
		numberstrip = number[4:-1]
		for person in self.phonedict:	
			for cbnr in self.phonedict[person]:
				if cbnr != None:
					cbnr = cbnr.replace(" ", "")
					cbnr = cbnr.lstrip('0')
					if cbnr == number or numberstrip.endswith(cbnr) or number.endswith(cbnr):
						return person
					
		return None
	
	def get_photo_from_name(self, pname, imgsize):
		res = self.ab.search(pname)
		### do some nice stuff here
		#l = [x.get_name() for x in res]
		#print "search for:", pname, "gave res: ", l
		if res != None:
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
							#print "h:", height, "w:", img.get_width()
							#print "newh:", newheight, "neww:", newwidth
							img = img.scale_simple(newwidth, newheight, gtk.gdk.INTERP_BILINEAR)
			return img
		else:
			return None
		
		
if __name__ == '__main__':
	cb = ContactHandler()
	#c = ab.get_contact("id")
