#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" GUI.

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
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
import fmms_config_dialog as fMMSConfigDialog
import controller as fMMSController
import contacts as ContactH

import logging
log = logging.getLogger('fmms.%s' % __name__)

class fMMS_GUI(hildon.Program):
	""" GUI class for the application. """

	def __init__(self):
		""" Initializes the GUI, creating all widgets. """
		self.cont = fMMSController.fMMS_controller()
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self.ch = ContactH.ContactHandler()
		
		self.osso_c = osso.Context("se.frals.fmms", self.config.get_version(), False)
		self.osso_rpc = osso.Rpc(self.osso_c)
		self.osso_rpc.set_rpc_callback("se.frals.fmms","/se/frals/fmms","se.frals.fmms", self.cb_open_fmms, self.osso_c)
		
		self.refreshlistview = True
		
		self.avatarlist = {}
		self.namelist = {}
	
		if not os.path.isdir(self._mmsdir):
			log.info("creating dir %s", self._mmsdir)
			os.makedirs(self._mmsdir)
		if not os.path.isdir(self._pushdir):
			log.info("creating dir %s", self._pushdir)
			os.makedirs(self._pushdir)
	
		hildon.Program.__init__(self)
		program = hildon.Program.get_instance()
			
		self.window = hildon.StackableWindow()
		gtk.set_application_name("fMMS")
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


	def take_ss(self):
		""" Takes a screenshot of the application used by hildon to show while loading.

		inspired by Andrew Flegg and WimpWorks.
		@see http://maemo.org/api_refs/5.0/5.0-final/hildon/hildon-Additions-to-GTK+.html#hildon-gtk-window-take-screenshot 
		"""
		if os.path.isfile("/home/user/.cache/launch/se.frals.fmms.pvr"):
			gobject.timeout_add(10, hildon.hildon_gtk_window_take_screenshot, self.window, False)
		
		gobject.timeout_add(10, hildon.hildon_gtk_window_take_screenshot, self.window, True)


	def cb_button_press(self, widget, event):
		""" Used to keep track of the current selection in the treeview. """
		try:
			(self.curPath, tvcolumn, x, y) = self.treeview.get_path_at_pos(int(event.x), int(event.y))
		except:
			self.curPath = None
		return False


	def cb_on_focus(self, widget, event):
		""" Checks if the listview needs to be refreshed and takes screenshot. """
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
						firstlaunchmessage = "NOTE: Read the thread on talk.maemo.org."
						note = hildon.hildon_note_new_information(self.window, firstlaunchmessage)
						dialog = fMMSConfigDialog.fMMS_ConfigDialog(self.window)
						self.config.set_firstlaunch(0)
						note.run()
						note.destroy()
						
			self.take_ss()
			
		return True


	def cb_open_fmms(self, interface, method, args, user_data):
		""" Determines what action should be done when a dbus-call is made. """
		if method == 'open_mms':
			filename = args[0]
			self.refreshlistview = True
			if self.cont.is_fetched_push_by_transid(filename):
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
				self.force_ui_update()
				viewer = fMMSViewer.fMMS_Viewer(filename)
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
				return
			else:
				return
		elif method == 'open_gui':
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
		else:
			return
		
	def create_menu(self):
		""" Creates the application menu. """
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
		""" Determine what button was clicked in the app menu. """
		buttontext = button.get_label()
		if buttontext == "Configuration":
			dialog = fMMSConfigDialog.fMMS_ConfigDialog(self.window)
		elif buttontext == "About":
			ret = self.create_about_dialog()
	
	def new_mms_button_clicked(self, button):
		""" Fired when the 'New MMS' button is clicked. """
		self.refreshlistview = True
		ret = fMMSSenderUI.fMMS_SenderUI(self.window).run()
		
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

	def add_buttons_liststore(self):
		""" Adds all messages to the liststore. """
		icon_theme = gtk.icon_theme_get_default()

		pushlist = self.cont.get_push_list()

		primarytxt = self.cont.get_primary_font().to_string()
		primarycolor = self.cont.get_primary_color().to_string()
		highlightcolor = self.cont.get_active_color().to_string()
		secondarytxt = self.cont.get_secondary_font().to_string()
		secondarycolor = self.cont.get_secondary_color().to_string()
		
		replied_icon = icon_theme.load_icon("chat_replied_sms", 48, 0)
		read_icon = icon_theme.load_icon("general_sms", 48, 0)
		unread_icon = icon_theme.load_icon("chat_unread_sms", 48, 0)
		default_avatar = icon_theme.load_icon("general_default_avatar", 48, 0)
		
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

			# TODO: cleanup
			senderuid = self.ch.get_uid_from_number(sender)
			avatar = default_avatar

			if senderuid != None:
				sendertest = self.namelist.get(senderuid, '')
				if sendertest == '':
					sender = self.ch.get_displayname_from_uid(senderuid)
				else:
					sender = sendertest
				
				avatartest = self.avatarlist.get(senderuid, '')
				if avatartest == '':
					avatartest = self.ch.get_photo_from_uid(senderuid, 48)
				if avatartest != None:
					avatar = avatartest
				
				self.namelist[senderuid] = sender
				self.avatarlist[senderuid] = avatar

			if direction == fMMSController.MSG_DIRECTION_OUT:
				icon = replied_icon
			elif self.cont.is_fetched_push_by_transid(fname) and isread:
				icon = read_icon
			else:
				icon = unread_icon

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
			self.liststore.append([icon, stringline, avatar, fname, sender])

	def quit(self, *args):
		""" Quits the application. """
		gtk.main_quit()
	
	def force_ui_update(self):
		""" Force a UI update if events are pending. """
		while gtk.events_pending():
			gtk.main_iteration(False)
		
	def delete_push(self, fname):
		""" Deletes the given push message. """
		self.cont.delete_push_message(fname)
		
	def delete_mms(self, fname):
		""" Deletes the given MMS message. """
		self.cont.delete_mms_message(fname)

	def delete_push_mms(self, fname):
		""" Deletes both the MMS and the PUSH message. """
		try:
			self.cont.wipe_message(fname)
			#banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Message deleted")
		except Exception, e:
			log.exception("%s %s", type(e), e)
			#raise
			banner = hildon.hildon_banner_show_information(self.window, "", "fMMS: Failed to delete message.")

	def liststore_delete_clicked(self, widget):
		""" Shows a confirm dialog when Delete menu is clicked.

		Deletes the message if the user accepts the dialog.

		"""
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
			self.liststore.remove(miter)
		dialog.destroy()
		return
	

	def liststore_mms_menu(self):
		""" Creates the context menu and shows it. """
		menu = gtk.Menu()
		menu.set_property("name", "hildon-context-sensitive-menu")

		openItem = gtk.MenuItem("Delete")
		menu.append(openItem)
		openItem.connect("activate", self.liststore_delete_clicked)
		openItem.show()
		
		menu.show_all()
		return menu

	def show_mms(self, treeview, path):
		""" Shows the message at the current selection in the treeview. """
		# Show loading indicator
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		log.info("showing mms: %s", path)
		model = treeview.get_model()
		miter = model.get_iter(path)
		# the 4th value is the transactionid (start counting at 0)
		transactionid = model.get_value(miter, 3)
		
		if not self.cont.is_mms_read(transactionid) and not self.cont.get_direction_mms(transactionid) == fMMSController.MSG_DIRECTION_OUT:
			self.refreshlistview = True
		
		try:
			viewer = fMMSViewer.fMMS_Viewer(transactionid, spawner=self)
		except Exception, e:
			log.exception("%s %s", type(e), e)
			#raise
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		
	def run(self):
		""" Run. """
		self.window.show_all()
		gtk.main()


if __name__ == "__main__":
	try:
		app = fMMS_GUI()
		app.run()
	except:
		log.exception("General failure.")
		raise