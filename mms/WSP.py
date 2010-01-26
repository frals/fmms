# -*- coding: utf-8 -*-
#
# This library is free software, distributed under the terms of
# the GNU Lesser General Public License Version 2.
# See the COPYING.LESSER file included in this archive
#
# The docstrings in this module contain epytext markup; API documentation
# may be created by processing this file with epydoc: http://epydoc.sf.net
"""
Library for WAP transport, original by Francois Aucamp, modified by Nick Leppänen Larsson
for use in Maemo5/Fremantle on the Nokia N900.

@author: Francois Aucamp <faucamp@csir.co.za>
@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU LGPL
"""
from WTP import WTP
import sys
import array
import socket, time

from wsp_pdu import Decoder, Encoder, WSPEncodingAssignments
from iterator import PreviewIterator

class WSP:
    """ This class implements a very limited subset of the WSP layer.
    
    It uses python-mms's WSP PDU encoding module for almost all encodings,
    and essentially just glues it together into a limited WSP layer. """
    def __init__(self, wapGatewayHost, wapGatewayPort=9201):
        self.serverSessionID = -1
        self.capabilities = {'ClientSDUSize': 261120,
                             'ServerSDUSize': 261120}
        self.headers = [('User-Agent', 'Nokia N900'),
                        ('Accept', 'text/plain'),
                        ('Accept', 'application/vnd.wap.mms-message')]
        self.wtp = WTP(wapGatewayHost, wapGatewayPort)

    def connect(self):
        """ Sends a WSP Connect message to the gateway, including any
        configured capabilities. It also updates the WSP object to reflect
        the status of the WSP connection """
        print '>> WSP: Connect'
        response = self.wtp.invoke(self.encodeConnectPDU())
        self._decodePDU(response)
        

    def disconnect(self):
        """ Sends a WSP Connect message to the gateway, including any
        configured capabilities. It also updates the WSP object to reflect
        the status of the WSP connection """
        print '>> WSP: Disconnect'
        self.wtp.invoke(self.encodeDisconnectPDU(self.serverSessionID))
        self.serverSessionID = -1
        
    def post(self, uri, contentType, data):
        """ Performs a WSP POST """
        if type(data) == array.array:
            data = data.tolist()
        print '>> WSP: Post'
        pdu = self.encodePostPDU(uri, contentType) + data
        response = self.wtp.invoke(pdu)
        self._decodePDU(response)
        
    def get(self, uri):
        """ Performs a WSP GET """
        response = self.wtp.invoke(self.encodeGetPDU(uri))
        self._decodePDU(response)

    def encodeConnectPDU(self):
        """ Sends a WSP connect request (S-Connect.req, i.e. Connect PDU) to
        the WAP gateway 
        
        This PDU is described in WAP-230, section 8.2.2, and is sent to
        initiate the creation of a WSP session. Its field structure::
         
            Field Name       Type               Description
            ===============  =================  =================
            Version          uint8              WSP protocol version
            CapabilitiesLen  uintvar            Length of the Capabilities field
            HeadersLen       uintvar            Length of the Headers field
            Capabilities     <CapabilitiesLen>
                              octets            S-Connect.req::Requested Capabilities
            Headers          <HeadersLen>
                              octets            S-Connect.req::Client Headers
        """
        pdu = []
        pdu.append(0x01) # Type: "Connect"
        # Version field - we are using version 1.0
        pdu.extend(Encoder.encodeVersionValue('1.0'))
        # Add capabilities
        capabilities = []
        for capability in self.capabilities:
            # Unimplemented/broken capabilities are not added
            try:
                exec 'capabilities.extend(WSP._encodeCapabilty%s(self.capabilities[capability]))' % capability
            except:
                pass
        # Add and encode headers
        headers = array.array('B')
        for hdr, hdrValue in self.headers:
            headers.extend(Encoder.encodeHeader(hdr, hdrValue))
        # Add capabilities and headers to PDU (including their lengths)
        pdu.extend(Encoder.encodeUintvar(len(capabilities)))
        pdu.extend(Encoder.encodeUintvar(len(headers)))
        pdu.extend(capabilities)
        pdu.extend(headers)
        return pdu
    
    @staticmethod
    def encodePostPDU(uri, contentType):
        """ Builds a WSP POST PDU
        
        @note: This method does not add the <Data> part at the end of the PDU;
               this should be appended manually to the result of this method.
        
        The WSP Post PDU is defined in WAP-230, section 8.2.3.2::
                                     Table 10. Post Fields
         Name        Type                       Source
         ==========  ========================   ========================================
         UriLen      uintvar                    Length of the URI field
         HeadersLen  uintvar                    Length of the ContentType and Headers fields
                                                combined
         Uri         UriLen octets              S-MethodInvoke.req::Request URI or
                                                S-Unit-MethodInvoke.req::Request URI
         ContentType multiple octets            S-MethodInvoke.req::Request Headers or
                                                S-Unit-MethodInvoke.req::Request Headers
         Headers     (HeadersLen - length of    S-MethodInvoke.req::Request Headers or
                     ContentType) octets        S-Unit-MethodInvoke.req::Request Headers
         Data        multiple octets            S-MethodInvoke.req::Request Body or
                                                S-Unit-MethodInvoke.req::Request Body

        """
        #TODO: remove this, or make it dynamic or something:
        headers = [('Accept', 'application/vnd.wap.mms-message')]
        pdu = [0x60] # Type: "Post"
        # UriLen:
        pdu.extend(Encoder.encodeUintvar(len(uri)))
        # HeadersLen:
        encodedContentType = Encoder.encodeContentTypeValue(contentType, {})
        encodedHeaders = []
        for hdr, hdrValue in headers:
            encodedHeaders.extend(Encoder.encodeHeader(hdr, hdrValue))
        headersLen = len(encodedContentType) + len(encodedHeaders)
        pdu.extend(Encoder.encodeUintvar(headersLen))
        # URI - this should NOT be null-terminated (according to WAP-230 section 8.2.3.2)
        for char in uri:
            pdu.append(ord(char))
        # Content-Type:
        pdu.extend(encodedContentType)
        # Headers:
        pdu.extend(encodedHeaders)
        return pdu
    
    @staticmethod
    def encodeGetPDU(uri):
        """ Builds a WSP GET PDU 
        
        The WSP Get PDU is defined in WAP-230, section 8.2.3.1::
         Name    Type          Source
         ======  ============  =======================
         URILen  uintvar       Length of the URI field
         URI     URILen octets S-MethodInvoke.req::Request URI or
                               S-Unit-MethodInvoke.req::Request URI
         Headers multiple      S-MethodInvoke.req::Request Headers or
                 octets        S-Unit-MethodInvoke.req::Request Headers
        """
        pdu = self
        # UriLen:
        pdu.extend(Encoder.encodeUintvar(len(uri)))
        # URI - this should NOT be null-terminated (according to WAP-230 section 8.2.3.1)
        for char in uri:
            pdu.append(ord(char))
        headers = []
        #TODO: not sure if these should go here...
        for hdr, hdrValue in pdu.headers:
            headers.extend(Encoder.encodeHeader(hdr, hdrValue))
        pdu.extend(headers)
        return pdu
    
    @staticmethod
    def encodeDisconnectPDU(serverSessionID):
        """ Builds a WSP Disconnect PDU
        
        The Disconnect PDU is sent to terminate a session. It structure is
        defined in WAP-230, section 8.2.2.4::
         Name             Type     Source
         ===============  =======  ===================
         ServerSessionId  uintvar  Session_ID variable
        """
        pdu = [0x05] # Type: "Disconnect"
        pdu.extend(Encoder.encodeUintvar(serverSessionID))
        return pdu
    
    def _decodePDU(self, byteIter):
        """ Reads and decodes a WSP PDU from the sequence of bytes starting at
        the byte pointed to by C{dataIter.next()}.
        
        @param byteIter: an iterator over a sequence of bytes
        @type byteIteror: mms.iterator.PreviewIterator
        
        @note: If the PDU type is correctly determined, byteIter will be
               modified in order to read past the amount of bytes required
               by the PDU type.
        """
        pduType = Decoder.decodeUint8(byteIter)
        if pduType not in WSPEncodingAssignments.wspPDUTypes:
            #TODO: maybe raise some error or something
            print 'Error - unknown WSP PDU type: %s' % hex(pduType)
            raise TypeError
        pduType = WSPEncodingAssignments.wspPDUTypes[pduType]
        print '<< WSP: %s' % pduType
        pduValue = None
        try:
            exec 'pduValue = self._decode%sPDU(byteIter)' % pduType
        except:
            print 'A fatal error occurred, probably due to an unimplemented feature.\n'
            raise
        return pduValue
    
    def _decodeConnectReplyPDU(self, byteIter):
        """ The WSP ConnectReply PDU is sent in response to a S-Connect.req
        PDU. It is defined in WAP-230, section 8.2.2.2.
        
        All WSP PDU headers start with a type (uint8) byte (we do not
        implement connectionless WSP, thus we don't prepend TIDs to the WSP
        header). The WSP PDU types are specified in WAP-230, table 34.
        
        ConnectReply PDU Fields::
         Name            Type               Source
         =============== =================  =====================================
         ServerSessionId Uintvar            Session_ID variable
         CapabilitiesLen Uintvar            Length of Capabilities field
         HeadersLen      Uintvar            Length of the Headers field
         Capabilities    <CapabilitiesLen>  S-Connect.res::Negotiated Capabilities
                          octets
         Headers         <HeadersLen>       S-Connect.res::Server Headers
                          octets

        @param byteIters: an iterator over the sequence of bytes containing
                          the ConnectReply PDU
        @type bytes: mms.iterator.PreviewIterator
        """
        self.serverSessionID = Decoder.decodeUintvar(byteIter)
        capabilitiesLen = Decoder.decodeUintvar(byteIter)
        headersLen = Decoder.decodeUintvar(byteIter)
        # Stub to decode capabilities (currently we ignore these)
        cFieldBytes = []
        for i in range(capabilitiesLen):
            cFieldBytes.append(byteIter.next())
        cIter = PreviewIterator(cFieldBytes)
        # Stub to decode headers (currently we ignore these)
        hdrFieldBytes = []
        for i in range(headersLen):
            hdrFieldBytes.append(byteIter.next())
        hdrIter = PreviewIterator(hdrFieldBytes)
    
    
    def _decodeReplyPDU(self, byteIter):
        """ The WSP Reply PDU is the generic response PDU used to return
        information from the server in response to a request. It is defined in
        WAP-230, section 8.2.3.3.
        
        All WSP PDU headers start with a type (uint8) byte (we do not
        implement connectionless WSP, thus we don't prepend TIDs to the WSP
        header). The WSP PDU types are specified in WAP-230, table 34.
        
        Reply PDU Fields::
         Name            Type
         =============== =================
         Status          Uint8
         HeadersLen      Uintvar
         ContentType     multiple octects
         Headers         <HeadersLen> - len(ContentType) octets
         Data            multiple octects

        @param byteIters: an iterator over the sequence of bytes containing
                          the ConnectReply PDU
        @type bytes: mms.iterator.PreviewIterator
        """
        status = Decoder.decodeUint8(byteIter)
        headersLen = Decoder.decodeUintvar(byteIter)
        
        # Stub to decode headers (currently we ignore these)
        hdrFieldBytes = []
        for i in range(headersLen):
            hdrFieldBytes.append(byteIter.next())
        hdrIter = PreviewIterator(hdrFieldBytes)
        contentType, parameters = Decoder.decodeContentTypeValue(hdrIter)
        while True:
            try:
                hdr, value = Decoder.decodeHeader(hdrIter)
            except StopIteration:
                break
        # Read the data
        data = []
        while True:
            try:
                data.append(byteIter.next())
            except StopIteration:
                break
    
    @staticmethod
    def _encodeCapabiltyClientSDUSize(size):
        """ Encodes the Client-SDU-Size capability (Client Service Data Unit);
        described in WAP-230, section 8.3.2.1
        
        This defines the maximum size (in octets) of WTP Service Data Units
        
        @param size: The requested SDU size to negotiate (in octets)
        @type size: int
        """
        identifier = Encoder.encodeShortInteger(0x00)
        parameters = Encoder.encodeUintvar(size)
        length = Encoder.encodeUintvar(len(identifier) + len(parameters))
        capability = length
        capability.extend(identifier)
        capability.extend(parameters)
        return capability
     
    @staticmethod
    def _encodeCapabilityServerSDUSize(size):
        """ Encodes the Client-SDU-Size capability (Server Service Data Unit);
        described in WAP-230, section 8.3.2.1.
        
        This defines the maximum size (in octets) of WTP Service Data Units
        
        @param size: The requested SDU size to negotiate (in octets)
        @type size: int
        """
        identifier = Encoder.encodeShortInteger(0x01)
        parameters = Encoder.encodeUintvar(size)
        length = Encoder.encodeUintvar(len(identifier) + len(parameters))
        capability = length
        capability.extend(identifier)
        capability.extend(parameters)
        return capability
