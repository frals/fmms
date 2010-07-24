#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Message-viewer UI for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os
import sys
import gettext

import gtk
import hildon
import gobject
import osso
from gnome import gnomevfs
import Image

import controller_gtk as fMMSController
import fmms_sender_ui as fMMSSenderUI
import contacts as ContactH

import logging
log = logging.getLogger('fmms.%s' % __name__)

_ = gettext.gettext
gettext.bindtextdomain('fmms','/opt/fmms/share/locale/')
gettext.textdomain('fmms')


class fMMS_Viewer(hildon.Program):

	def __init__(self, fname, standalone=False, spawner=None):
		self.cont = fMMSController.fMMS_controllerGTK()
		self.ch = ContactH.ContactHandler()
		self.standalone = standalone
		self.config = self.cont.config
		self._mmsdir = self.config.get_mmsdir()
		self._pushdir = self.config.get_pushdir()
		self._outdir = self.config.get_outdir()
		self.osso_c = osso.Context("se.frals.fmms_ui", self.config.get_version(), False)
		self.spawner = spawner
		
		self.window = hildon.StackableWindow()
		self.window.set_title("MMS")
		self.window.connect("delete_event", self.quit)
		
		vbox = gtk.VBox()
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)

		self._direction = self.cont.get_direction_mms(fname)

		self._parse_mms(fname, vbox)

		pan.add_with_viewport(vbox)
		
		align = gtk.Alignment(1, 1, 1, 1)
		align.set_padding(2, 2, 10, 10)
		align.add(pan)
		self.window.add(align)

		if not self.cont.is_mms_read(fname) and self._direction == fMMSController.MSG_DIRECTION_IN:
			self.cont.mark_mms_read(fname)
			if self.spawner:
				self.spawner.refreshlistview = True

		mms_menu = self.create_mms_menu(fname)
		self.window.set_app_menu(mms_menu)
		self.window.show_all()
	
	def quit(self, *args):
		""" lets call it quits! """
		self.window.destroy()
		if self.standalone == True:
			gtk.main_quit()
	
	def force_ui_update(self):
		""" forces ui update, kinda... god this is AWESOME """
		while gtk.events_pending():
			gtk.main_iteration(False)
				
	def create_mms_menu(self, fname):
		""" create app menu for mms viewing window """
		menu = hildon.AppMenu()
		
		self.headerstxt = _("Headers")
		headers = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		headers.set_label(self.headerstxt)
		headers.connect('clicked', self.mms_menu_button_clicked, fname)
		
		self.replytxt = gettext.ldgettext('skype-ui', 'skype_ti_incoming_call_options')
		reply = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		reply.set_label(self.replytxt)
		reply.connect('clicked', self.mms_menu_button_clicked, fname)
		
		self.replysmstxt = "%s (%s)" % (gettext.ldgettext('skype-ui', 'skype_ti_incoming_call_options'), "SMS")
		replysms = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		replysms.set_label(self.replysmstxt)
		replysms.connect('clicked', self.mms_menu_button_clicked, fname)
		
		self.forwardtxt = gettext.ldgettext('rtcom-messaging-ui', 'messaging_fi_forward')
		forward = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		forward.set_label(self.forwardtxt)
		forward.connect('clicked', self.mms_menu_button_clicked, fname)
		
		self.copytxt = "%s (%s)" % (gettext.ldgettext('rtcom-messaging-ui', 'messaging_fi_copy'), "Text")
		copyb = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		copyb.set_label(self.copytxt)
		copyb.connect('clicked', self.mms_menu_button_clicked, fname)
		
		self.deletetxt = gettext.ldgettext('hildon-libs', 'wdgt_bd_delete')
		delete = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
		delete.set_label(self.deletetxt)
		delete.connect('clicked', self.mms_menu_button_clicked, fname)
		
		menu.append(reply)
		menu.append(replysms)
		menu.append(forward)
		menu.append(copyb)
		menu.append(headers)
		menu.append(delete)
		menu.show_all()
		
		return menu		
	
	def delete_dialog(self, filename):
		dialog = gtk.Dialog()
		confirmtxt = gettext.ldgettext('rtcom-messaging-ui', "messaging_fi_delete_1_sms")
		dialog.set_title(confirmtxt)
		dialog.add_button(gtk.STOCK_YES, 1)
		dialog.add_button(gtk.STOCK_NO, 0)
		label = gtk.Label(confirmtxt)
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
	
	def delete_push_mms(self, fname):
		""" delete push & mms """
		log.info("deleting message: %s", fname)
		try:
			self.cont.wipe_message(fname)
			#banner = hildon.hildon_banner_show_information(self.window, "", "Message deleted")
			self.force_ui_update()
			self.window.destroy()
		except Exception, e:
			log.exception("%s %s", type(e), e)
			banner = hildon.hildon_banner_show_information(self.window, "", \
					gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed"))

	def mms_menu_button_clicked(self, button, fname):
		""" actions for mms menu """
		buttontext = button.get_label()
		if buttontext == self.headerstxt:
			ret = self.create_headers_dialog(fname)
		elif buttontext == self.replytxt:
			number = self.cont.get_replyuri_from_transid(fname)
			fMMSSenderUI.fMMS_SenderUI(spawner=self.window, tonumber=number).run()
		elif buttontext == self.replysmstxt:
			number = self.cont.get_replyuri_from_transid(fname)
			if "@" in number:
				note = osso.SystemNote(self.osso_c)
				note.system_note_dialog(gettext.ldgettext('rtcom-messaging-ui', "messaging_fi_smsc_invalid_chars") , 'notice')
			else:
				rpc = osso.Rpc(self.osso_c)
				nr = "sms:%s" % str(number)
				args = (nr, "")
				rpc.rpc_run('com.nokia.MessagingUI', '/com/nokia/MessagingUI', 'com.nokia.MessagingUI', 'messaging_ui_interface_start_sms', args, True, True)
		elif buttontext == self.forwardtxt:
			tbuffer = self.textview.get_buffer()
			msg = tbuffer.get_text(tbuffer.get_start_iter(), tbuffer.get_end_iter())
			fn = self.attachment
			fMMSSenderUI.fMMS_SenderUI(spawner=self.window, withfile=fn, message=msg)
		elif buttontext == self.deletetxt:
			self.delete_dialog(fname)
		elif buttontext == self.copytxt:
			clip = gtk.Clipboard(display=gtk.gdk.display_get_default(), selection="CLIPBOARD")
			tbuffer = self.textview.get_buffer()
			msg = tbuffer.get_text(tbuffer.get_start_iter(), tbuffer.get_end_iter())
			clip.set_text(msg, -1)
			
	def create_headers_dialog(self, fname):
		""" show headers in a dialog """
		dialog = gtk.Dialog()
		dialog.set_title(self.headerstxt)
		
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
	
	def _parse_mms(self, filename, container):
		""" parse mms and push each part to the container 
		    fetches the mms if its not downloaded         """
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		if not self.cont.is_fetched_push_by_transid(filename):
			msgstr = gettext.ldgettext('hildon-application-manager', "ai_nw_downloading") % "MMS"
			banner = hildon.hildon_banner_show_information(self.window, "", msgstr)
			self.force_ui_update()
			self.cont.get_mms_from_push(filename)
			self.cont.mark_mms_read(filename)
				

		headerlist = self.cont.get_mms_headers(filename)

		topbox = gtk.HBox()
		
		if self._direction == fMMSController.MSG_DIRECTION_IN:
			label = gtk.Label('<span foreground="#666666">%s</span>' \
					  % gettext.ldgettext('modest', 'mail_va_from'))
			sender = headerlist.get('From', "0").replace("/TYPE=PLMN", "")
		else:
			label = gtk.Label('<span foreground="#666666">%s</span>' \
					  % gettext.ldgettext('rtcom-messaging-ui', 'messaging_fi_new_sms_to'))
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

		topbox.pack_start(label, False, False, 0)
		topbox.pack_start(namelabel, True, True, 10)
		topbox.pack_end(timelabel, False, False, 0)
		
		container.pack_start(topbox, False, False, 5)
		sep = gtk.HSeparator()
		container.pack_start(sep, False, False, 0)
		# TODO: add correct padding to first item in next container
				
		self.textview = hildon.TextView()
		self.textview.set_property("name", "hildon-readonly-textview")
		self.textview.set_editable(False)
		self.textview.set_cursor_visible(False)
		self.textview.set_wrap_mode(gtk.WRAP_WORD)
		self.textview.set_justification(gtk.JUSTIFY_LEFT)
		textbuffer = gtk.TextBuffer()
		direction = self.cont.get_direction_mms(filename)
		
		if direction == fMMSController.MSG_DIRECTION_OUT:
			path = self._outdir + filename
		else:
			path = self.cont.get_filepath_for_mms_transid(filename)
		
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
					if filetype.startswith("text") and not "x-vcard" in filetype:
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
		
	def mms_img_clicked(self, widget, data):
		""" action on click on image/button """
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
			elif "vcard" in file_mimetype:
				rpc = osso.Rpc(self.osso_c)
				ret = rpc.rpc_run("com.nokia.osso_addressbook", "/com/nokia/osso_addressbook", "com.nokia.osso_addressbook", "mime_open", (str, path))
		else:
			# TODO: how to solve this?
			# move .mms to ~/MyDocs? change button to copy file to ~/MyDocs?
			#rpc = osso.Rpc(self.osso_c)
			#path = os.path.dirname(path).replace("file://", "")
			log.info("path %s", str(path))
			#rpc.rpc_run("com.nokia.osso_filemanager", "/com/nokia/osso_filemanager", "com.nokia.osso_filemanager", "open_folder", (str, path))

	def mms_img_menu(self, data=None):
		""" long press on image creates this """
		menu = gtk.Menu()
		menu.set_property("name", "hildon-context-sensitive-menu")

		openItem = gtk.MenuItem(gettext.ldgettext('hildon-fm', 'ckdg_ti_open_file'))
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