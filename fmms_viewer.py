#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Message-viewer UI for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os
import sys
import time

import gtk
import hildon
import gobject
import osso
from gnome import gnomevfs
import dbus
import Image

from wappushhandler import PushHandler
import fmms_config as fMMSconf
import controller as fMMSController
import fmms_sender_ui as fMMSSenderUI
import contacts as ContactH
import dbhandler as DBHandler

import logging
log = logging.getLogger('fmms.%s' % __name__)

class fMMS_Viewer(hildon.Program):

	def __init__(self, fname, standalone=False, spawner=None):
		self.cont = fMMSController.fMMS_controller()
		self.ch = ContactH.ContactHandler()
		self.standalone = standalone
		self.config = fMMSconf.fMMS_config()
		self.store = DBHandler.DatabaseHandler()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._outdir = self.config.get_outdir()
		self.osso_c = osso.Context("se.frals.fmms_ui", self.config.get_version(), False)
		self.spawner = spawner
		
		self.window = hildon.StackableWindow()
		self.window.set_title("Showing MMS")
		self.window.connect("delete_event", self.quit)
		
		vbox = gtk.VBox()
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)

		self._direction = self.cont.get_direction_mms(fname)

		self._parse_mms(fname, vbox)

		pan.add_with_viewport(vbox)
		self.window.add(pan)

		if not self.cont.is_mms_read(fname) and self._direction == fMMSController.MSG_DIRECTION_IN:
			self.cont.mark_mms_read(fname)

		mms_menu = self.create_mms_menu(fname)
		self.window.set_app_menu(mms_menu)
		self.window.show_all()
	
	""" lets call it quits! """
	def quit(self, *args):
		self.window.destroy()
		if self.standalone == True:
			gtk.main_quit()
	
	""" forces ui update, kinda... god this is AWESOME """
	def force_ui_update(self):
		while gtk.events_pending():
			gtk.main_iteration(False)
				
	""" create app menu for mms viewing window """
	def create_mms_menu(self, fname):
		menu = hildon.AppMenu()
		
		headers = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		headers.set_label("Headers")
		headers.connect('clicked', self.mms_menu_button_clicked, fname)
		
		reply = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		reply.set_label("Reply")
		reply.connect('clicked', self.mms_menu_button_clicked, fname)
		
		forward = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		forward.set_label("Forward")
		forward.connect('clicked', self.mms_menu_button_clicked, fname)
		
		delete = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		delete.set_label("Delete")
		delete.connect('clicked', self.mms_menu_button_clicked, fname)
		
		menu.append(reply)
		menu.append(forward)
		menu.append(headers)
		menu.append(delete)
	
		menu.show_all()
		
		return menu		
	
	
	def delete_dialog(self, filename):
		dialog = gtk.Dialog()
		dialog.set_title("Confirm")
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		label = gtk.Label("Are you sure you want to delete the message?")
		dialog.vbox.add(label)
		dialog.show_all()
		ret = dialog.run()
		if ret == 1:
			hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
			self.force_ui_update()
			log.info("deleting %s", filename)
			if self.spawner:
				self.spawner.refreshlistview = True
			self.force_ui_update()
			self.delete_push_mms(filename)
		dialog.destroy()
	
	""" delete push & mms """
	def delete_push_mms(self, fname):
		log.info("deleting message: %s", fname)
		try:
			self.cont.wipe_message(fname)
			#banner = hildon.hildon_banner_show_information(self.window, "", "Message deleted")
			self.force_ui_update()
			self.window.destroy()
		except Exception, e:
			log.exception("%s %s", type(e), e)
			banner = hildon.hildon_banner_show_information(self.window, "", "Failed to delete message.")

	""" actions for mms menu """
	def mms_menu_button_clicked(self, button, fname):
		buttontext = button.get_label()
		if buttontext == "Headers":
			ret = self.create_headers_dialog(fname)
		elif buttontext == "Reply":
			number = self.cont.get_replyuri_from_transid(fname)
			fMMSSenderUI.fMMS_SenderUI(spawner=self.window, tonumber=number).run()
		elif buttontext == "Forward":
			tbuffer = self.textview.get_buffer()
			msg = tbuffer.get_text(tbuffer.get_start_iter(), tbuffer.get_end_iter())
			fn = self.attachment
			fMMSSenderUI.fMMS_SenderUI(spawner=self.window, withfile=fn, message=msg)
		elif buttontext == "Delete":
			self.delete_dialog(fname)

	""" show headers in a dialog """
	def create_headers_dialog(self, fname):
		dialog = gtk.Dialog()
		dialog.set_title("Headers")
		
		dialogVBox = gtk.VBox()
		
		pan = hildon.PannableArea()
		pan.set_property("size-request-policy", hildon.SIZE_REQUEST_CHILDREN)
		
		allVBox = gtk.VBox()
		headerlist = self.cont.get_mms_headers(fname)
		for line in headerlist:
			hbox = gtk.HBox()
			titel = gtk.Label(line)
			titel.set_alignment(0, 0)
			titel.set_width_chars(18)
			label = gtk.Label(headerlist[line])
			label.set_line_wrap(True)
			label.set_alignment(0, 0)
			hbox.pack_start(titel, False, False, 0)
			hbox.pack_start(label, False, False, 0)
			allVBox.pack_start(hbox)

		allVBox.show_all()
		
		pan.add_with_viewport(allVBox)
		dialog.vbox.add(pan)
		dialog.vbox.show_all()
		ret = dialog.run()
		
		dialog.destroy()
		return ret
	
	""" parse mms and push each part to the container 
	    fetches the mms if its not downloaded         """
	def _parse_mms(self, filename, container):
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		if not self.cont.is_fetched_push_by_transid(filename):
			banner = hildon.hildon_banner_show_information(self.window, "", "Trying to download MMS...")
			self.force_ui_update()
			self.cont.get_mms_from_push(filename)
			self.cont.mark_mms_read(filename)
				

		headerlist = self.cont.get_mms_headers(filename)

		topbox = gtk.HBox()
		
		if self._direction == fMMSController.MSG_DIRECTION_IN:
			label = gtk.Label('<span foreground="#666666">From</span>')
			sender = headerlist.get('From', "0").replace("/TYPE=PLMN", "")
		else:
			label = gtk.Label('<span foreground="#666666">To</span>')
			sender = headerlist['To'].replace("/TYPE=PLMN", "")
		
		label.set_use_markup(True)
		label.set_alignment(0, 0.5)

		senderuid = self.ch.get_uid_from_number(sender)
		sendername = self.ch.get_displayname_from_uid(senderuid)
		if sendername != None:
			sender = sendername

		self.window.set_title("MMS - " + str(sender))

		namelabel = gtk.Label(sender)
                namelabel.set_alignment(0, 0.5)

                mtime = headerlist['Time']
		mtime = self.cont.convert_timeformat(mtime, "%Y-%m-%d | %H:%M")
					
                timestring = '<span foreground="#666666">' + mtime + "</span>"
                timelabel = gtk.Label(timestring)
                timelabel.set_use_markup(True)
                timelabel.set_alignment(1, 0.5)
                
		topbox.pack_start(label, False, False, 20)
		topbox.pack_start(namelabel, True, True, 0)
		topbox.pack_end(timelabel, False, False, 10)
		
		container.pack_start(topbox, False, False, 5)
		sep = gtk.HSeparator()
		container.pack_start(sep, False, False, 0)
		# TODO: add correct padding to first item in next container
				
		self.textview = gtk.TextView()
		self.textview.set_editable(False)
		self.textview.set_cursor_visible(False)
		self.textview.set_wrap_mode(gtk.WRAP_WORD)
		self.textview.set_justification(gtk.JUSTIFY_CENTER)
		black = gtk.gdk.Color(red=0, green=0, blue=0)
		self.textview.modify_base(gtk.STATE_NORMAL, black)
		self.textview.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
		textbuffer = gtk.TextBuffer()
		direction = self.cont.get_direction_mms(filename)
		
		# TODO: get path from db instead
		if direction == fMMSController.MSG_DIRECTION_OUT:
			path = self._outdir + filename
		else:
			path = self.store.get_filepath_for_mms_transid(filename).replace("/message", "")
		
		filelist = self.cont.get_mms_attachments(filename)
		log.info("filelist: %s", filelist)
		self.attachment = None
		for fname in filelist:
			(name, ext) = os.path.splitext(fname)
			fnpath = os.path.join(path, fname)
			isText = False
			isImage = False
			try:
				filetype = gnomevfs.get_mime_type(fnpath)
				log.info("filetype: %s", filetype)
				if filetype != None:
					if filetype.startswith("image") or filetype.startswith("sketch"):
						isImage = True
					if filetype.startswith("text"):
						isText = True
			except Exception, e:
				filetype = None
				log.exception("%s %s", type(e), e)
			
			if isImage or ext == ".wbmp":
				""" insert the image in an eventbox so we can get signals """
				ebox = gtk.EventBox()
				img = gtk.Image()
				#img.set_from_file(path + "/" + fname)
				fullpath = "%s/%s" % (path, fname)
				im = Image.open(fnpath)
				im.thumbnail((384, 384), Image.NEAREST)
				pixbuf = self.cont.image2pixbuf(im)
				img = gtk.Image()
				img.set_from_pixbuf(pixbuf)
				ebox.add(img)
				menu = self.mms_img_menu(fullpath)
				ebox.tap_and_hold_setup(menu)
				container.add(ebox)
				self.attachment = fnpath
			elif isText or ext.startswith(".txt"):
				fp = open(path + "/" + fname, 'r')
				contents = fp.read()
				fp.close()
				textbuffer.insert(textbuffer.get_end_iter(), contents)
			elif name != "message" and name != "headers" and not ext.startswith(".smil") and filetype != "application/smil":
				self.attachment = fnpath
				attachButton = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, fname)
				attachButton.connect('clicked', self.mms_img_clicked, fnpath)
				container.pack_end(attachButton, False, False, 0)
				
		self.textview.set_buffer(textbuffer)
		container.pack_start(self.textview)
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		
		
	""" action on click on image/button """
	def mms_img_clicked(self, widget, data):
		log.info("img clicked: %s", data)
		path = str("file://" + data)
		# gnomevfs seems to be better than mimetype when guessing mimetype for us
		file_mimetype = gnomevfs.get_mime_type(path)
		log.info("path: %s", path)
		log.info("mimetype: %s", file_mimetype)
		if file_mimetype != None:
			if file_mimetype.startswith("video") or file_mimetype.startswith("audio"):
				rpc = osso.Rpc(self.osso_c)
				rpc.rpc_run("com.nokia.mediaplayer", "/com/nokia/mediaplayer", "com.nokia.mediaplayer", "mime_open", (str, path))	
			elif file_mimetype.startswith("image"):
				rpc = osso.Rpc(self.osso_c)
				ret = rpc.rpc_run("com.nokia.image_viewer", "/com/nokia/image_viewer", "com.nokia.image_viewer", "mime_open", (str, path))
		else:
			# TODO: how to solve this?
			# move .mms to ~/MyDocs? change button to copy file to ~/MyDocs?
			#rpc = osso.Rpc(self.osso_c)
			#path = os.path.dirname(path).replace("file://", "")
			log.info("path %s", str(path))
			#rpc.rpc_run("com.nokia.osso_filemanager", "/com/nokia/osso_filemanager", "com.nokia.osso_filemanager", "open_folder", (str, path))


	""" long press on image creates this """
	def mms_img_menu(self, data=None):
		menu = gtk.Menu()
		menu.set_property("name", "hildon-context-sensitive-menu")

		openItem = gtk.MenuItem("Open")
		menu.append(openItem)
		openItem.connect("activate", self.mms_img_clicked, data)
		openItem.show()
		menu.show_all()
		return menu

	def run(self):
		self.window.show_all()
		gtk.main()
		
if __name__ == "__main__":
	app = fMMS_Viewer(sys.argv[1], True)
	app.run()