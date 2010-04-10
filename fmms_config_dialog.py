#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" GUI.

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import gtk
import hildon
import logging
log = logging.getLogger('fmms.%s' % __name__)

import fmms_config as fMMSconf

class fMMS_ConfigDialog():

	def __init__(self, spawner):
		""" Create and display the Configuration dialog. """
		self.config = fMMSconf.fMMS_config()
		
		self.window = spawner
		
		dialog = gtk.Dialog()
		#dialog.set_transient_for(self.window)
		dialog.set_title("Configuration")

		allVBox = gtk.VBox()

		self.active_apn_index = 0

		labelwidth = 16

		apnHBox = gtk.HBox()
		apn_label = gtk.Label("APN:")
		apn_label.set_width_chars(labelwidth)
		self.selector = self.create_apn_selector()
		self.apn = hildon.PickerButton(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
		self.apn.set_selector(self.selector)
		self.apn.set_active(self.active_apn_index)

		apnHBox.pack_start(apn_label, False, True, 0)
		apnHBox.pack_start(self.apn, True, True, 0)

		mmscHBox = gtk.HBox()
		mmsc_label = gtk.Label("MMSC:")
		mmsc_label.set_width_chars(labelwidth)
		self.mmsc = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		mmsc_text = self.config.get_mmsc()
		if mmsc_text != None:	
			self.mmsc.set_text(mmsc_text)
		else:
			self.mmsc.set_text("http://")
		mmscHBox.pack_start(mmsc_label, False, True, 0)
		mmscHBox.pack_start(self.mmsc, True, True, 0)

		numberHBox = gtk.HBox()
		number_label = gtk.Label("Your phonenumber:")
		number_label.set_width_chars(labelwidth)
		self.number = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.number.set_property('hildon-input-mode', gtk.HILDON_GTK_INPUT_MODE_TELE)
		number_text = self.config.get_phonenumber()
		if number_text != None:
			self.number.set_text(number_text)
		else:
			self.number.set_text("")
		numberHBox.pack_start(number_label, False, True, 0)
		numberHBox.pack_start(self.number, True, True, 0)

		imgwidthHBox = gtk.HBox()
		imgwidth_label = gtk.Label("Resize image width:")
		imgwidth_label.set_width_chars(labelwidth)
		self.imgwidth = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.imgwidth.set_max_length(5)
		#self.imgwidth_signal = self.imgwidth.connect('insert_text', self.insert_resize_cb)
		self.imgwidth.set_property('hildon-input-mode', gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
		imgwidth_text = self.config.get_img_resize_width()
		if imgwidth_text != None:
			self.imgwidth.set_text(str(imgwidth_text))
		else:
			self.imgwidth.set_text("")
		imgwidthHBox.pack_start(imgwidth_label, False, True, 0)
		imgwidthHBox.pack_start(self.imgwidth, True, True, 0)


		expHBox = gtk.HBox()
		exp_label = gtk.Label("Connection mode")
		exp_label.set_width_chars(labelwidth)
		# havoc = CONNMODE_UGLYHACK = 1
		# polite = CONNMODE_ICDSWITCH = 2
		# rude = CONNMODE_FORCESWITCH = 3
		self.havocbutton = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.havocbutton.set_label("Havoc")
		self.rudebutton = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT, self.havocbutton)
		self.rudebutton.set_label("Rude")
		self.icdbutton = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT, self.havocbutton)
		self.icdbutton.set_label("Polite")
		# Set the correct button to be active
		self.connmode_setactive()

		expHBox.pack_start(exp_label, False, True, 0)
		expHBox.pack_start(self.icdbutton, True, True, 0)
		expHBox.pack_start(self.rudebutton, True, True, 0)
		expHBox.pack_start(self.havocbutton, True, True, 0)

		allVBox.pack_start(apnHBox, False, False, 0)
		allVBox.pack_start(mmscHBox, False, False, 0)
		allVBox.pack_start(numberHBox, False, False, 0)
		allVBox.pack_start(imgwidthHBox, False, False, 0)
		allVBox.pack_end(expHBox, False, False, 0)

		allVBox.show_all()
		dialog.vbox.add(allVBox)
		dialog.add_button("Save", gtk.RESPONSE_APPLY)
		ret = dialog.run()
		ret2 = self.config_menu_button_clicked(ret)
		dialog.destroy()

	def create_apn_selector(self):
		""" Creates and populates the APN selector. """
		selector = hildon.TouchSelector(text = True)
		apnlist = self.config.get_gprs_apns()
		currval = self.config.get_apn_nicename()
		# Populate selector
		i = 0
		for apn in apnlist:
			if apn != None:
				if apn == currval:
					self.active_apn_index = i
				i += 1	
				# Add item to the column 
				selector.append_text(apn)

		selector.center_on_selected()
		selector.set_active(0, i)
		# Set selection mode to allow multiple selection
		selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
		return selector

	def connmode_option(self):
		""" Returns which 'Connection Mode' button is active. """
		if self.havocbutton.get_active():
			return fMMSconf.CONNMODE_UGLYHACK
		elif self.icdbutton.get_active():
			return fMMSconf.CONNMODE_ICDSWITCH
		elif self.rudebutton.get_active():
			return fMMSconf.CONNMODE_FORCESWITCH

	def connmode_setactive(self):
		""" Activate one of the 'Connection Mode' buttons. """
		if self.config.get_connmode() == fMMSconf.CONNMODE_UGLYHACK:
			self.havocbutton.set_active(True)
		elif self.config.get_connmode() == fMMSconf.CONNMODE_ICDSWITCH:
			self.icdbutton.set_active(True)
		elif self.config.get_connmode() == fMMSconf.CONNMODE_FORCESWITCH:
			self.rudebutton.set_active(True)

	def config_menu_button_clicked(self, action):
		""" Checks if we should save the Configuration options. """
		if action == gtk.RESPONSE_APPLY:
			log.info("%s", self.apn.get_selector().get_current_text())
			ret_setapn = self.config.get_apnid_from_name(self.apn.get_selector().get_current_text())
			if ret_setapn != None:
				self.config.set_apn(ret_setapn)
				log.info("Set apn to: %s" % ret_setapn)
				ret = self.config.set_mmsc(self.mmsc.get_text())
				log.info("Set mmsc to %s" % self.mmsc.get_text())
				self.config.set_phonenumber(self.number.get_text())
				log.info("Set phonenumber to %s" % self.number.get_text())
				self.config.set_img_resize_width(self.imgwidth.get_text())
				log.info("Set image width to %s" % self.imgwidth.get_text())
				self.config.set_connmode(self.connmode_option())
				log.info("Set connection mode %s" % self.connmode_option())				
				banner = hildon.hildon_banner_show_information(self.window, "", "Settings saved")
				return 0
			else:
				log.info("Set mmsc to %s" % self.mmsc.get_text())
				self.config.set_phonenumber(self.number.get_text())
				log.info("Set phonenumber to %s" % self.number.get_text())
				self.config.set_img_resize_width(self.imgwidth.get_text())
				log.info("Set image width to %s" % self.imgwidth.get_text())
				banner = hildon.hildon_banner_show_information(self.window, "", "Could not save APN settings. Did you enter a correct APN?")
				banner.set_timeout(5000)
			return -1