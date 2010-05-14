#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Useful functions that shouldn't be in the UI code

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import StringIO

import gtk
import hildon

import controller

import logging
log = logging.getLogger('fmms.%s' % __name__)

MSG_DIRECTION_IN = 0
MSG_DIRECTION_OUT = 1
MSG_UNREAD = 0
MSG_READ = 1

class fMMS_controllerGTK(controller.fMMS_controller):
	
	def import_configdialog(self):
		""" This is used to import configdialog only when we need it
		    as its quite a hog """
		try:
			if not self.cdimported:
				import fmms_config_dialog as fMMSConfigDialog
				global fMMSConfigDialog
				self.cdimported = True
		except:
			import fmms_config_dialog as fMMSConfigDialog
			global fMMSConfigDialog
			self.cdimported = True
	
	def create_menu(self, parent=None):
		""" Creates the application menu. """
		menu = hildon.AppMenu()

		config = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		config.set_label("Configuration")
		config.connect('clicked', self.menu_button_clicked, parent)

		about = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		about.set_label("About")
		about.connect('clicked', self.menu_button_clicked, parent)

		menu.append(config)
		menu.append(about)

		menu.show_all()

		return menu

	def menu_button_clicked(self, button, parent):
		""" Determine what button was clicked in the app menu. """
		buttontext = button.get_label()
		if buttontext == "Configuration":
			self.import_configdialog()
			fMMSConfigDialog.fMMS_ConfigDialog(parent)
		elif buttontext == "About":
			self.create_about_dialog()

	def create_about_dialog(self):
		""" Create and display the About dialog. """
		dialog = gtk.AboutDialog()
		dialog.set_name("fMMS")
		fmms_logo = gtk.gdk.pixbuf_new_from_file("/opt/fmms/fmms.png")
		dialog.set_logo(fmms_logo)
		dialog.set_comments('MMS send and receive support for Fremantle')
		dialog.set_version(self.config.get_version())
		dialog.set_copyright("By Nick Leppänen Larsson (aka frals)")
		gtk.about_dialog_set_url_hook(lambda dialog, link: self.osso_rpc.rpc_run_with_defaults("osso_browser", "open_new_window", (link,)))
		dialog.set_website("http://mms.frals.se/")
		dialog.connect("response", lambda d, r: d.destroy())
		dialog.show()
		
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
			log.info("Failed to convert, trying as gif.")
			try:
				im.save(file1, "gif")
				contents = file1.getvalue()
				file1.close()
				loader = gtk.gdk.PixbufLoader()
				loader.write(contents, len(contents))
				pixbuf = loader.get_pixbuf()
				loader.close()
				return pixbuf
			except:
				log.exception("Failed to convert")
				raise