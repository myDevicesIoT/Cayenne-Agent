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


class PiFaceDigital(MCP23S17):
    def __init__(self, board=0):
        self.board = toint(board)
        MCP23S17.__init__(self, 0, 0x20 + toint(board))
        self.writeRegister(self.getAddress(self.IODIR, 0), 0x00) # Port A as output
        self.writeRegister(self.getAddress(self.IODIR, 8), 0xFF) # Port B as input
        self.writeRegister(self.getAddress(self.GPPU,  0), 0x00) # Port A PU OFF
        self.writeRegister(self.getAddress(self.GPPU,  8), 0xFF) # Port B PU ON
        
    def __str__(self):
        return "PiFaceDigital(%d)" % self.board 

