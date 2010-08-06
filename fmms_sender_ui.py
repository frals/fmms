#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Sender UI for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import os
import socket
import re
import Image
import gettext
from shutil import copy

import gtk
import hildon
import gobject
import osso
from gnome import gnomevfs

import contacts as ContactH
import controller_gtk as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

_ = gettext.gettext
gettext.bindtextdomain('fmms','/opt/fmms/share/locale/')
gettext.textdomain('fmms')


class fMMS_SenderUI(hildon.Program):
	def __init__(self, spawner=None, tonumber=None, withfile=None, subject=None, message=None):
		hildon.Program.__init__(self)
		program = hildon.Program.get_instance()
		
		self.ch = ContactH.ContactHandler()
		self.cont = fMMSController.fMMS_controllerGTK()
		self.config = self.cont.config
		self.subject = subject
		self.osso_c = osso.Context("fMMS", "1.0", False)
		
		self.window = hildon.StackableWindow()
		self.window.set_title(gettext.ldgettext('rtcom-messaging-ui', "messaging_ti_new_mms"))
		if subject:
			try:
				self.window.set_title(subject)
			except:
				pass
		program.add_window(self.window)
		
		self.window.connect("delete_event", self.quit)
		self.attachmentFile = ""
		
		draftfile = False
		if spawner != None:
			self.spawner = spawner
			(tonumber, message, tmpfn) = self.cont.get_draft()
			if tmpfn != "" and tmpfn != "None" and os.path.isfile(tmpfn):
				withfile = tmpfn
				self.attachmentFile = tmpfn
				draftfile = True
		else:
			self.spawner = self.window
		allBox = gtk.VBox()
		
		""" Begin top section """
		topHBox1 = gtk.HBox()
		
		bTo = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, \
				     gettext.ldgettext('rtcom-messaging-ui', "messaging_fi_new_sms_to"))
		bTo.connect('clicked', self.open_contacts_dialog)
		bTo.set_size_request(128, gtk.HILDON_SIZE_FINGER_HEIGHT)
		self.eNumber = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		if tonumber != None:
			self.eNumber.set_text(tonumber)
		
		self.bSend = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
		self.bSend.connect('clicked', self.send_mms_clicked)
		icon_theme = gtk.icon_theme_get_default()
		sendPixbuf = icon_theme.load_icon("email_message_send", 48, 0)
		sendImage = gtk.Image()
		sendImage.set_from_pixbuf(sendPixbuf)
		#sendImage.set_alignment(1, 0.5)
		self.bSend.set_image(sendImage)
		self.bSend.set_size_request(128, gtk.HILDON_SIZE_FINGER_HEIGHT)
		
		topHBox1.pack_start(bTo, False, True, 0)
		topHBox1.pack_start(self.eNumber, True, True, 5)
		topHBox1.pack_start(self.bSend, False, True, 0)
		
		
		""" Begin midsection """
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
		midBox = gtk.VBox()
		centerBox = gtk.HBox()
		self.imageBox = gtk.EventBox()
		self.imageBox.set_size_request(400, 200)
		
		self.imageBoxContent = gtk.Fixed()
		border = gtk.Image()
		border.set_from_file("/opt/fmms/dotted_border.png")
		addimglabel = gtk.Label(gettext.ldgettext('modest', "mcen_me_editor_attach_inlineimage"))
		addimglabel.set_justify(gtk.JUSTIFY_CENTER)
		addimglabel.set_size_request(300, 50)
		
		self.imageBoxContent.put(border, 0, 0)
		self.imageBoxContent.put(addimglabel, 50, 100)
		
		self.imageBox.add(self.imageBoxContent)
		self.imageBox.connect('button-press-event', self.open_file_dialog)
		
		centerBox.pack_start(self.imageBox, True, False, 0)

		self.tvMessage = hildon.TextView()
		self.tvMessage.set_property("name", "hildon-fullscreen-textview")
		self.tvMessage.set_wrap_mode(gtk.WRAP_WORD_CHAR)
		self.tvMessage.set_justification(gtk.JUSTIFY_LEFT)
		if message != None and message != '':
			tb = gtk.TextBuffer()
			tb.set_text(message)
			self.tvMessage.set_buffer(tb)
		
		midBox.pack_start(centerBox)
		midBox.pack_start(self.tvMessage)
		
		pan.add_with_viewport(midBox)
		
		# Copy the file to our tempdir in case sharing service removes it
		if withfile and not draftfile:
			filename = os.path.basename(withfile)
			dst = "%s/%s" % (self.config.get_imgdir(), filename)
			log.info("Copying file to: %s" % dst)
			copy(withfile, dst)
			self.attachmentFile = dst
			self.fromSharingService = True
			self.fromSharingFile = dst
		if withfile or draftfile:
			try:
				self.set_thumbnail(self.attachmentFile)
			except:
				log.exception("wtf: %s" % self.attachmentFile)

		""" Show it all! """
		allBox.pack_start(topHBox1, False, False)
		allBox.pack_start(pan, True, True)
		#allBox.pack_start(self.botHBox, False, False)
		
		align = gtk.Alignment(1, 1, 1, 1)
		align.set_padding(2, 2, 10, 10)		
		align.add(allBox)
		
		self.window.add(align)
		self.window.show_all()
		
		self.menu = self.cont.create_menu(self.window)
		self.window.set_app_menu(self.menu)
		
		self.add_window(self.window)
		
		# so appearently throwing an exception here
		# makes osso-abook always load the contacts...
		self.this_doesnt_exist()
	
	def open_contacts_dialog(self, button):
		invalue = self.ch.contact_chooser_dialog()
		if invalue:
			invalue = invalue.replace(" ", "")
			if not "@" in invalue:
				invalue = re.sub(r'[^\d|\+]+', '', invalue)
			self.eNumber.set_text(invalue)

	def force_ui_update(self):
		""" forces ui update, kinda... god this is AWESOME """
		while gtk.events_pending():
			gtk.main_iteration(False)	

	def set_thumbnail(self, filename):
		try:
			filetype = gnomevfs.get_mime_type(filename)
		except:
			filetype = "unknown"
		if filetype.startswith("image") or filetype.startswith("sketch"):
			im = Image.open(filename)
			im.thumbnail((256, 256), Image.NEAREST)
			pixbuf = self.cont.image2pixbuf(im)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)
		elif filetype.startswith("audio"):
			icon_theme = gtk.icon_theme_get_default()
			pixbuf = icon_theme.load_icon("mediaplayer_default_album", 128, 0)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)			
		elif filetype.startswith("video"):
			icon_theme = gtk.icon_theme_get_default()
			pixbuf = icon_theme.load_icon("general_video", 128, 0)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)
		else:
			icon_theme = gtk.icon_theme_get_default()
			pixbuf = icon_theme.load_icon("tasklaunch_file_manager", 128, 0)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)
		
		self.imageBox.remove(self.imageBoxContent)
		self.imageBoxContent = image
		self.imageBox.add(self.imageBoxContent)
		self.imageBox.show_all()
		return
		
	def open_file_dialog(self, button, data=None):
		# this shouldnt issue a warning according to the pymaemo mailing list, but does
		# anyway, nfc why :(
		#fcd = gobject.new(hildon.FileChooserDialog, self.window, action=gtk.FILE_CHOOSER_ACTION_OPEN)
		fcd = hildon.FileChooserDialog(self.window, gtk.FILE_CHOOSER_ACTION_OPEN)
		fcd.set_default_response(gtk.RESPONSE_OK)
		fcd.set_transient_for(self.window)
		folder = self.config.get_last_ui_dir()
		if folder:
			if os.path.isdir(folder):
				fcd.set_current_folder(folder)
		ret = fcd.run()
		if ret == gtk.RESPONSE_OK:
			### TODO: dont hardcode filesize check
			filesize = os.path.getsize(fcd.get_filename()) / 1024
			if filesize > 10240:
				errhelp = _("Attachment is too large (limit is %s)." % "10 MB")
				banner = hildon.hildon_banner_show_information(self.window, "", errhelp)
			else:
				self.attachmentFile = fcd.get_filename()
				self.set_thumbnail(self.attachmentFile)

			folder = fcd.get_current_folder()
			self.config.set_last_ui_dir(folder)
			fcd.destroy()
		else:
			fcd.destroy()
		return True
	
	def resize_img(self, filename):
		""" resize an image """
		""" thanks tomaszf for this function """
		""" slightly modified by frals """
		try:
			img = Image.open(filename)
			log.info("width %s", str(img.size[0]))
			log.info("height %s", str(img.size[1]))
			newWidth = int(self.config.get_img_resize_width())
			if img.size[0] > newWidth:
				newWidth = int(self.config.get_img_resize_width())
				newHeight = int(newWidth * img.size[1] / img.size[0])
				log.info("Resizing image: %s * %s", str(newWidth), str(newHeight))

				# Image.BILINEAR, Image.BICUBIC, Image.ANTIALIASING
				rimg = img.resize((newWidth, newHeight), Image.BILINEAR)
				filename = filename.rpartition("/")
				filename = filename[-1]
				rattachment = self.config.get_imgdir() + filename
				try:
					rimg.save(rattachment)
				except KeyError:
					try:
						mimetype = gnomevfs.get_mime_type(rattachment)
						extension = mimetype.rpartition("/")[2]
						rattachment = "%s.%s" % (rattachment, extension)
					except:
						log.exception("rimg.save filetype troubles")
						# we tried our best... lets just go with jpg!
						rattachment = "%s.jpg" % (rattachment)
					rimg.save(rattachment)
				self.attachmentIsResized = True
			else:
				rattachment = filename
				
			return rattachment
		
		except Exception, e:
			log.exception("resizer: %s %s", type(e), e)
			raise
	
	def send_mms_clicked(self, widget):
		# Disable send-button
		self.bSend.set_sensitive(False)
		self.force_ui_update()
		self.send_mms(widget)
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		self.bSend.set_sensitive(True)
		
	def show_system_note(self, msg):
		note = osso.SystemNote(self.osso_c)
		note.system_note_dialog(msg, 'notice')
	
	def send_mms(self, widget):
		""" sends the message (no shit?) """
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		to = self.eNumber.get_text()
		if not self.cont.validate_phonenumber_email(to) or to == "":
			self.show_system_note(gettext.ldgettext('rtcom-messaging-ui', "messaging_fi_smsc_invalid_chars"))
			return
		
		attachment = self.attachmentFile
		
		hildon.hildon_banner_show_information(self.window, "", \
							gettext.ldgettext('modest', "mcen_li_outbox_sending"))
		self.force_ui_update()
		
		if attachment == "" or attachment == None:
			attachment = None
			self.attachmentIsResized = False
		else:
			filetype = gnomevfs.get_mime_type(attachment)
			self.attachmentIsResized = False
			if self.config.get_img_resize_width() != 0 and filetype.startswith("image"):
				try:
					attachment = self.resize_img(attachment)
				except Exception, e:
					log.exception("resize failed: %s %s", type(e), e)
					errmsg = str(e.args)
					errstr = gettext.ldgettext('hildon-common-strings', "sfil_ni_operation_failed")
					self.show_system_note("%s\n%s" % (errstr, errmsg))
					raise
		
		to = self.eNumber.get_text()
		sender = self.config.get_phonenumber()
		tb = self.tvMessage.get_buffer()
		message = tb.get_text(tb.get_start_iter(), tb.get_end_iter())
		log.info("attachment: %s message: %s", attachment, message)

		(status, msg) = self.cont.send_mms(to, self.subject, message, attachment, sender)
		
		if status == 0:
			banner = hildon.hildon_banner_show_information(self.spawner, "", \
						 gettext.dngettext('modest', 'mcen_ib_message_sent', 'mcen_ib_messages_sent', 1))
		
			if self.attachmentIsResized == True:
				log.info("Removing temporary image: %s", attachment)
				os.remove(attachment)
			self.quit("clean")
			return
		elif status == -1:
			self.show_system_note(msg)
		
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		self.bSend.set_sensitive(True)

	def from_sharing_service(self):
		try:
			if self.fromSharingService:
				log.info("Removing fromsharingfile: %s", self.fromSharingFile)
				os.remove(self.fromSharingFile)
		except:
			pass

	def quit(self, args, *kargs):
		if args != "clean":
			to = self.eNumber.get_text()
			tb = self.tvMessage.get_buffer()
			message = tb.get_text(tb.get_start_iter(), tb.get_end_iter())
			self.cont.save_draft(to, message, "")
		else:
			self.cont.save_draft("", "", "")

		self.from_sharing_service()

		if self.window == self.spawner:		
			gtk.main_quit()
		else:
			self.window.destroy()

	def run(self):
		self.window.show_all()
		gtk.main()
		
if __name__ == "__main__":
	app = fMMS_SenderUI()
	app.run()