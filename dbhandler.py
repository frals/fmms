#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" database handler for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import sqlite3
import os

from gnome import gnomevfs

import fmms_config as fMMSconf

import logging
log = logging.getLogger('fmms.%s' % __name__)


# TODO: constants.py?
MSG_DIRECTION_IN = 0
MSG_DIRECTION_OUT = 1
MSG_UNREAD = 0
MSG_READ = 1


class DatabaseHandler:
	
	def __init__(self):
		self.config = fMMSconf.fMMS_config()
		self.pushdir = self.config.get_pushdir()
		self.mmsdir = self.config.get_mmsdir()
		self.outdir = self.config.get_outdir()
		self.db = self.config.get_db_path()
		self.conn = sqlite3.connect(self.db)
		self.conn.text_factory = str
		self.conn.row_factory = sqlite3.Row
		try:
			c = self.conn.cursor()
			c.execute("SELECT * FROM revision")
			for row in c:
				if row['version'] != 1:
					self.create_database_layout()
		except:
			self.create_database_layout()

	def alter_database_layout_1(self):
		c = self.conn
		c.execute("""UPDATE """)
		c.execute("""ALTER TABLE """)
		
	def create_database_layout(self):
		c = self.conn
		c.execute("""CREATE TABLE "revision" ("version" INT);""")
		c.execute("""INSERT INTO "revision" ("version") VALUES ('1');""")
		# database layout
		c.execute("""CREATE TABLE "push"(
			  "idpush" INTEGER PRIMARY KEY NOT NULL,
			  "transactionid" TEXT NOT NULL,
			  "content_location" TEXT NULL,
			  "msg_time" TIMESTAMP,
			  "msg_type" TEXT NOT NULL,
			  "file" TEXT
			);""")
		c.execute("""CREATE TABLE "contacts"(
			  "idcontacts" INTEGER PRIMARY KEY NOT NULL,
			  "number" INTEGER NOT NULL,
			  "abook_uid" INTEGER DEFAULT NULL
			);""")
		c.execute("""CREATE TABLE "mms"(
			  "id" INTEGER PRIMARY KEY NOT NULL,
			  "pushid" INTEGER DEFAULT NULL,
			  "transactionid" INTEGER DEFAULT NULL,
			  "msg_time" TIMESTAMP DEFAULT NULL,
			  "read" INTEGER DEFAULT NULL,
			  "direction" INTEGER DEFAULT NULL,
			  "size" INT DEFAULT NULL,
			  "contact" INTEGER DEFAULT NULL,
			  "file" TEXT DEFAULT NULL,
			  CONSTRAINT "pushid"
			    FOREIGN KEY("pushid")
			    REFERENCES "push"("idpush"),
			  CONSTRAINT "contact"
			    FOREIGN KEY("contact")
			    REFERENCES "contacts"("idcontacts")
			);""")
		c.execute("""CREATE INDEX "mms.pushid" ON "mms"("pushid");""")
		c.execute("""CREATE INDEX "mms.contact" ON "mms"("contact");""")
		c.execute("""CREATE TABLE "mms_headers"(
			  "idmms_headers" INTEGER PRIMARY KEY NOT NULL,
			  "mms_id" INTEGER DEFAULT NULL,
			  "header" TEXT DEFAULT NULL,
			  "value" TEXT DEFAULT NULL,
			  CONSTRAINT "mms_id"
			    FOREIGN KEY("mms_id")
			    REFERENCES "mms"("id")
			);""")
		c.execute("""CREATE INDEX "mms_headers.mms_id" ON "mms_headers"("mms_id");""")
		c.execute("""CREATE TABLE "attachments"(
			  "idattachments" INTEGER PRIMARY KEY NOT NULL,
			  "mmsidattach" INTEGER DEFAULT NULL,
			  "file" TEXT DEFAULT NULL,
			  "hidden" INTEGER DEFAULT NULL,
			  CONSTRAINT "mmsidattach"
			    FOREIGN KEY("mmsidattach")
			    REFERENCES "mms"("id")
			);""")
		c.execute("""CREATE INDEX "attachments.mmsidattach" ON "attachments"("mmsidattach");""")
		c.execute("""CREATE TABLE "push_headers"(
			  "idpush_headers" INTEGER PRIMARY KEY NOT NULL,
			  "push_id" INTEGER DEFAULT NULL,
			  "header" TEXT DEFAULT NULL,
			  "value" TEXT DEFAULT NULL,
			  CONSTRAINT "push_id"
			    FOREIGN KEY("push_id")
			    REFERENCES "push"("idpush")
			);""")
		c.execute("""CREATE INDEX "push_headers.push_id" ON "push_headers"("push_id");""")
		self.conn.commit()


	def get_push_list(self, types=None):
		""" gets all push messages from the db and returns as a list
		containing a dict for each separate push """
		c = self.conn.cursor()
		retlist = []
		# TODO: better where clause
		c.execute("select * from push where msg_type != 'm-notifyresp-ind' order by msg_time DESC")
		pushlist = c.fetchall()
		for line in pushlist:
			result = {}
			result['PUSHID'] = line['idpush']
			result['Transaction-Id'] = line['transactionid']
			result['Content-Location'] = line['content_location']
			result['Time'] = line['msg_time']
			result['Message-Type'] = line['msg_type']
			c.execute("select * from push_headers WHERE push_id = ?", (line['idpush'],))
			for line2 in c:
				result[line2['header']] = line2['value']
				
			retlist.append(result)

		return retlist

	def insert_push_message(self, pushlist):
		""" Inserts a push message (from a list)
		Returns the id of the inserted row
		
		"""
		c = self.conn.cursor()
		conn = self.conn
		try:
			transid = pushlist['Transaction-Id']
			del pushlist['Transaction-Id']
			contentloc = pushlist['Content-Location']
			del pushlist['Content-Location']
			msgtype = pushlist['Message-Type']
			del pushlist['Message-Type']
		except:
			log.exception("No transid/contentloc/message-type, bailing out!")
			raise
		fpath = self.pushdir + transid
		vals = (transid, contentloc, msgtype, fpath)
		c.execute("insert into push (transactionid, content_location, msg_time, msg_type, file) VALUES (?, ?, datetime('now'), ?, ?)", vals)
		pushid = c.lastrowid
		conn.commit()
		log.info("inserted row as: %s", pushid)
		
		for line in pushlist:
			vals = (pushid, line, str(pushlist[line]))
			c.execute("insert into push_headers (push_id, header, value) VALUES (?, ?, ?)", vals)
			conn.commit()
			
		return pushid
	
	def insert_push_send(self, pushlist):
		""" Inserts a push message (from a list)
		Returns the id of the inserted row

		"""
		c = self.conn.cursor()
		conn = self.conn
		try:
			transid = pushlist['Transaction-Id']
			del pushlist['Transaction-Id']
			msgtype = pushlist['Message-Type']
			del pushlist['Message-Type']
		except:
			log.exception("No transid/message-type, bailing out!")
			raise
		fpath = self.outdir + transid
		vals = (transid, 0, msgtype, fpath)
		c.execute("insert into push (transactionid, content_location, msg_time, msg_type, file) VALUES (?, ?, datetime('now'), ?, ?)", vals)
		pushid = c.lastrowid
		conn.commit()
		log.info("inserted row as: %s", pushid)

		for line in pushlist:
			vals = (pushid, line, str(pushlist[line]))
			c.execute("insert into push_headers (push_id, header, value) VALUES (?, ?, ?)", vals)
			conn.commit()
					
		return pushid

	def link_push_mms(self, pushid, mmsid):
		c = self.conn.cursor()
		c.execute("update mms set pushid = ? where id = ?", (pushid, mmsid))
		self.conn.commit()
	
	
	def mark_message_read(self, transactionid):
		c = self.conn.cursor()
		c.execute("update mms set read = 1 where transactionid = ?", (transactionid, ))
		self.conn.commit()
	
	

	def get_push_message(self, transid):
		""" retrieves a push message from the db and returns it as a dict """
		c = self.conn.cursor()
		retlist = {}
		vals = (transid,)
		c.execute("select * from push WHERE transactionid = ? LIMIT 1;", vals)
		
		for line in c:
			retlist['Transaction-Id'] = line['transactionid']
			retlist['Content-Location'] = line['content_location']
			retlist['Message-Type'] = line['msg_type']
			retlist['Time'] = line['msg_time']
			retlist['File'] = line['file']
			retlist['PUSHID'] = line['idpush']
		
		try:
			c.execute("select * from push_headers WHERE push_id = ?;", (retlist['PUSHID'], ))
		except Exception, e:
			log.exception("%s %s", type(e), e)
			raise
		
		for line in c:
			hdr = line['header']
			val = line['value']
			retlist[hdr] = val
		
		return retlist
	

	def is_mms_downloaded(self, transid):
		c = self.conn.cursor()
		vals = (transid,)
		isread = None
		c.execute("select * from mms where `transactionid` = ?;", vals)
		for line in c:
			isread = line['id']
		if isread != None:
			return True
		else:
			return False
			
	
	def is_message_read(self, transactionid):
		c = self.conn.cursor()
		vals = (transactionid,)
		isread = None
		c.execute("select read from mms where `transactionid` = ?;", vals)
		for line in c:
			isread = line['read']
		if isread == 1:
			return True
		else:
			return False
	
	def insert_mms_message(self, pushid, message, direction=MSG_DIRECTION_IN):
		"""Takes a MMSMessage object as input, and optionally a MSG_DIRECTION_*
		Returns the newly inserted rows id.
		
		"""		
		mmslist = message.headers
		attachments = message.attachments
		c = self.conn.cursor()
		conn = self.conn
		try:
			transid = mmslist['Transaction-Id']
			del mmslist['Transaction-Id']
			if direction == MSG_DIRECTION_OUT:
				basedir = self.outdir + transid
			else:
				basedir = self.mmsdir + transid
				
			fpath = basedir + "/message"
			size = os.path.getsize(fpath)
		except:
			log.exception("No transid/message-type, bailing out!")
			raise
		try:
			time = mmslist['Date']
			del mmslist['Date']
			dateset = True
		except:
			dateset = False
		isread = MSG_UNREAD
		contact = 0
		if dateset == False:
			vals = (pushid, transid, isread, direction, size, contact, fpath)
			c.execute("insert into mms (pushid, transactionid, msg_time, read, direction, size, contact, file) VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?)", vals)
		else:
			vals = (pushid, transid, time, isread, direction, size, contact, fpath)
			c.execute("insert into mms (pushid, transactionid, msg_time, read, direction, size, contact, file) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", vals)
		mmsid = c.lastrowid
		conn.commit()
		log.info("inserted row as: %s", mmsid)
		
		# insert all headers
		for line in mmslist:
			vals = (mmsid, line, str(mmslist[line]))
			c.execute("insert into mms_headers (mms_id, header, value) VALUES (?, ?, ?)", vals)
			conn.commit()
		attachpaths = basedir + "/"
		# insert the attachments
		for line in attachments:
			log.info("inserting attachment: %s", line)
			filetype = gnomevfs.get_mime_type(attachpaths + line)
			(fname, ext) = os.path.splitext(line)
			hidden = 0
			# These files should be "hidden" from the user
			if ext.startswith(".smil") or filetype == "application/smil":
				hidden = 1
			vals = (mmsid, line, hidden)
			c.execute("insert into attachments (mmsidattach, file, hidden) VALUES (?, ?, ?)", vals)
			conn.commit()
		
		try:
			description = str(mmslist['Subject'])
		except:
			description = ""			
			# get the textfiles
			for line in attachments:
				filetype = gnomevfs.get_mime_type(attachpaths + line)
				log.info("filetype: %s", filetype)
				if filetype.startswith("text"):
					filep = open(attachpaths + line, 'r')
					description += filep.read()
					filep.close()
			
		# insert the message to be shown in the mainview
		vals = (mmsid, "Description", description)
		log.info("inserting description: %s", description)
		c.execute("insert into mms_headers (mms_id, header, value) VALUES (?, ?, ?)", vals)
		conn.commit()

		return mmsid

	def get_mms_attachments(self, transactionid, allFiles=False):
		c = self.conn.cursor()
		mmsid = self.get_mmsid_from_transactionid(transactionid)
		if mmsid != None:
			if allFiles == True:
				c.execute("select * from attachments where mmsidattach == ?", (mmsid,))
			else:
				c.execute("select * from attachments where mmsidattach == ? and hidden == 0", (mmsid,))
			filelist = []
			for line in c:
				filelist.append(line['file'])

			return filelist


	def get_mms_headers(self, transactionid):
		c = self.conn.cursor()
		mmsid = self.get_mmsid_from_transactionid(transactionid)
		retlist = {}
		
		c.execute("select * from mms WHERE id = ? LIMIT 1;", (mmsid,))
				
		for line in c:
			retlist['Transaction-Id'] = line['transactionid']
			retlist['Time'] = line['msg_time']

		if mmsid != None:
			c.execute("select * from mms_headers WHERE mms_id = ?;", (mmsid, ))
			for line in c:
				hdr = line['header']
				val = line['value']
				retlist[hdr] = val
		return retlist

	def get_mmsid_from_transactionid(self, transactionid):
		c = self.conn.cursor()
		c.execute("select * from mms where transactionid == ?", (transactionid, ))
		res = c.fetchone()
		try:
			mmsid = res['id']
			return mmsid
		except:
			return None
	
	def get_direction_mms(self, transid):
		c = self.conn.cursor()
		c.execute("select direction from mms where transactionid = ?", (transid, ))
		res = c.fetchone()
		try:
			direction = res['direction']
			return direction
		except:
			return None
	
	def get_replyuri_from_transid(self, transid):
		mmsid = self.get_mmsid_from_transactionid(transid)
		if mmsid == None:
			return None
		c = self.conn.cursor()
		c.execute("select value from mms_headers where mms_id = ? and header = 'From'", (mmsid, ))
		res = c.fetchone()
		try:
			uri = res['value']
			return uri
		except:
			return None
	
	
	def get_pushid_from_transactionid(self, transactionid):
		c = self.conn.cursor()
		c.execute("select * from push where transactionid == ?", (transactionid, ))
		res = c.fetchone()
		try:
			mmsid = res['idpush']
			return mmsid
		except:
			return None
	
	def delete_mms_message(self, transactionid):
		c = self.conn.cursor()
		mmsid = self.get_mmsid_from_transactionid(transactionid)
		if mmsid != None:
			c.execute("delete from mms where id == ?", (mmsid,))
			c.execute("delete from attachments where mmsidattach == ?", (mmsid,))
			c.execute("delete from mms_headers where mms_id == ?", (mmsid,))
			self.conn.commit()
			
	def delete_push_message(self, transactionid):
		c = self.conn.cursor()
		pushid = self.get_pushid_from_transactionid(transactionid)
		if pushid != None:
			c.execute("delete from push where idpush == ?", (pushid,))
			c.execute("delete from push_headers where push_id == ?", (pushid,))
			self.conn.commit()	


if __name__ == '__main__':
	db = DatabaseHandler()
	c = db.conn.cursor()