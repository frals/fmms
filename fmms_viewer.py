#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Message-viewer UI for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import os
import sys

import gtk
import hildon
import gobject
import osso
from gnome import gnomevfs
import dbus

from wappushhandler import PushHandler
import fmms_config as fMMSconf
import controller as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

class fMMS_Viewer(hildon.Program):

	def __init__(self, fname, standalone=False):
		self.cont = fMMSController.fMMS_controller()
		self.standalone = standalone
		self.config = fMMSconf.fMMS_config()
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._outdir = self.config.get_outdir()
		self.osso_c = osso.Context("fMMS", "0.1.0", False)
		
		self.window = hildon.StackableWindow()
		self.window.set_title("Showing MMS: " + fname)
		self.window.connect("delete_event", self.quit)
		
		vbox = gtk.VBox()
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)

		self._parse_mms(fname, vbox)

		pan.add_with_viewport(vbox)
		self.window.add(pan)

		if not self.cont.is_mms_read(fname) and self.cont.get_direction_mms(fname) == fMMSController.MSG_DIRECTION_IN:
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
		
		menu.append(headers)
	
		menu.show_all()
		
		return menu		
	
	""" actions for mms menu """
	def mms_menu_button_clicked(self, button, fname):
		buttontext = button.get_label()
		if buttontext == "Headers":
			ret = self.create_headers_dialog(fname)

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
			self.cont.get_mms_from_push(filename)
				
		textview = gtk.TextView()
		textview.set_editable(False)
		textview.set_cursor_visible(False)
		textview.set_wrap_mode(gtk.WRAP_WORD)
		textbuffer = gtk.TextBuffer()
		direction = self.cont.get_direction_mms(filename)
		if direction == fMMSController.MSG_DIRECTION_OUT:
			path = self._outdir + filename
		else:
			path = self._mmsdir + filename
		filelist = self.cont.get_mms_attachments(filename)
		log.info("filelist: %s", filelist)
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
				img.set_from_file(path + "/" + fname)
				fullpath = path + "/" + fname
				ebox.add(img)
				## TODO: make this menu proper without this ugly
				# args passing
				menu = self.mms_img_menu(fullpath)
				ebox.tap_and_hold_setup(menu)
				container.add(ebox)
			elif isText or ext.startswith(".txt"):
				fp = open(path + "/" + fname, 'r')
				contents = fp.read()
				fp.close()
				textbuffer.insert(textbuffer.get_end_iter(), contents)
			elif name != "message" and name != "headers" and not ext.startswith(".smil") and filetype != "application/smil":
				attachButton = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, fname)
				attachButton.connect('clicked', self.mms_img_clicked, fnpath)
				container.pack_end(attachButton, False, False, 0)
				
		textview.set_buffer(textbuffer)
		container.add(textview)
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
				self.osso_c = osso.Context("fMMSViewer", "0.3", False)
				rpc = osso.Rpc(self.osso_c)
				rpc.rpc_run("com.nokia.mediaplayer", "/com/nokia/mediaplayer", "com.nokia.mediaplayer", "mime_open", (str, path))	
			elif file_mimetype.startswith("image"):
				self.osso_c = osso.Context("fMMSViewer", "0.3", False)
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
		menu.set_title("hildon-context-sensitive-menu")

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