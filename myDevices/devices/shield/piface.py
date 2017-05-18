#   Copyright 2012-2013 Eric Ptak - trouch.com
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from myDevices.utils.types import M_JSON, toint
from myDevices.devices.digital.mcp23XXX import MCP23S17
from myDevices.decorators.rest import request, response


class PiFaceDigital():
    def __init__(self, board=0):
        mcp = MCP23S17(0, 0x20+toint(board))
        mcp.writeRegister(mcp.getAddress(mcp.IODIR, 0), 0x00) # Port A as output
        mcp.writeRegister(mcp.getAddress(mcp.IODIR, 8), 0xFF) # Port B as input
        mcp.writeRegister(mcp.getAddress(mcp.GPPU,  0), 0x00) # Port A PU OFF
        mcp.writeRegister(mcp.getAddress(mcp.GPPU,  8), 0xFF) # Port B PU ON
        self.mcp = mcp
        self.board = toint(board)
        
    def __str__(self):
        return "PiFaceDigital(%d)" % self.board 

    def __family__(self):
        return "GPIOPort"
    
    def checkChannel(self, channel):
#        if not channel in range(8):
        if not channel in range(16):
            raise ValueError("Channel %d invalid" % channel)
    
    #@request("GET", "%(channel)d/value")
    @response("%d")
    def digitalRead(self, channel):
        self.checkChannel(channel)
#        return not self.mcp.digitalRead(channel+8)
        return self.mcp.digitalRead(channel)
    
    #@request("POST", "%(channel)d/value/%(value)d")
    @response("%d")
    def digitalWrite(self, channel, value):
        self.checkChannel(channel)
        return self.mcp.digitalWrite(channel, value)
    
#    #@request("GET", "digital/output/%(channel)d")
#    @response("%d")
#    def digitalReadOutput(self, channel):
#        self.checkChannel(channel)
#        return self.mcp.digitalRead(channel)
    
#    #@request("GET", "digital/*")
#    @response(contentType=M_JSON)
#    def readAll(self):
#        inputs = {}
#        outputs = {}
#        for i in range(8):
#            inputs[i] = self.digitalRead(i)
#            outputs[i] = self.digitalReadOutput(i)
#        return {"input": inputs, "output": outputs}

    #@request("GET", "*")
    @response(contentType=M_JSON)
    def readAll(self):
#        inputs = {}
#        outputs = {}
#        for i in range(8):
#            inputs[i] = self.digitalRead(i)
#            outputs[i] = self.digitalReadOutput(i)
#        return {"input": inputs, "output": outputs}

        values = {}
        for i in range(16):
            values[i] = {"function": self.mcp.getFunctionString(i), "value": int(self.mcp.digitalRead(i))}
        return values

    #@request("GET", "count")
    @response("%d")
    def digitalCount(self):
        return 16
