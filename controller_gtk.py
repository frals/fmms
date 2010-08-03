#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Useful functions that shouldn't be in the UI code

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import StringIO
import gettext

import gtk
import hildon

import controller
import heaboutdialog

import logging
log = logging.getLogger('fmms.%s' % __name__)

MSG_DIRECTION_IN = 0
MSG_DIRECTION_OUT = 1
MSG_UNREAD = 0
MSG_READ = 1

_ = gettext.gettext

class fMMS_controllerGTK(controller.fMMS_controller):
	
	def __init__(self):
		controller.fMMS_controller.__init__(self)
		self.config_label = gettext.ldgettext('rtcom-messaging-ui', "messaging_me_main_settings")
		self.about_label = gettext.ldgettext('hildon-libs', "ecdg_ti_aboutdialog_title")
	
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
		config.set_label(self.config_label)
		config.connect('clicked', self.menu_button_clicked, parent)
		
		about = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		about.set_label(self.about_label)
		about.connect('clicked', self.menu_button_clicked, parent)
		
		menu.append(config)
		menu.append(about)

		menu.show_all()

		return menu

	def menu_button_clicked(self, button, parent):
		""" Determine what button was clicked in the app menu. """
		buttontext = button.get_label()
		if buttontext == self.config_label:
			self.import_configdialog()
			fMMSConfigDialog.fMMS_ConfigDialog(parent)
		elif buttontext == self.about_label:
			self.create_about_dialog(parent)

	def create_about_dialog(self, parent=None):
		""" Create and display the About dialog. """
		heaboutdialog.HeAboutDialog.present(parent,
					'fMMS',
					'fmms',
					self.config.get_version(),
					_('Send and receive MMS on your N900.'),
					'Copyright (C) 2010 Nick Leppänen Larsson.\n' +
					'This program is free software; you can redistribute it and/or' +
					 ' modify it under the terms of the GNU General Public License' +
					 ' as published by the Free Software Foundation; either version 2' +
					 ' of the License, or (at your option) any later version.\n' +
					 'This program is distributed in the hope that it will be useful,' +
					 ' but WITHOUT ANY WARRANTY; without even the implied warranty of' +
					 ' MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the' +
					 ' GNU General Public License for more details.',
					'http://mms.frals.se/',
					'http://bugs.maemo.org/enter_bug.cgi?product=fMMS',
					'https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=AZKC7ZRYKEY76&lc=SE&item_name=frals_mms&item_number=fmms_app&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted')
		
		
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