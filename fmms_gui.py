#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Main-view UI for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import os
import time
import cgi
import re

import gtk
import hildon
import osso
import gobject
import dbus
from gnome import gnomevfs

from wappushhandler import PushHandler
import fmms_config as fMMSconf
import fmms_sender_ui as fMMSSenderUI
import fmms_viewer as fMMSViewer
import controller as fMMSController
import contacts as ContactH

import logging
log = logging.getLogger('fmms.%s' % __name__)


class fMMS_GUI(hildon.Program):

	def __init__(self):
		self.cont = fMMSController.fMMS_controller()
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self.ch = ContactH.ContactHandler()
		self.osso_c = osso.Context("fMMS", self.config.get_version(), False)
		self.osso_rpc = osso.Rpc(self.osso_c)
		
		self.refreshlistview = True
	
		if not os.path.isdir(self._mmsdir):
			log.info("creating dir %s", self._mmsdir)
			os.makedirs(self._mmsdir)
		if not os.path.isdir(self._pushdir):
			log.info("creating dir %s", self._pushdir)
			os.makedirs(self._pushdir)
	
		hildon.Program.__init__(self)
		program = hildon.Program.get_instance()
		
		self.osso_rpc = osso.Rpc(self.osso_c)
      		self.osso_rpc.set_rpc_callback("se.frals.fmms","/se/frals/fmms","se.frals.fmms", self.cb_open_fmms, self.osso_c)
		
		self.window = hildon.StackableWindow()
		self.window.set_title("fMMS")
		program.add_window(self.window)
		
		self.window.connect("delete_event", self.quit)
		
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_VERT)
		
		### TODO: dont hardcode the values here.. oh well
		iconcell = gtk.CellRendererPixbuf()
		photocell = gtk.CellRendererPixbuf()
		textcell = gtk.CellRendererText()
		photocell.set_property('xalign', 1.0)
		textcell.set_property('mode', gtk.CELL_RENDERER_MODE_INERT)
		textcell.set_property('xalign', 0.0)
		
		self.liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, gtk.gdk.Pixbuf, str, str)
		self.treeview = hildon.GtkTreeView(gtk.HILDON_UI_MODE_NORMAL)
		self.treeview.set_property("fixed-height-mode", True)
		self.treeview.set_model(self.liststore)

		icon_col = gtk.TreeViewColumn('Icon')
		sender_col = gtk.TreeViewColumn('Sender')
		placeholder_col = gtk.TreeViewColumn('Photo')

		icon_col.pack_start(iconcell, False)
		icon_col.set_attributes(iconcell, pixbuf=0)
		icon_col.set_fixed_width(64)
		icon_col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		sender_col.pack_start(textcell, True)
		sender_col.set_attributes(textcell, markup=1)
		sender_col.set_fixed_width(640)
		sender_col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		placeholder_col.pack_end(photocell, False)
		placeholder_col.set_attributes(photocell, pixbuf=2)
		placeholder_col.set_fixed_width(64)
		placeholder_col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		
		self.treeview.append_column(icon_col)
		self.treeview.append_column(sender_col)
		self.treeview.append_column(placeholder_col)

		self.treeview.tap_and_hold_setup(self.liststore_mms_menu())
		self.treeview.tap_and_hold_setup(None)
		self.tapsignal = self.treeview.connect('hildon-row-tapped', self.show_mms)
		self.treeview.connect('button-press-event', self.cb_button_press)

		mmsBox = gtk.HBox()
		icon_theme = gtk.icon_theme_get_default()
		envelopePixbuf = icon_theme.load_icon("general_sms_button", 48, 0)
		envelopeImage = gtk.Image()
		envelopeImage.set_from_pixbuf(envelopePixbuf)
		envelopeImage.set_alignment(1, 0.5)
		mmsLabel = gtk.Label("New MMS")
		mmsLabel.set_alignment(0, 0.5)
		
		mmsBox.pack_start(envelopeImage, True, True, 0)
		mmsBox.pack_start(mmsLabel, True, True, 0)
		newMsgButton = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
		
		newMsgButton.add(mmsBox)
		newMsgButton.connect('clicked', self.new_mms_button_clicked)

		""" gets the newMsgButton on top of the treeview """
		actionbox = self.treeview.get_action_area_box()
		self.treeview.set_action_area_visible(True)
		actionbox.add(newMsgButton)
		
		pan.add(self.treeview)

		align = gtk.Alignment(1, 1, 1, 1)
		align.set_padding(2, 2, 10, 10)		
		align.add(pan)
		
		self.window.add(align)
	
		self.menu = self.create_menu()
		self.window.set_app_menu(self.menu)
		
		self.window.connect('focus-in-event', self.cb_on_focus)
		
		self.window.show_all()
		self.add_window(self.window)


	""" need this to always have the current path """
	def cb_button_press(self, widget, event):
		try:
			(self.curPath, tvcolumn, x, y) = self.treeview.get_path_at_pos(int(event.x), int(event.y))
		except:
			self.curPath = None
		return False


	def cb_on_focus(self, widget, event):
		if self.refreshlistview == True:
			t1 = time.clock()
			hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
			self.force_ui_update()
			self.liststore.clear()
			self.add_buttons_liststore()
			hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
			t2 = time.clock()
			log.info("liststore time: %s" % round(t2-t1, 3))
			self.refreshlistview = False
			
			if self.config.get_firstlaunch() == 1:
						note = osso.SystemNote(self.osso_c)
						firstlaunchmessage = "NOTE: Currently you have to connect manually to the MMS APN when sending and receiving.\nOnly implemented attachment is image."
						note = hildon.hildon_note_new_information(self.window, firstlaunchmessage)
						self.create_config_dialog()
						self.config.set_firstlaunch(0)
						note.run()
						note.destroy()
		return True


	def cb_open_fmms(self, interface, method, args, user_data):
		if method != 'open_mms' and method != 'open_gui' and method != 'send_via_service':
			return
		if method == 'open_mms':
			filename = args[0]
			if self.cont.is_fetched_push_by_transid(filename):
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
				self.force_ui_update()
				viewer = fMMSViewer.fMMS_Viewer(filename)
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
				return
			else:
				return
		elif method == 'open_gui':
			# this shouldnt be needed as the on-focus cb should activate
			#self.cb_on_focus(None, None)
			return
		elif method == 'send_mms':
			log.info("launching sender with args: %s", args)
			self.refreshlistview = True
			fMMSSenderUI.fMMS_SenderUI(tonumber=args[0]).run()
			return
		elif method == 'send_via_service':
			log.info("launching sendviaservice with args: %s", args)
			self.refreshlistview = False
			ret = fMMSSenderUI.fMMS_SenderUI(withfile=args[0], subject=args[1], message=args[2]).run()
			self.quit()
		
	def create_menu(self):
		menu = hildon.AppMenu()
		
		config = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		config.set_label("Configuration")
		config.connect('clicked', self.menu_button_clicked)
		
		about = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		about.set_label("About")
		about.connect('clicked', self.menu_button_clicked)
		
		menu.append(config)
		menu.append(about)
		
		menu.show_all()
		
		return menu
		
		
	def menu_button_clicked(self, button):
		buttontext = button.get_label()
		if buttontext == "Configuration":
			ret = self.create_config_dialog()
		elif buttontext == "About":
			ret = self.create_about_dialog()
	
	
	def new_mms_button_clicked(self, button):
		self.refreshlistview = True
		ret = fMMSSenderUI.fMMS_SenderUI(self.window).run()
		
		
	def create_about_dialog(self):
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
 

	def create_config_dialog(self):
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
		self.imgwidth_signal = self.imgwidth.connect('insert_text', self.insert_resize_cb)
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
		""" 
		    havoc = CONNMODE_UGLYHACK = 1
		    polite = CONNMODE_ICDSWITCH = 2
		    rude = CONNMODE_FORCESWITCH = 3
		"""
		self.havocbutton = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.havocbutton.set_label("Havoc")
		self.rudebutton = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT, self.havocbutton)
		self.rudebutton.set_label("Rude")
		self.icdbutton = hildon.GtkRadioButton(gtk.HILDON_SIZE_FINGER_HEIGHT, self.havocbutton)
		self.icdbutton.set_label("Polite")
		""" set the correct button active """
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

		
	""" from http://faq.pygtk.org/index.py?req=show&file=faq14.005.htp """
	def insert_resize_cb(self, widget, text, length, *args):
		# if you don't do this, garbage comes in with text
		text = text[:length]
		pos = widget.get_position()
		# stop default emission
		widget.emit_stop_by_name("insert_text")
		signal = self.imgwidth_signal
		gobject.idle_add(self.insert_nr_mod, widget, signal, text, pos)
		
		
	""" from http://faq.pygtk.org/index.py?req=show&file=faq14.005.htp """
	def insert_nr_mod(self, widget, signal, text, pos):
		# the next three lines set up the text. this is done because we
		# can't use insert_text(): it always inserts at position zero.
		orig_text = widget.get_text()
		#text = string.replace(text, " ", "<SPACE>")
		pattern = re.compile('[!^\D]')
		text = pattern.sub("", text)
		new_text = orig_text[:pos] + text + orig_text[pos:]
		# avoid recursive calls triggered by set_text
		widget.handler_block(signal)
		# replace the text with some new text
		widget.set_text(new_text)
		widget.handler_unblock(signal)
		# set the correct position in the widget
		widget.set_position(pos + len(text))



	""" selector for apn """
	def create_apn_selector(self):
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
		""" 
		    havoc = CONNMODE_UGLYHACK = 1
		    polite = CONNMODE_ICDSWITCH = 2
		    rude = CONNMODE_FORCESWITCH = 3
		"""
		if self.havocbutton.get_active():
			return fMMSconf.CONNMODE_UGLYHACK
		elif self.icdbutton.get_active():
			return fMMSconf.CONNMODE_ICDSWITCH
		elif self.rudebutton.get_active():
			return fMMSconf.CONNMODE_FORCESWITCH
		
	def connmode_setactive(self):
		if self.config.get_connmode() == fMMSconf.CONNMODE_UGLYHACK:
			self.havocbutton.set_active(True)
		elif self.config.get_connmode() == fMMSconf.CONNMODE_ICDSWITCH:
			self.icdbutton.set_active(True)
		elif self.config.get_connmode() == fMMSconf.CONNMODE_FORCESWITCH:
			self.rudebutton.set_active(True)
	
		
	def config_menu_button_clicked(self, action):
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


	""" add each item to our liststore """
	def add_buttons_liststore(self):
			icon_theme = gtk.icon_theme_get_default()
			
			pushlist = self.cont.get_push_list()
			
			primarytxt = self.cont.get_primary_font().to_string()
			primarycolor = self.cont.get_primary_color().to_string()
			highlightcolor = self.cont.get_active_color().to_string()
			secondarytxt = self.cont.get_secondary_font().to_string()
			secondarycolor = self.cont.get_secondary_color().to_string()
			for varlist in pushlist:
                                mtime = varlist['Time']
                                # TODO: Remove date if date == today
                                # TODO: get locale format?
                                mtime = self.cont.convert_timeformat(mtime, "%Y-%m-%d | %H:%M")

				fname = varlist['Transaction-Id']
				direction = self.cont.get_direction_mms(fname)

				isread = False
				if self.cont.is_mms_read(fname):
					isread = True
				
				try:
					sender = varlist['From']
					sender = sender.replace("/TYPE=PLMN", "")
				except:
					sender = "0000000"
				
				if direction == fMMSController.MSG_DIRECTION_OUT:
					sender = self.cont.get_mms_headers(varlist['Transaction-Id'])
					sender = sender['To'].replace("/TYPE=PLMN", "")
				
				sendername = self.ch.get_name_from_number(sender)
				photo = icon_theme.load_icon("general_default_avatar", 48, 0)
				if sendername != None:
					sender = sendername
					phototest = self.ch.get_photo_from_name(sendername, 48)
					if phototest != None:	
						photo = phototest
				
				if direction == fMMSController.MSG_DIRECTION_OUT:
					icon = icon_theme.load_icon("chat_replied_sms", 48, 0)
				elif self.cont.is_fetched_push_by_transid(fname) and isread:
					icon = icon_theme.load_icon("general_sms", 48, 0)
				else:
					icon = icon_theme.load_icon("chat_unread_sms", 48, 0)
					
				try:
					headerlist = self.cont.get_mms_headers(fname)
					description = cgi.escape(headerlist['Description'])
				except:
					try:
						description = varlist['Subject']
					except:
						description = ""
						
				primarytext = ' <span font_desc="%s" foreground="%s"><sup>%s</sup></span>' % (secondarytxt, secondarycolor, mtime)
				secondarytext = '\n<span font_desc="%s" foreground="%s">%s</span>' % (secondarytxt, secondarycolor, description)
				if not isread and direction == fMMSController.MSG_DIRECTION_IN:
					sender = '<span foreground="%s">%s</span>' % (highlightcolor, sender)
				stringline = "%s%s%s" % (sender, primarytext, secondarytext)
				self.liststore.append([icon, stringline, photo, fname, sender])

	
	""" lets call it quits! """
	def quit(self, *args):
		gtk.main_quit()
	
	
	""" forces ui update, kinda... god this is AWESOME """
	def force_ui_update(self):
		while gtk.events_pending():
			gtk.main_iteration(False)
		
		
	""" delete push message """
	def delete_push(self, fname):
		self.cont.delete_push_message(fname)
		
	
	""" delete mms message (eg for redownload) """
	def delete_mms(self, fname):
		self.cont.delete_mms_message(fname)

	
	""" delete push & mms """
	def delete_push_mms(self, fname):
		try:
			self.cont.wipe_message(fname)
			#banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Message deleted")
			self.refreshlistview = True
		except Exception, e:
			log.exception("%s %s", type(e), e)
			#raise
			banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Failed to delete message.")
			self.refreshlistview = True


	""" action on delete contextmenu click """
	def liststore_delete_clicked(self, widget):
		if self.curPath == None:
			return
			
		model = self.treeview.get_model()
		miter = model.get_iter(self.curPath)
		# the 4th value is the transactionid (start counting at 0)
		filename = model.get_value(miter, 3)
		
		dialog = gtk.Dialog()
		dialog.set_title("Confirm")
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		label = gtk.Label("Are you sure you want to delete the message?")
		dialog.vbox.add(label)
		dialog.show_all()
		ret = dialog.run()
		if ret == 1:
			log.info("deleting %s", filename)
			self.delete_push_mms(filename)
			#self.liststore.remove(miter)
		dialog.destroy()
		self.refreshlistview = True
		return
	

	""" long press on image creates this """
	def liststore_mms_menu(self):
		menu = gtk.Menu()
		menu.set_property("name", "hildon-context-sensitive-menu")

		openItem = gtk.MenuItem("Delete")
		menu.append(openItem)
		openItem.connect("activate", self.liststore_delete_clicked)
		openItem.show()
		
		menu.show_all()
		return menu


	""" show the selected mms """		
	def show_mms(self, treeview, path):
		# Show loading indicator
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		log.info("showing mms: %s", path)
		model = treeview.get_model()
		miter = model.get_iter(path)
		# the 4th value is the transactionid (start counting at 0)
		transactionid = model.get_value(miter, 3)
		
		try:
			viewer = fMMSViewer.fMMS_Viewer(transactionid)
		except Exception, e:
			log.exception("%s %s", type(e), e)
			#raise
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		self.refreshlistview = True


	def run(self):
		self.window.show_all()
		gtk.main()
				
if __name__ == "__main__":
	app = fMMS_GUI()
	app.run()