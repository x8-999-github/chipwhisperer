#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2014, NewAE Technology Inc
# All rights reserved.
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================
import logging

from usb import USBError

import binascii
from ._base import TargetTemplate
from chipwhisperer.common.utils import pluginmanager
from simpleserial_readers.cwlite import SimpleSerial_ChipWhispererLite
from chipwhisperer.common.utils.parameter import setupSetParam


class SimpleSerial(TargetTemplate):
    _name = "Simple Serial"

    def __init__(self):
        TargetTemplate.__init__(self)

        ser_cons = pluginmanager.getPluginsInDictFromPackage("chipwhisperer.capture.targets.simpleserial_readers", True, False)
        self.ser = ser_cons[SimpleSerial_ChipWhispererLite._name]

        self.keylength = 16
        self.textlength = 16
        self.outputlength = 16
        self.input = ""
        self.protver = ''
        self.protformat = 'hex'

        # Preset lists are in the form
        # {'Dropdown Name':['Init Command', 'Load Key Command', 'Load Input Command', 'Go Command', 'Output Format']}
        # If a command is None, it's left unchanged and the text field is editable;
        # Otherwise, it's loaded with the value and set to readonly
        self.presets = {
            'Custom':[None, None, None, None, None],
            'SimpleSerial Encryption':['','k$KEY$\\n', '', 'p$TEXT$\\n', 'r$RESPONSE$\\n'],
            'SimpleSerial Authentication':['','k$KEY$\\n', 't$EXPECTED$\\n', 'p$TEXT$\\n', 'r$RESPONSE$\\n'],
            'Glitching':[None, None, None, None, '$GLITCH$\\n'],
        }
        self._preset = 'Custom'

        self.params.addChildren([
            {'name':'Connection', 'type':'list', 'key':'con', 'values':ser_cons, 'get':self.getConnection, 'set':self.setConnection},
            {'name':'Key Length (Bytes)', 'type':'list', 'values':[8, 16, 32], 'get':self.keyLen, 'set':self.setKeyLen},
            {'name':'Input Length (Bytes)', 'type':'list', 'values':[1, 2, 4, 8, 16, 32], 'default':16, 'get':self.textLen, 'set':self.setTextLen},
            {'name':'Output Length (Bytes)', 'type':'list', 'values':[8, 16, 32], 'default':16, 'get':self.outputLen, 'set':self.setOutputLen},
            # {'name':'Plaintext Command', 'key':'ptcmd', 'type':'list', 'values':['p', 'h'], 'value':'p'},
            {'name':'Protocol Version', 'key':'proto', 'type':'group', 'expanded':True, 'children':[
                {'name':'Version', 'key':'ver', 'type':'list', 'values':['1.0', '1.1', 'auto'], 'value':'auto'},
                {'name':'Timeout (ms)', 'key':'timeout', 'type':'int', 'value':20, 'range':(0, 500), 'step':1},
            ]},
            {'name':'Preset Mode', 'key': 'preset', 'type': 'list', 'values': self.presets, 'get': self.getPreset, 'set': self.setPreset},
            {'name':'Init Command', 'key':'cmdinit', 'type':'str', 'value':''},
            {'name':'Load Key Command', 'key':'cmdkey', 'type':'str', 'value':'k$KEY$\\n'},
            {'name':'Load Input Command', 'key':'cmdinput', 'type':'str', 'value':''},
            {'name':'Go Command','key':'cmdgo', 'type':'str', 'value':'p$TEXT$\\n'},
            {'name':'Output Format', 'key':'cmdout', 'type':'str', 'value':'r$RESPONSE$\\n'},
            {'name':'Protocol format', 'type':'list', 'values':['bin','hex'], 'get':self.protFormat, 'set':self.setProtFormat, 'help':"Assume the protocol to be in the given format. The original SimpleSerial module assumed that the keys where to be sent in hex format but in some situations it is needed to conver the contents to a binary string representation"}
            #{'name':'Data Format', 'key':'datafmt', 'type':'list', 'values':{'DEADBEEF':'',
            #                                                                 'DE AD BE EF':' ',
            #                                                                 'DE:AD:BE:EF':':',
            #                                                                 'DE-AD-BE-EF':'-'}, 'value':''},
        ])

        self.setConnection(self.ser, blockSignal=True)

    @setupSetParam("Key Length")
    def setKeyLen(self, klen):
        """ Set key length in bytes """
        self.keylength = klen

    def keyLen(self):
        """ Return key length in bytes """
        return self.keylength

    @setupSetParam("Input Length")
    def setTextLen(self, tlen):
        """ Set plaintext length. tlen given in bytes """
        self.textlength = tlen

    def textLen(self):
        """ Return plaintext length in bytes """
        return self.textlength

    @setupSetParam("Output Length")
    def setOutputLen(self, tlen):
        """ Set plaintext length in bytes """
        self.outputlength = tlen

    def outputLen(self):
        """ Return output length in bytes """
        return self.outputlength

    @setupSetParam("Protocol format")
    def setProtFormat(self, protformat):
        """ Set the protocol format used 'bin' or 'hex' """
        self.protformat = protformat

    def protFormat(self):
        """ Return the protocol format used 'bin' or 'hex' """
        return self.protformat

    @setupSetParam("Preset")
    def setPreset(self, mode):
        self._preset = mode
        settings = ['cmdinit', 'cmdkey', 'cmdinput', 'cmdgo', 'cmdout']
        values = mode
        for i in range(len(settings)):
            try:
                if values[i] is None:
                    self.findParam(settings[i]).setReadonly(False)
                else:
                    self.findParam(settings[i]).setReadonly(False)
                    self.findParam(settings[i]).setValue(values[i])
                    self.findParam(settings[i]).setReadonly(True)
            except KeyError as e:
                # This happens at startup when this parameter is being loaded before the text settings are ready
                logging.debug("SimpleSerial: could not find parameters for preset settings")
                pass

    def getPreset(self):
        return self._preset

    def getConnection(self):
        return self.ser

    @setupSetParam("Connection")
    def setConnection(self, con):
        self.ser = con
        self.params.append(self.ser.getParams())

        self.ser.connectStatus.setValue(False)
        self.ser.connectStatus.connect(self.connectStatus.emit)
        self.ser.selectionChanged()

    def _con(self, scope = None):
        if not scope or not hasattr(scope, "qtadc"): Warning("You need a scope with OpenADC connected to use this Target")

        self.outstanding_ack = False

        self.ser.con(scope)
        # 'x' flushes everything & sets system back to idle
        self.ser.write("xxxxxxxxxxxxxxxxxxxxxxxx")
        self.ser.flush()


    def close(self):
        if self.ser != None:
            self.ser.close()

    def getVersion(self):
        self.ser.flush()
        self.ser.write("v\n")
        t_ms = ver = self.findParam(['proto', 'timeout']).getValue()
        data = self.ser.read(4, timeout=t_ms)

        if len(data) > 1 and data[0] == 'z':
            self.protver = '1.1'
            logging.info("SimpleSerial: protocol V1.1 detected")
        else:
            self.protver = '1.0'
            logging.info("SimpleSerial: protocol V1.0 detected")

    def init(self):
        self.ser.flush()
        ver = self.findParam(['proto', 'ver']).getValue()
        if ver == 'auto':
            self.getVersion()
        else:
            self.protver = ver
        self.outstanding_ack = False

        self.runCommand(self.findParam('cmdinit').getValue())

    def setModeEncrypt(self):
        pass

    def setModeDecrypt(self):
        pass

    def convertVarToString(self, var):
        if isinstance(var, str):
            return var

        sep = ""
        s = sep.join(["%02x"%b for b in var])
        return s

    def runCommand(self, cmdstr, flushInputBefore=True):
        if self.connectStatus.value()==False:
            raise Warning("Can't write to the target while disconected. Connect to it first.")

        if cmdstr is None or len(cmdstr) == 0:
            return

        # Protocol version 1.1 waits for ACK - if we have outstanding ACK, wait now
        if self.protver == '1.1':
            if self.outstanding_ack:
                # TODO - Should be user-defined maybe
                data = self.ser.read(4, timeout=500)
                if len(data) > 1:
                    if data[0] != 'z':
                        logging.error("SimpleSerial: ACK ERROR, read %02x" % ord(data[0]))
                else:
                    logging.error("SimpleSerial: ACK ERROR, did not see anything - TIMEOUT possible!")
                self.outstanding_ack = False

        varList = [("$KEY$",self.key, "Hex Encryption Key"),
                   ("$TEXT$",self.input, "Input Plaintext"),
                   ("$EXPECTED$", self.getExpected(), "Expected Ciphertext")]

        newstr = cmdstr

        #Find variables to insert
        for v in varList:
            if v[1] is not None:
                newstr = newstr.replace(v[0], self.convertVarToString(v[1]))

        #This is dumb
        newstr = newstr.replace("\\n", "\n")
        newstr = newstr.replace("\\r", "\r")

        #print newstr
        try:
            if flushInputBefore:
                self.ser.flushInput()
            if self.protformat == "bin":
                newstr = binascii.unhexlify(newstr)
            self.ser.write(newstr)
        except USBError:
            self.dis()
            raise Warning("Error in the target. It may have been disconnected.")
        except Exception as e:
            self.dis()
            raise e
        if self.protver == '1.1':
            self.outstanding_ack = True

    def loadEncryptionKey(self, key):
        self.key = key
        if self.key:
            self.runCommand(self.findParam('cmdkey').getValue())

    def loadInput(self, inputtext):
        self.input = inputtext
        self.runCommand(self.findParam('cmdinput').getValue())

    def isDone(self):
        return True

    def readOutput(self):
        dataLen= self.outputlength*2

        fmt = self.findParam('cmdout').getValue()
        #This is dumb
        fmt = fmt.replace("\\n", "\n")
        fmt = fmt.replace("\\r", "\r")

        if len(fmt) == 0:
            return None

        if fmt.startswith("$GLITCH$"):

            try:
                databytes = int(fmt.replace("$GLITCH$",""))
            except ValueError:
                databytes = 64


            self.newInputData.emit(self.ser.read(databytes))
            return None

        dataLen += len(fmt.replace("$RESPONSE$", ""))
        expected = fmt.split("$RESPONSE$")

        #Read data from serial port
        response = self.ser.read(dataLen, timeout=500)

        # If the protocol format is bin convert is back to hex for handling by CW
        if self.protformat == "bin":
            response = binascii.hexlify(response)

        if len(response) < dataLen:
            logging.warning('Response length from target shorter than expected (%d<%d): "%s".' % (len(response), dataLen, response))
            return None

        #Go through...skipping expected if applicable
        #Check expected first

        #Is a beginning part
        if len(expected[0]) > 0:
            if response[0:len(expected[0])] != expected[0]:
                print("Sync Error: %s"%response)
                print("Hex Version: %s" % (" ".join(["%02x" % ord(t) for t in response])))

                return None

        startindx = len(expected[0])

        #Is middle part?
        data = bytearray(self.outputlength)
        if len(expected) == 2:
            for i in range(0,self.outputlength):
                data[i] = int(response[(i * 2 + startindx):(i * 2 + startindx + 2)], 16)

            startindx += self.outputlength*2

        #Is end part?
        if len(expected[1]) > 0:
            if response[startindx:startindx+len(expected[1])] != expected[1]:
                print("Sync Error: %s"%response)
                return None

        return data

    def go(self):
        self.runCommand(self.findParam('cmdgo').getValue())

    def checkEncryptionKey(self, kin):
        blen = self.keyLen()

        if len(kin) < blen:
            logging.warning('Padding key...')
            newkey = bytearray(kin)
            newkey += bytearray([0]*(blen - len(kin)))
            return newkey
        elif len(kin) > blen:
            logging.warning('Truncating key...')
            return kin[0:blen]

        return kin

    def checkPlaintext(self, text):
        blen = self.textLen()

        if len(text) < blen:
            logging.warning('Padding plaintext...')
            newtext = bytearray(text)
            newtext += bytearray([0] * (blen - len(text)))
            return newtext
        elif len(text) > blen:
            logging.warning('Truncating plaintext...')
            return text[0:blen]
        return text

    def getExpected(self):
        """Based on key & text get expected if known, otherwise returns None"""
        if self.textLen() == 16:
            return TargetTemplate.getExpected(self)
        else:
            return None
