#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Useful functions that shouldn't be in the UI code

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import StringIO

import gtk

import controller

import logging
log = logging.getLogger('fmms.%s' % __name__)

MSG_DIRECTION_IN = 0
MSG_DIRECTION_OUT = 1
MSG_UNREAD = 0
MSG_READ = 1

class fMMS_controllerGTK(controller.fMMS_controller):

		
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