#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" daemon for fMMS

@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU GPL
"""
import dbus
import gobject
import dbus.mainloop.glib
import dbus.service

from wappushhandler import PushHandler
import controller as fMMSController

import logging
log = logging.getLogger('fmms.%s' % __name__)

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
		handler = PushHandler()
		ret = handler._incoming_sms_push(source, srcport, dstport, header, payload)
		return 0

	""" According to wappushd.h IP PUSH is one more argument 
	@dbus.service.method(dbus_interface='com.nokia.WAPPushHandler')
	def HandleWAPPush(self, bearer, source, dest, srcport, dstport, header, payload):
		handler = PushHandler()
		ret = handler._incoming_ip_push(source, dest, srcport, dstport, header, payload)
		return 0
	"""

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
loop = gobject.MainLoop()
server = MMSHandler()
loop.run()
