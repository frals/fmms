#!/usr/bin/env python2.5

import gtk
import dbus
import hildon
from hildondesktop import StatusMenuItem
import gettext

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

import gobject

class fMMSStatusPlugin(StatusMenuItem):

	def __init__(self):
		StatusMenuItem.__init__(self)
		pixbuf_name = 'general_packetdata'

		bus = dbus.SessionBus()
		bus.add_signal_receiver(self.update, dbus_interface='se.frals.fmms.statusmenu')

		icon_theme = gtk.icon_theme_get_default()

		self.pixbuf = icon_theme.load_icon(pixbuf_name, 22, gtk.ICON_LOOKUP_NO_SVG)

		fmmsicon = icon_theme.load_icon("fmms", 48, 0)
		img = gtk.Image()
		img.set_from_pixbuf(fmmsicon)
		img.set_alignment(1, 0.5)

		self.button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
		self.button.set_image(img)
		self.button.set_text("fMMS", "Wreaking HAVOC")
		self.button.set_image_position(gtk.POS_LEFT)
		self.button.set_alignment(0.0, 0.5, 1, 1)
		#self.show_all()
		
	def update(self, *args):
		status = -1
		try:
			status = args[0]
			msg = args[1]
			if msg == 'Downloading':
				msg = gettext.ldgettext('hildon-application-manager', "ai_nw_downloading") % "MMS"
			elif msg == 'Sending':
				msg = gettext.ldgettext('modest', "mcen_li_outbox_sending")
		except:
			msg = ''
			pass
		print status, msg
		if status:
			self.button.set_text("fMMS", msg)
			self.add(self.button)
			self.set_status_area_icon(self.pixbuf)
			self.show_all()
		elif status == 0:
			self.button.hide()
			self.hide()
			self.set_status_area_icon(None)
		else:
			pass
		

hd_plugin_type = fMMSStatusPlugin