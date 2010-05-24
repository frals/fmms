#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" daemon for fMMS

fMMS - MMS for fremantle
Copyright (C) 2010 Nick Leppänen Larsson <frals@frals.se>

@license: GNU GPLv2, see COPYING file.
"""
import subprocess

import dbus
import gobject
import dbus.mainloop.glib
import dbus.service

import logging
log = logging.getLogger('fmms.fmmsd')

class MMSHandler(dbus.service.Object):
	def __init__(self):
		# Here the service name
		bus_name = dbus.service.BusName('se.frals.mms', bus=dbus.SystemBus())
		# Here the object path
		dbus.service.Object.__init__(self, bus_name, '/se/frals/mms')

	# TODO: This should filter by bearer and not number of arguments, really, it should.
	# Here the interface name, and the method is named same as on dbus.
	""" According to wappushd.h SMS PUSH is one less argument """
	@dbus.service.method(dbus_interface='com.nokia.WAPPushHandler')
	def HandleWAPPush(self, bearer, source, srcport, dstport, header, payload):
		try:
			subprocess.Popen(["/usr/bin/run-standalone.sh", "/opt/fmms/wappushhandler.py", str(source), str(srcport), str(dstport), str(header), str(payload)])
		except:
			log.exception("failed to spawn subprocess for processing")
		log.info("All done, signing off!")


	""" According to wappushd.h IP PUSH is one more argument 
	@dbus.service.method(dbus_interface='com.nokia.WAPPushHandler')
	def HandleWAPPush(self, bearer, source, dest, srcport, dstport, header, payload):
		handler = PushHandler()
		ret = handler._incoming_ip_push(source, dest, srcport, dstport, header, payload)
		return 0
	"""

if __name__ == '__main__':
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	bus = dbus.SystemBus()
	loop = gobject.MainLoop()
	server = MMSHandler()
	loop.run()