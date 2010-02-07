#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Sender UI for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import os
import time
import socket
import re
import Image
import mimetypes

import gtk
import hildon
import gobject
import osso
import dbus

from wappushhandler import MMSSender
import fmms_config as fMMSconf
import contacts as ContactH
import controller as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

class fMMS_SenderUI(hildon.Program):
	def __init__(self, spawner=None, tonumber=None):
		hildon.Program.__init__(self)
		program = hildon.Program.get_instance()
		
		self.config = fMMSconf.fMMS_config()
		self.ch = ContactH.ContactHandler()
		self.cont = fMMSController.fMMS_controller()
		
		self.window = hildon.StackableWindow()
		self.window.set_title("fMMS - New MMS")
		program.add_window(self.window)
		
		self.window.connect("delete_event", self.quit)
		
		if spawner != None:
			self.spawner = spawner
		else:
			self.spawner = self.window
		allBox = gtk.VBox()
		
		""" Begin top section """
		topHBox1 = gtk.HBox()
		
		bTo = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, "     To     ")
		bTo.connect('clicked', self.open_contacts_dialog)
		self.eNumber = hildon.Entry(gtk.HILDON_SIZE_FINGER_HEIGHT)
		if tonumber != None:
			self.eNumber.set_text(tonumber)
		
		topHBox1.pack_start(bTo, False, True, 0)
		topHBox1.pack_start(self.eNumber, True, True, 0)
		
		
		""" Begin midsection """
		pan = hildon.PannableArea()
		pan.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)		
		
		self.tvMessage = hildon.TextView()
		self.tvMessage.set_property("name", "hildon-fullscreen-textview")
		self.tvMessage.set_wrap_mode(gtk.WRAP_WORD)
		
		pan.add_with_viewport(self.tvMessage)
		
		""" Begin botsection """
		
		botHBox = gtk.HBox()
		botHBox.set_homogeneous(True)
		#self.bAttachment = gtk.FileChooserButton('')
		#self.bAttachment.connect('file-set', self.update_size)
		self.bAttachment = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, "Attachment")
		self.bAttachment.connect('clicked', self.open_file_dialog)
		self.attachmentFile = ""
		
		self.lSize = gtk.Label()
		self.lSize.set_markup("Size:\n<small>0 kB</small>")
		#self.lSize.set_width_chars(24)
		self.lSize.set_alignment(0.5, 0.5)
		
		
		self.bSend = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, "Send")
		self.bSend.connect('clicked', self.send_mms_clicked)
		
		botHBox.pack_start(self.bAttachment, True, True, 0)
		botHBox.pack_start(self.lSize, True, True, 0)
		botHBox.pack_start(self.bSend, True, True, 0)
		

		""" Show it all! """
		allBox.pack_start(topHBox1, False, False)
		allBox.pack_start(pan, True, True)
		allBox.pack_start(botHBox, False, False)
		
		self.window.add(allBox)
		self.window.show_all()
		self.add_window(self.window)
	
	# TODO: pass reference instead of making it available in the object?
	def open_contacts_dialog(self, button):
		selector = self.create_contacts_selector()
		self.contacts_dialog = gtk.Dialog("Select a contact")

		# TODO: remove hardcoded height
		self.contacts_dialog.set_default_size(-1, 320)
			        			    
		self.contacts_dialog.vbox.pack_start(selector)
		self.contacts_dialog.add_button("Done", 1)
		self.contacts_dialog.show_all()
		while 1:
			ret = self.contacts_dialog.run()
			if ret == 1:
				ret2 = self.contact_selector_changed(selector)
				if ret2 == 0:
					break
			else:
				break
		self.contacts_dialog.destroy()

	""" forces ui update, kinda... god this is AWESOME """
	def force_ui_update(self):
		while gtk.events_pending():
			gtk.main_iteration(False)
	
	def contact_number_chosen(self, button, nrdialog):
		print button.get_label()
		nr = button.get_label().replace(" ", "")
		nr = re.sub("[^0-9]\+", "", nr)
		self.eNumber.set_text(nr)
		nrdialog.response(0)
		self.contacts_dialog.response(0)
		
	def contact_selector_changed(self, selector):
		username = selector.get_current_text()
		nrlist = self.ch.get_numbers_from_name(username)
		nrdialog = gtk.Dialog("Pick a number")
		for number in nrlist:
			numberbox = gtk.HBox()
			typelabel = gtk.Label(nrlist[number].capitalize())
			typelabel.set_width_chars(24)
			button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
			button.set_label(number)
			button.connect('clicked', self.contact_number_chosen, nrdialog)
			numberbox.pack_start(typelabel, False, False, 0)
			numberbox.pack_start(button, True, True, 0)
			nrdialog.vbox.pack_start(numberbox)
		nrdialog.show_all()
		# this is blocking until we get a return
		ret = nrdialog.run()
		nrdialog.destroy()
		return ret
	
	def create_contacts_selector(self):
		#Create a HildonTouchSelector with a single text column
		selector = hildon.TouchSelectorEntry(text = True)
		#selector.connect('changed', self.contact_selector_changed)

		cl = self.ch.get_contacts_as_list()

		# Populate selector
		for contact in cl:
			if contact != None:
				# Add item to the column 
				#print "adding", contact
				selector.append_text(contact)

		# Set selection mode to allow multiple selection
		selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
		return selector

		
	def open_file_dialog(self, button):
		#fsm = hildon.FileSystemModel()
		#fcd = hildon.FileChooserDialog(self.window, gtk.FILE_CHOOSER_ACTION_OPEN, fsm)
		# this shouldnt issue a warning according to the pymaemo mailing list, but does
		# anyway, nfc why :(
		fcd = gobject.new(hildon.FileChooserDialog, action=gtk.FILE_CHOOSER_ACTION_OPEN)
		fcd.set_default_response(gtk.RESPONSE_OK)
		ret = fcd.run()
		if ret == gtk.RESPONSE_OK:
			### filesize check
			### TODO: dont hardcode
			filesize = os.path.getsize(fcd.get_filename()) / 1024
			if filesize > 10240:
				banner = hildon.hildon_banner_show_information(self.window, "", "10MB attachment limit in effect, please try another file")
				self.bAttachment.set_label("Attachment")
			else:
				self.bAttachment.set_label(os.path.basename(fcd.get_filename()))
				self.update_size(fcd.get_filename())
				self.attachmentFile = fcd.get_filename()
			fcd.destroy()
		else:
			fcd.destroy()
	
	""" resize an image """
	""" thanks tomaszf for this function """
	""" slightly modified by frals """
	def resize_img(self, filename):
		try:
			if not os.path.isdir(self.config.get_imgdir()):
				log.info("creating dir %s", self.config.get_imgdir())
				os.makedirs(self.config.get_imgdir())
			
			hildon.hildon_banner_show_information(self.window, "", "fMMS: Resizing image, this might take a while...")
			self.force_ui_update()
			
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
				rimg.save(rattachment)
				self.attachmentIsResized = True
			else:
				rattachment = filename
				
			return rattachment
		
		except Exception, e:
			log.exception("resizer: %s %s", type(exc), exc)
			raise
	
	def send_mms_clicked(self, widget):
		# Disable send-button
		self.bSend.set_sensitive(False)
		self.send_mms(widget)
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		self.bSend.set_sensitive(True)
	
	""" sends the message (no shit?) """
	def send_mms(self, widget):
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		self.osso_c = osso.Context("fMMS", "0.1.0", False)
		
		
		to = self.eNumber.get_text()
		if not self.cont.validate_phonenumber(to):
			note = osso.SystemNote(self.osso_c)
			note.system_note_dialog("Invalid phonenumber, must only contain + and digits" , 'notice')
			return
		
		attachment = self.attachmentFile
		if attachment == "" or attachment == None:
			attachment = None
			self.attachmentIsResized = False
		else:
			log.info("attachment: %s", attachment)
			filetype = mimetypes.guess_type(attachment)[0]
			self.attachmentIsResized = False
			if self.config.get_img_resize_width() != 0 and filetype.startswith("image"):
				try:
					attachment = self.resize_img(attachment)
				except Exception, e:
					log.exception("resize failed: %s %s", type(exc), exc)
					note = osso.SystemNote(self.osso_c)
					errmsg = str(e.args)
					note.system_note_dialog("Resizing failed:\nError: " + errmsg , 'notice')
					raise
		
		to = self.eNumber.get_text()
		sender = self.config.get_phonenumber()
		tb = self.tvMessage.get_buffer()
		message = tb.get_text(tb.get_start_iter(), tb.get_end_iter())
		log.info("sender: %s attachment %s to %s message %s", sender, attachment, to, message)

		""" Construct and send the message, off you go! """
		# TODO: remove hardcoded subject
		# TODO: let controller do this
		try:
			subject = message[:10]
			if len(message) > 10:
				subject += "..."
			sender = MMSSender(to, subject, message, attachment, sender)
			(status, reason, output) = sender.sendMMS()
			### TODO: Clean up and make this look decent
			message = str(status) + "_" + str(reason)
		
			reply = str(output)
			#print message
			#note = osso.SystemNote(self.osso_c)
			#ret = note.system_note_dialog("MMSC REPLIED:" + message + "\nBODY:" + reply, 'notice')
			banner = hildon.hildon_banner_show_information(self.window, "", "MMSC REPLIED:" + message + "\nBODY: " + reply)
                        
		except TypeError, exc:
			log.exception("sender: %s %s", type(exc), exc)
			note = osso.SystemNote(self.osso_c)
			errmsg = "Invalid attachment"
			note.system_note_dialog("Sending failed:\nError: " + errmsg + " \nPlease make sure the file is valid" , 'notice')
			#raise
		except socket.error, exc:
			log.exception("sender: %s %s", type(exc), exc)
			code = str(exc.args[0])
			text = str(exc.args[1])
			note = osso.SystemNote(self.osso_c)
			errmsg = code + " " + text
			note.system_note_dialog("Sending failed:\nError: " + errmsg + " \nPlease make sure APN settings are correct" , 'notice')
			#raise
		except Exception, exc:
			log.exception("sender: %s %s", type(exc), exc)
			raise
		finally:
			hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
			self.bSend.set_sensitive(True)
			
		if self.attachmentIsResized == True:
			log.info("Removing temporary image: %s", attachment)
			os.remove(attachment)
		#self.window.destroy()
		
	def update_size(self, fname):
		try:
			size = os.path.getsize(fname) / 1024
			self.lSize.set_markup("Size:\n<small>" + str(size) + " kB</small>")	
		except TypeError:
			self.lSize.set_markup("Size:\n<small>0 kB</small>")

	def quit(self, *args):
		gtk.main_quit()

	def run(self):
		self.window.show_all()
		gtk.main()
		
if __name__ == "__main__":
	app = fMMS_SenderUI()
	app.run()