#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" GUI.

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os
import time
from cgi import escape

import gtk
import hildon
import osso
import gobject
import gettext

import controller_gtk as fMMSController
import contacts as ContactH
import fmms_config as fMMSconf

import logging
log = logging.getLogger('fmms.%s' % __name__)

_ = gettext.gettext
gettext.bindtextdomain('fmms','/opt/fmms/share/locale/')
gettext.textdomain('fmms')

class fMMS_GUI(hildon.Program):
	""" GUI class for the application. """

	def __init__(self):
		""" Initializes the GUI, creating all widgets. """
		self.cont = fMMSController.fMMS_controllerGTK()
		self.config = self.cont.config
		self.ch = ContactH.ContactHandler()
		
		self.osso_c = osso.Context("se.frals.fmms", self.config.get_version(), False)
		self.osso_rpc = osso.Rpc(self.osso_c)
		self.osso_rpc.set_rpc_callback("se.frals.fmms", "/se/frals/fmms", "se.frals.fmms", self.cb_open_fmms, self.osso_c)
		
		self.refreshlistview = True
		self.viewerimported = False
		self.senderimported = False
		
		self.avatarlist = {}
		self.namelist = {}
		self.nrlist = {}
	
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
		mmsLabel = gtk.Label(gettext.ldgettext('rtcom-messaging-ui', "messaging_ti_new_mms"))
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
	
		self.menu = self.cont.create_menu(self.window)
		self.window.set_app_menu(self.menu)
		
		self.window.connect('focus-in-event', self.cb_on_focus)
		
		self.window.show_all()
		self.add_window(self.window)

	def import_viewer(self):
		""" This is used to import viewer only when we need it
		    as its quite a hog """
		if not self.viewerimported:
			import fmms_viewer as fMMSViewer
			global fMMSViewer
			self.viewerimported = True

	def import_sender(self):
		""" This is used to import sender_ui only when we need it
		    as its quite a hog """
		if not self.senderimported:
			import fmms_sender_ui as fMMSSenderUI
			global fMMSSenderUI
			self.senderimported = True

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
			
			if self.config.get_firstlaunch() < 2:
				settings = self.config.get_apn_settings()
				if settings.get('apn', '') == '' or settings.get('mmsc', '') == '':
					auto = self.cont.get_apn_settings_automatically()
					self.config.set_apn_settings(auto)
					settings = self.config.get_apn_settings()
				if settings.get('apn', '') == '' or settings.get('mmsc', '') == '':
					self.cont.import_configdialog()
					self.cont.fMMSConfigDialog.fMMS_ConfigDialog(self.window)
				self.config.set_firstlaunch(2)
				log.info("Seems this is the first time we are running.")
				self.config.switcharoo()

			self.take_ss()

		return True


	def cb_open_fmms(self, interface, method, args, user_data):
		""" Determines what action should be done when a dbus-call is made. """
		if method == 'open_mms':
			filename = args[0]
			self.refreshlistview = True
			self.import_viewer()
			if self.cont.is_fetched_push_by_transid(filename):
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
				self.force_ui_update()
				fMMSViewer.fMMS_Viewer(filename)
				hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
				return
			else:
				return
		elif method == 'open_gui':
			return
		elif method == 'send_mms':
			log.info("launching sender with args: %s", args)
			self.refreshlistview = False
			self.import_sender()
			fMMSSenderUI.fMMS_SenderUI(tonumber=args[0]).run()
			return
		elif method == 'send_via_service':
			log.info("launching sendviaservice with args: %s", args)
			self.refreshlistview = False
			self.import_sender()
			fMMSSenderUI.fMMS_SenderUI(withfile=args[0], subject=args[1], message=args[2]).run()
			self.quit()
		else:
			return
			
	def new_mms_button_clicked(self, button):
		""" Fired when the 'New MMS' button is clicked. """
		self.refreshlistview = True
		self.import_sender()
		fMMSSenderUI.fMMS_SenderUI(self.window).run()
		
	def add_buttons_liststore(self):
		""" Adds all messages to the liststore. """
		icon_theme = gtk.icon_theme_get_default()

		pushlist = self.cont.get_push_list()

		#primarytxt = self.cont.get_primary_font().to_string()
		#primarycolor = self.cont.get_primary_color().to_string()
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

			isread = self.cont.is_mms_read(fname)

			if direction == fMMSController.MSG_DIRECTION_OUT:
				sender = self.cont.get_mms_headers(varlist['Transaction-Id'])
				sender = sender['To'].replace("/TYPE=PLMN", "")
			else:
				sender = varlist.get('From', '00000').replace("/TYPE=PLMN", "")

			sendernr = sender

			senderuid = self.nrlist.get(sender, -1)
			if senderuid == -1:
				senderuid = self.ch.get_uid_from_number(sender)
				self.nrlist[sender] = senderuid

			avatar = default_avatar
			# compare with -1 as thats invalid contactuid
			if senderuid != -1 and senderuid != None:
				sender = self.namelist.get(senderuid, None)
				if not sender:
					sender = self.ch.get_displayname_from_uid(senderuid)
				if not sender:
					sender = sendernr
				
				avatar = self.avatarlist.get(senderuid, None)
				if not avatar:
					avatar = self.ch.get_photo_from_uid(senderuid, 48)
					if not avatar:
						avatar = default_avatar

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
				description = headerlist['Description']
			except:
				description = varlist.get('Subject', '')

			description = description.decode('utf-8', 'ignore')
			primarytext = ' <span font_desc="%s" foreground="%s"><sup>%s</sup></span>' % (secondarytxt, secondarycolor, mtime)
			secondarytext = '\n<span font_desc="%s" foreground="%s">%s</span>' % (secondarytxt, secondarycolor, escape(description))
			if not isread and direction == fMMSController.MSG_DIRECTION_IN:
				sender = '<span foreground="%s">%s</span>' % (highlightcolor, escape(sender))
			else:
				sender = escape(sender)
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
		except Exception, e:
			log.exception("failed to delete push mms")
			hildon.hildon_banner_show_information(self.window, "", gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed"))

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
		
		confirmtxt = gettext.ldgettext('rtcom-messaging-ui', "messaging_fi_delete_1_sms")
		
		dialog = gtk.Dialog()
		dialog.set_transient_for(self.window)
		dialog.set_title(confirmtxt)
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		label = gtk.Label(confirmtxt)
		dialog.vbox.add(label)
		dialog.show_all()
		ret = dialog.run()
		if ret == 1:
			log.info("Deleting %s", filename)
			self.delete_push_mms(filename)
			self.liststore.remove(miter)
		dialog.destroy()
		hildon.hildon_gtk_window_take_screenshot(self.window, False)
		hildon.hildon_gtk_window_take_screenshot(self.window, True)
		self.force_ui_update()
		return
	
	def liststore_mms_menu(self):
		""" Creates the context menu and shows it. """
		menu = gtk.Menu()
		menu.set_property("name", "hildon-context-sensitive-menu")

		openItem = gtk.MenuItem(gettext.ldgettext('hildon-libs', "wdgt_bd_delete"))
		menu.append(openItem)
		openItem.connect("activate", self.liststore_delete_clicked)
		openItem.show()
		
		menu.show_all()
		return menu

	def show_mms(self, treeview, path):
		""" Shows the message at the current selection in the treeview. """
		self.treeview.set_sensitive(False)
		# Show loading indicator
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		log.info("showing mms: %s", path)
		model = treeview.get_model()
		miter = model.get_iter(path)
		# the 4th value is the transactionid (start counting at 0)
		transactionid = model.get_value(miter, 3)
		
		switch = False
		if not self.cont.is_fetched_push_by_transid(transactionid) and self.config.get_connmode() == fMMSconf.CONNMODE_ICDSWITCH:
			if not self.cont.get_current_connection_iap_id() == self.config.get_apn():
				switch = self.show_switch_conn_dialog()
		
		if switch:
			self.cont.disconnect_current_connection()
		#if not self.cont.is_mms_read(transactionid) and not self.cont.get_direction_mms(transactionid) == fMMSController.MSG_DIRECTION_OUT:
			#self.refreshlistview = True
		
		self.import_viewer()
		try:
			fMMSViewer.fMMS_Viewer(transactionid, spawner=self)
		except Exception, e:
			log.exception("Failed to open viewer with transaction id: %s" % transactionid)
			#raise
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		self.treeview.set_sensitive(True)

	def show_switch_conn_dialog(self):
		""" Show confirmation dialog asking if we should disconnect """
		self.refreshlistview = False
		dialog = gtk.Dialog()
		dialog.set_title(gettext.ldgettext('osso-connectivity-ui', 'conn_mngr_me_int_conn_change_iap'))
		dialog.set_transient_for(self.window)
		label = gtk.Label(_("To retrieve the MMS your active connection will need to change. Switch connection?"))
		label.set_line_wrap(True)
		dialog.vbox.add(label)
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		dialog.vbox.show_all()
		ret = dialog.run()
		switch = False
		if ret == 1:
			switch = True
		dialog.destroy()
		self.force_ui_update()
		return switch
		
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