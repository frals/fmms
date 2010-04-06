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
import StringIO

import gtk
import hildon
import gobject
import osso
import dbus
from gnome import gnomevfs

from wappushhandler import MMSSender
import fmms_config as fMMSconf
import contacts as ContactH
import controller as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

class fMMS_SenderUI(hildon.Program):
	def __init__(self, spawner=None, tonumber=None, withfile=None, subject=None, message=None):
		hildon.Program.__init__(self)
		program = hildon.Program.get_instance()
		
		self.config = fMMSconf.fMMS_config()
		self.ch = ContactH.ContactHandler()
		self.cont = fMMSController.fMMS_controller()
		self.subject = subject
		
		self.window = hildon.StackableWindow()
		self.window.set_title("New MMS")
		program.add_window(self.window)
		
		self.window.connect("delete_event", self.quit)
		
		if spawner != None:
			self.spawner = spawner
		else:
			self.spawner = self.window
		allBox = gtk.VBox()
		
		""" Begin top section """
		topHBox1 = gtk.HBox()
		
		bTo = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL, "To")
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
		
		eboxFrame = gtk.Frame()
		eboxFrame.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
		self.imageBox = gtk.EventBox()
		self.imageBox.set_size_request(200, 200)
		#self.imageBox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("blue"))
		self.imageBoxContent = gtk.Label("Tap to add image")
		self.imageBox.add(self.imageBoxContent)
		self.imageBox.connect('button-press-event', self.open_file_dialog)
		
		
		""" this stuff doesnt really work yet.. """
		eboxFrame.set_border_width(2)
		eboxFrame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("blue"))
		
		eboxFrame.add(self.imageBox)
		
		centerBox.pack_start(eboxFrame, True, False, 0)
		
		self.tvMessage = hildon.TextView()
		self.tvMessage.set_property("name", "hildon-fullscreen-textview")
		self.tvMessage.set_wrap_mode(gtk.WRAP_CHAR)
		self.tvMessage.set_justification(gtk.JUSTIFY_CENTER)
		if message != None and message != '':
			tb = gtk.TextBuffer()
			tb.set_text(message)
			self.tvMessage.set_buffer(tb)
		
		midBox.pack_start(centerBox)
		midBox.pack_start(self.tvMessage)
		
		pan.add_with_viewport(midBox)
		#pan.add_with_viewport(self.tvMessage)
		
		self.attachmentFile = ""
		
		if withfile != None:
			self.attachmentFile = withfile
			self.set_thumbnail(self.attachmentFile)

		""" get all contacts in a dict (name, uid) """
		self.cl = self.ch.get_contacts_as_list()
		self.cldict = self.ch.get_contacts_as_dict()

		""" Show it all! """
		allBox.pack_start(topHBox1, False, False)
		allBox.pack_start(pan, True, True)
		#allBox.pack_start(self.botHBox, False, False)
		
		align = gtk.Alignment(1, 1, 1, 1)
		align.set_padding(2, 2, 10, 10)		
		align.add(allBox)
		
		self.window.add(align)
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
		nr = button.get_label().replace(" ", "")
		if not "@" in nr:
			nr = re.sub(r'[^\d|\+]+', '', nr)
		self.eNumber.set_text(nr)
		nrdialog.response(0)
		self.contacts_dialog.response(0)
	
	
	def contact_selector_changed(self, selector):
		username = selector.get_current_text()
		uid = self.cldict[username]
		nrlist = self.ch.get_numbers_from_uid(uid)
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
		selector = hildon.TouchSelectorEntry(text=True)
		
		for (contact, uid) in self.cl:
			if contact != None:
				selector.append_text(contact)

		selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
		return selector

	def set_thumbnail(self, filename):
		filetype = gnomevfs.get_mime_type(filename)
		if filetype.startswith("image") or filetype.startswith("sketch"):
			im = Image.open(filename)
			im.thumbnail((256, 256), Image.NEAREST)
			pixbuf = self.cont.image2pixbuf(im)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)
			self.imageBox.remove(self.imageBoxContent)
			self.imageBoxContent = image
			self.imageBox.add(self.imageBoxContent)
			self.imageBox.show_all()
		elif filetype.startswith("audio"):
			icon_theme = gtk.icon_theme_get_default()
			pixbuf = icon_theme.load_icon("mediaplayer_default_album", 128, 0)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)
			self.imageBox.remove(self.imageBoxContent)
			self.imageBoxContent = image
			self.imageBox.add(self.imageBoxContent)
			self.imageBox.show_all()
		elif filetype.startswith("video"):
			icon_theme = gtk.icon_theme_get_default()
			pixbuf = icon_theme.load_icon("general_video", 128, 0)
			image = gtk.Image()
			image.set_from_pixbuf(pixbuf)
			self.imageBox.remove(self.imageBoxContent)
			self.imageBoxContent = image
			self.imageBox.add(self.imageBoxContent)
			self.imageBox.show_all()
		return

		
	def open_file_dialog(self, button, data=None):
		#fsm = hildon.FileSystemModel()
		#fcd = hildon.FileChooserDialog(self.window, gtk.FILE_CHOOSER_ACTION_OPEN, fsm)
		# this shouldnt issue a warning according to the pymaemo mailing list, but does
		# anyway, nfc why :(
		# TODO: set default dir to Camera
		fcd = gobject.new(hildon.FileChooserDialog, action=gtk.FILE_CHOOSER_ACTION_OPEN)
		fcd.set_default_response(gtk.RESPONSE_OK)
		ret = fcd.run()
		if ret == gtk.RESPONSE_OK:
			### TODO: dont hardcode filesize check
			filesize = os.path.getsize(fcd.get_filename()) / 1024
			if filesize > 10240:
				banner = hildon.hildon_banner_show_information(self.window, "", "10MB attachment limit in effect, please try another file")
			else:
				self.attachmentFile = fcd.get_filename()
				self.set_thumbnail(self.attachmentFile)
			fcd.destroy()
		else:
			fcd.destroy()
		return True
	
	
	""" from http://snippets.dzone.com/posts/show/655 """
	def image2pixbuf(self, im):
		file1 = StringIO.StringIO()
		im.save(file1, "ppm")
		contents = file1.getvalue()
		file1.close()
		loader = gtk.gdk.PixbufLoader("pnm")
		loader.write(contents, len(contents))
		pixbuf = loader.get_pixbuf()
		loader.close()
		return pixbuf

	
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
		self.send_mms(widget)
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
		self.bSend.set_sensitive(True)
	
	""" sends the message (no shit?) """
	def send_mms(self, widget):
		hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
		self.force_ui_update()
		
		self.osso_c = osso.Context("fMMS", "0.1.0", False)
		
		
		to = self.eNumber.get_text()
		# TODO: skip this if it looks like an email
		if not self.cont.validate_phonenumber_email(to):
			note = osso.SystemNote(self.osso_c)
			note.system_note_dialog("Invalid phonenumber, must only contain + and digits" , 'notice')
			return
		
		attachment = self.attachmentFile
		if attachment == "" or attachment == None:
			attachment = None
			self.attachmentIsResized = False
		else:
			log.info("attachment: %s", attachment)
			filetype = gnomevfs.get_mime_type(attachment)
			self.attachmentIsResized = False
			if self.config.get_img_resize_width() != 0 and filetype.startswith("image"):
				try:
					attachment = self.resize_img(attachment)
				except Exception, e:
					log.exception("resize failed: %s %s", type(e), e)
					note = osso.SystemNote(self.osso_c)
					errmsg = str(e.args)
					note.system_note_dialog("Resizing failed:\nError: " + errmsg , 'notice')
					raise
		
		to = self.eNumber.get_text()
		sender = self.config.get_phonenumber()
		tb = self.tvMessage.get_buffer()
		message = tb.get_text(tb.get_start_iter(), tb.get_end_iter())
		log.info("sender: %s attachment: %s to: %s message: %s", sender, attachment, to, message)

		""" Construct and send the message, off you go! """
		# TODO: let controller do this
		try:
			if self.subject == '' or self.subject == None:
				subject = message[:10]
				if len(message) > 10:
					subject += "..."
				if len(subject) == 0:
					subject = "MMS"
			else:
				subject = self.subject
			sender = MMSSender(to, subject, message, attachment, sender, setupConn=True)
			(status, reason, output, parsed) = sender.sendMMS()
			### TODO: Clean up and make this look decent
			
			if parsed == True and "Response-Status" in output:
				if output['Response-Status'] == "Ok":
					log.info("message seems to have sent AOK!")
					banner = hildon.hildon_banner_show_information(self.spawner, "", "Message sent")
					if self.window == self.spawner:
						self.quit()
					else:
						self.window.destroy()
					return
			
			message = str(status) + "_" + str(reason)
			reply = str(output)
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
		

	def quit(self, *args):
		gtk.main_quit()

	def run(self):
		self.window.show_all()
		gtk.main()
		
if __name__ == "__main__":
	app = fMMS_SenderUI()
	app.run()