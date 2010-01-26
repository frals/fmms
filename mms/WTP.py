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
for standalone use.

@author: Francois Aucamp <faucamp@csir.co.za>
@author: Nick Leppänen Larsson <frals@frals.se>
@license: GNU LGPL
"""
import sys
import array
import socket, time
from iterator import PreviewIterator

class WTP:
    """ This class implements a very limited subset of the WTP layer """
    pduTypes = {0x00: None, # Not Used
                0x01: 'Invoke',
                0x02: 'Result',
                0x03: 'Ack',
                0x04: 'Abort',
                0x05: 'Segmented Invoke',
                0x06: 'Segmented Result',
                0x07: 'Negative Ack'}
    
    abortTypes = {0x00: 'PROVIDER',
                  0x01: 'USER'}
    
    abortReasons = {0x00: 'UNKNOWN',
                    0x01: 'PROTOERR',
                    0x02: 'INVALIDTID',
                    0x03: 'NOTIMPLEMENTEDCL2',
                    0x04: 'NOTIMPLEMENTEDSAR',
                    0x05: 'NOTIMPLEMENTEDUACK',
                    0x06: 'WTPVERSIONONE',
                    0x07: 'CAPTEMPEXCEEDED',
                    0x08: 'NORESPONSE',
                    0x09: 'MESSAGETOOLARGE',
                    0x10: 'NOTIMPLEMENTEDESAR'}
    
    def __init__(self, gatewayHost, gatewayPort=9201):
        self.udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.tidCounter = 0
        # Currently "active" WTP transactions (their IDs)
        self.activeTransactions = []
        self.gatewayHost = gatewayHost
        self.gatewayPort = gatewayPort
    
    def invoke(self, wspPDU):
        """ Invoke (send) a request via WTP, and get the response.
        
        This method automatically assigns a new unique transaction ID to the 
        transmitted PDU.
        
        @return: an iterator over the bytes read from the response
        @rtype: mms.iterator.previewIterator
        """
        self.tidCounter += 1
        print '>> WTP: Invoke, transaction ID: %d' % self.tidCounter
        pdu = self.encodeInvokePDU(self.tidCounter) + wspPDU
        self._sendPDU(pdu)
        print '>> WTP: Sent PDU'
        self.activeTransactions.append(self.tidCounter)    
        return self._parseResponse(self._receiveData())
    
    def ack(self, transactionID):
        print '>> WTP: Ack, transaction ID: %d' % transactionID
        self._sendPDU(self.encodeAckPDU(transactionID))
        
    def _sendPDU(self, pdu):
        """ Transmits a PDU through the socket
        
        @param pdu: The PDU to send (a sequence of bytes)
        @type pdu: list
        """
        data = ''
        for char in pdu:
            data += chr(char)
        self.udpSocket.sendto(data, (self.gatewayHost, self.gatewayPort))
    
    def _receiveData(self):
        """ Read data from the UDP socket
        
        @return: The data read from the socket
        @rtype: str
        """
        #done = False
        done = True
        response = ''
        print '>> WTP: Receiving data'
        while not done:
            buff = self.udpSocket.recv(1024)
            print buff
            response += buff
            if len(buff) < 1024:
                done = True
        return response

    def _parseResponse(self, responseData):
        """ Interpret data read from the socket (at the WTP layer level) 
        
        @param responseData: A buffer containing data to interpret
        @type responseData: str
        """
        byteArray = array.array('B')
        print responseData
        for char in responseData:
            byteArray.append(ord(char))
        byteIter = PreviewIterator(byteArray)
        pduType, transactionID = self._decodePDU(byteIter)
        if pduType == 'Result':
            self.ack(transactionID)
        return byteIter
        
    
    @staticmethod
    def encodeInvokePDU(tid):
        """ Builds a WTP Invoke PDU
        
        @param tid: The transaction ID for this PDU
        @type tid: int
        
        @return: the WTP invoke PDU as a sequence of bytes
        @rtype: list
        
        The WTP Invoke PDU structure is defined in WAP-224, section 8.3.1::
             Bit| 0 |  1  |  2   |  3   |  4   | 5 | 6 | 7
         Octet  |   |     |      |      |      |   |   |
         1      |CON|    PDU Type = Invoke     |GTR|TDR|RID
         2      |                TID
         3      |
         4      |Version  |TIDnew| U/P  |  RES |RES|  TCL
         
         ...where bit 0 is the most significant bit.
        
        Invoke PDU type = 0x01 = 0 0 0 1
        GTR  is 0 and TDR is 1  (check: maybe make both 1: segmentation not supported)
        RID is set to 0 (not retransmitted)
        TCL is 0x02  == 1 0 (transaction class 2)
        Version is 0x00 (according to WAP-224, section 8.3.1)
        Thus, for our Invoke, this is::
             Bit| 0 |  1  |  2   |  3   |  4   | 5 | 6 | 7
         Octet  |   |     |      |      |      |   |   |
         1      | 0 |  0  |  0   |  0   |  1   | 0 | 1 | 0
         2      |   TID
         3      |   TID
         4      | 0 |  0  |  0   |  1   |  0   | 0 | 1 | 0 
        """
        #TODO: check GTR and TDR values (probably should rather be 11, for segmentation not supported)
        pdu = [0x0a] # 0000 1010
        pdu.extend(WTP._encodeTID(tid))
        pdu.append(0x12) # 0001 0010
        return pdu
    
    @staticmethod
    def encodeAckPDU(tid):
        """ Builds a WTP Ack PDU (acknowledge)
        
        @param tid: The transaction ID for this PDU
        @type tid: int
        
        @return: the WTP invoke PDU as a sequence of bytes
        @rtype: list
        
        The WTP PDU structure is defined in WAP-224, section 8
        The ACK PDU structure is described in WAP-224, section 8.3.3::
             Bit| 0 |  1  |  2   |  3   |  4   |   5   | 6 | 7
         Octet  |   |     |      |      |      |       |   |
         1      |CON|PDU Type = Acknowledgement|Tve/Tok|RES|RID
         2                       TID
         3

         ...where bit 0 is the most significant bit.
        
        Thus, for our ACK, this is::
             Bit| 0 |  1  |  2   |  3   |  4   | 5 | 6 | 7
         Octet  |   |     |      |      |      |   |   |
         1      | 0 |  0  |  0   |   1  |   1  | 0 | 0 | 0
                    |  PDU type = 0x03 = 0011  |
         2         TID
         3         TID
        """
        pdu = [0x18] # binary: 00011000
        pdu.extend(WTP._encodeTID(tid))
        return pdu
    
    def _decodePDU(self, byteIter):
        """ Reads and decodes a WTP PDU from the sequence of bytes starting at
        the byte pointed to by C{dataIter.next()}.
        
        @param byteIter: an iterator over a sequence of bytes
        @type byteIteror: mms.iterator.PreviewIterator
        
        @note: If the PDU type is correctly determined, byteIter will be
               modified in order to read past the amount of bytes required
               by the PDU type.
        
        @return: The PDU type, and the transaction ID, in the format:
                 (str:<pdu_type>, int:<transaction_id>)
        @rtype: tuple
        """
        byte = byteIter.preview()
        byteIter.resetPreview()
        # Get the PDU type
        pduType = (byte >> 3) & 0x0f
        pduValue = (None, None)
        if pduType not in WTP.pduTypes:
            #TODO: maybe raise some error or something
            print 'Error - unknown WTP PDU type: %s' % hex(pduType)
        else:
            print '<< WTP: %s' % WTP.pduTypes[pduType],
            try:
                exec 'pduValue = self._decode%sPDU(byteIter)' % WTP.pduTypes[pduType]
            except:
                print 'A fatal error occurred, probably due to an unimplemented feature.\n'
                raise
        # after this follows the WSP pdu(s)....
        return pduValue
    
    def _decodeResultPDU(self, byteIter):
        """ Decodes a WTP Result PDU
        
        @param byteIter: an iterator over a sequence of bytes
        @type byteIteror: mms.iterator.PreviewIterator
        
        The WTP Result PDU structure is defined in WAP-224, section 8.3.2::
             Bit| 0 |  1  |  2   |  3   |  4   |   5   | 6 | 7
         Octet  |   |     |      |      |      |       |   |
         1      |CON|    PDU Type = Result     |Tve/Tok|RES|RID
         2                       TID
         3
        
        The WTP Result PDU Type is 0x02, according to WAP-224, table 11
        """
        # Read in 3 bytes
        bytes = []
        for i in range(3):
            bytes.append(byteIter.next())
        pduType = (bytes[0] >> 3) & 0x0f
        # Get the transaction ID
        transactionID = WTP._decodeTID(bytes[1:])
        print 'transaction ID: %d' % transactionID
        if transactionID in self.activeTransactions:
            self.activeTransactions.remove(transactionID)
        return (WTP.pduTypes[pduType], transactionID)
    
    def _decodeAckPDU(self, byteIter):
        """ Decodes a WTP Result PDU
        
        @param byteIter: an iterator over a sequence of bytes
        @type byteIteror: mms.iterator.PreviewIterator
        
        The ACK PDU structure is described in WAP-224, section 8.3.3::
             Bit| 0 |  1  |  2   |  3   |  4   |   5   | 6 | 7
         Octet  |   |     |      |      |      |       |   |
         1      |CON|PDU Type = Acknowledgement|Tve/Tok|RES|RID
         2                       TID
         3
        
        The WTP Result PDU Type is 0x03, according to WAP-224, table 11
        """
        # Read in 3 bytes
        bytes = []
        for i in range(3):
            bytes.append(byteIter.next())
        pduType = (bytes[0] >> 3) & 0x0f
        # Get the transaction ID
        transactionID = WTP._decodeTID(bytes[1:])
        print 'transaction ID: %d' % transactionID
        if transactionID not in self.activeTransactions:
            self.activeTransactions.append(transactionID)
        return (WTP.pduTypes[pduType], transactionID)
    
    def _decodeAbortPDU(self, byteIter):
        """ Decodes a WTP Abort PDU
        
        @param byteIter: an iterator over a sequence of bytes
        @type byteIteror: mms.iterator.PreviewIterator
        
        The WTP Result PDU structure is defined in WAP-224, section 8.3.2::
             Bit| 0 |  1  |  2   |  3   |  4   |   5   | 6 | 7
         Octet  |   |     |      |      |      |       |   |
         1      |CON|    PDU Type = Result     |   Abort type
         2                       TID
         3
         4                  Abort reason
        
        The WTP Abort PDU Type is 0x04, according to WAP-224, table 11
        """
        # Read in 4 bytes
        bytes = []
        for i in range(4):
            bytes.append(byteIter.next())
        pduType = (bytes[0] >> 3) & 0x0f
        abortType = bytes[0] & 0x07
        abortReason = bytes[3]
        if abortType in self.abortTypes:
            abortType = self.abortTypes[abortType]
        else:
            abortType = str(abortType)
        if abortReason in self.abortReasons:
            abortReason = self.abortReasons[abortReason]
        else:
            abortReason = str(abortReason)
        # Get the transaction ID
        transactionID = WTP._decodeTID(bytes[1:3])
        print 'transaction ID: %d' % transactionID
        if transactionID in self.activeTransactions:
            self.activeTransactions.remove(transactionID)
        print 'WTP: Abort, type: %s, reason: %s' % (abortType, abortReason)
        return (WTP.pduTypes[pduType], transactionID)
    
    @staticmethod
    def _encodeTID(transactionID):
        """ Encodes the specified transaction ID into the format used in
        WTP PDUs (makes sure it spans 2 bytes)
        
        From WAP-224, section 7.8.1: The TID is 16-bits but the high order bit
        is used to indicate the direction. This means that the TID space is
        2**15. The TID is an unsigned integer.
        
        @param transactionID: The transaction ID to encode
        @type transactionID: int
        
        @return: The encoded transaction ID as a sequence of bytes
        @rtype: list
        """
        if transactionID > 0x7FFF:
            raise ValueError, 'Transaction ID too large (must fit into 15 bits): %d' % transactionID
        else:
            encodedTID = [transactionID & 0xFF]
            encodedTID.insert(0, transactionID >> 8)
            return encodedTID

    @staticmethod
    def _decodeTID(bytes):
        """ Decodes the transaction ID contained in <bytes>
        
        From WAP-224, section 7.8.1: The TID is 16-bits but the high order bit
        is used to indicate the direction. This means that the TID space is
        2**15. The TID is an unsigned integer.

        @param bytes: The byte sequence containing the transaction ID
        @type bytes: list
        
        @return: The decoded transaction ID
        @rtype: int
        """
        tid = bytes[0] << 8
        tid |= bytes[1]
        # make unsigned
        tid &= 0x7f
        return tid
