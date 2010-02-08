#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
""" Set up a supersecret connection!

@license: GNU GPL
"""
import dbus

from dbus import SystemBus, SessionBus, Interface
from dbus._expat_introspect_parser import process_introspection_data

def introspect_object(named_service, object_path):
    obj = SystemBus().get_object(named_service, object_path)
    iface = Interface(obj, 'org.freedesktop.DBus.Introspectable')
#    return process_introspection_data(iface.Introspect())
    return iface.Introspect()

#print introspect_object('com.nokia.csd', '/com/nokia/csd')
#print introspect_object('com.nokia.csd.GPRS', '/com/nokia/csd/gprs')
#print introspect_object('com.nokia.csd.GPRS', '/com/nokia/csd/gprs/0')

bus = dbus.SystemBus()
gprs = dbus.Interface(bus.get_object("com.nokia.csd", "/com/nokia/csd/gprs"), "com.nokia.csd.GPRS")
obj = gprs.QuickConnect("internet.tele2.se", "IP", "", "")
conn = dbus.Interface(bus.get_object("com.nokia.csd", obj), "com.nokia.csd.GPRS.Context")
(apn, ctype, iface, ipaddr, connected, tx, rx) = conn.GetStatus()
# operations on conn:
# Connect, Disconnect, Delete, GetStatus, Connected, ConnectFailed, Disconnected, Deleted
# Properties: APN, Username, Password, PDPType, PDPAddress, SDNSAddres, PDNSAddress, NetIF, Connected, RxBytes, TxBytes
print (apn, ctype, iface, ipaddr, connected, tx, rx)
try:
	tmp = bus.get_object("com.nokia.csd.GPRS", obj)
	props = dbus.Interface(tmp, "org.freedesktop.DBus.Properties")
	apn = props.Get("com.nokia.csd.GPRS.Context", "APN")
	dns = props.Get("com.nokia.csd.GPRS.Context", "PDNSAddress")
	sdns = props.Get("com.nokia.csd.GPRS.Context", "SDNSAddress")
	print apn, dns, sdns
except Exception, e:
	print type(e), e

"""
ifconfig gprs0 <ip> up
route add -net 83.191.132.0 netmask 255.255.255.0 dev gprs0
route add -net 130.244.202.0 netmask 255.255.255.0 dev gprs0
"""

conn.Disconnect()