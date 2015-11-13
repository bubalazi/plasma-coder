# -*- coding: utf8 -*-
import os
import time
import easygui as eg
import sys

__author__ = 'Lyuboslav Petrov'


class PlasmaGCodeParser():
    """
    A Gcode parser to modify gcode for a floating head plasma cutter.

    +-------------+     +------------------+     +-----------------------------------+
    |Vectric GCode|     |Remove Redundant  |     |Determine the location (in code) of|
    |for Mach2/3  +----->words: Numbers,   +----->of the separate parts and inject   |
    |Mill         |     |Feedrates, M3's   |     |plasma workflow                    |
    +-------------+     +------------------+     +-----------------------------------+

    """
    def __init__(self):

        self.title = "Plasma GCode Parser"
        self.inFileName = self.getInFileName()
        self.fidin = open(self.inFileName, 'r')
        self.blocks = self.fidin.readlines()
        self.cleanCode = self.cleanBlocks()
        self.outFileName = self.getOutFileName()
        self.fidout = open(self.outFileName, 'w')
        self.fidout.write('( This is a modified Vectric-generated Gcode file )\n')
        self.fidout.write('( %s )\n' % time.ctime())
        self.workBlocks = self.getWorkBlocks()
        self.workBlockCount = len(self.workBlocks)

        self.startWorkBlock = [
            "G31Z-30\n"           # Descend for material probe
            "G91\n"               # Set to incremental mode
            "G0Z15.00\n"          # Ascend to TOM (top of material)
            "G00Z0.00\n"          # Set Z software 0
            "M3\n"                # Start torch
            "G4P250\n"            # Wait for ms
            "G90\n"               # Set to absolute mode
        ]
        self.endWorkBlock = [
            "M5\n"                # Stop Torch
        ]

    def getInFileName(self):
        msg = "Find the GCode file to be converted"
        inFileName = eg.fileopenbox(msg=msg, title=self.title, default='*',
                                    filetypes=None)

        if inFileName and len(inFileName) > 1:
            return inFileName
        else:
            msg = "No File found. Do you want to quit?"
            response = eg.ynbox(msg=msg, title=self.title,
                                choices=('Yes', 'No'))
            if response:
                self.getInFileName()
            else:
                sys.exit(0)

    def getOutFileName(self):
        msg = "Save File"
        default = self.inFileName
        outFileName = eg.filesavebox(msg=msg,
                                     title=self.title,
                                     default=default,
                                     filetypes=['.nc', '.gcode', '.ngc'])

        if outFileName and len(outFileName) > 1:
            return outFileName
        else:
            msg = "No File defined. Do you want to quit?"
            response = eg.ynbox(msg=msg,
                                title=self.title,
                                choices=('Yes', 'No'))
            if not response:
                self.getOutFileName()
            else:
                sys.exit(0)

    def gCodeParser(self):
        pass

    def isNumber(self, character):
        try:
            int(character)
            return True
        except ValueError:
            return False

    def moveOverNumbers(self, block, indx):
        while (self.isNumber(block[indx]) or block[indx] == '.' or block[indx]==' ') and (indx < len(block)-1):
            indx += 1
        return indx

    def findEndOfComment(self, block, indx):
        while not block[indx] == ')':
            indx += 1
        return indx + 1

    def cropBlock(self, block, startIndx, endIndx):
        return block[0:startIndx] + block[endIndx:]

    def cleanComments(self, block):
        if '(' in block:
            startIndx = block.find('(')
            endIndx = self.findEndOfComment(block, startIndx)
            block = self.cropBlock(block, startIndx, endIndx)
        return block

    def cleanNumbering(self, block):
        if 'N' in block.upper():
            startIndx = block.upper().find('N')
            endIndx = self.moveOverNumbers(block, startIndx+1)
            block = self.cropBlock(block, startIndx, endIndx)
        return block

    def addNumbering(self, code=None):
        pass

    def cleanM3s(self, block):

        if not 'M30' in block:
            m3 = ('M3' in block)
            m03 = ('M03' in block)

            if m3 or m03:
                if m3:
                    startIndx = block.upper().find('M3')
                else:
                    startIndx = block.upper().find('M03')
                endIndx = self.moveOverNumbers(block, startIndx+1)
                block = self.cropBlock(block, startIndx, endIndx)
        return block

    def cleanBlocks(self):
        clean = []
        for line in self.blocks:
            clean.append(self.cleanNumbering(line))

        for indx, line in enumerate(clean):
            clean[indx] = self.cleanM3s(line)

        return clean

    def isWorkBlock(self, block):

        g1 = 'G1' in block.upper()
        g2 = 'G2' in block.upper()
        g3 = 'G3' in block.upper()

        if g1 or g2 or g3:
            if g1:
                startIndx = block.upper().find('G1')
                if not self.isNumber(block[startIndx+2]):
                    return True
                else:
                    return False
            if g2:
                startIndx = block.upper().find('G2')
                if not self.isNumber(block[startIndx+2]):
                    return True
                else:
                    return False
            if g3:
                startIndx = block.upper().find('G3')
                if not self.isNumber(block[startIndx+2]):
                    return True
                else:
                    return False
        else:
            return False

    def getWorkBlocks(self):
        workBlocks = []
        startIndx = []
        for indx, block in enumerate(self.blocks):
            if self.isWorkBlock(block):
                startIndx.append(indx)
            elif not self.isWorkBlock(block) and len(startIndx) > 0:
                endIndx = indx
                workBlocks.append([startIndx[0], endIndx])
                startIndx = []
            else:
                pass
        return workBlocks

    def injectCode(self):

        blockIndx = 0

        for block in self.workBlocks:
            # Write out existing code up until the start of this workblock
            for lineIndx in range(blockIndx, block[0]):
                self.fidout.write(self.cleanCode[lineIndx])
                blockIndx = block[1]+1
            # Inject plasma initialisation code prior the work block
            self.fidout.write('\n')
            self.fidout.write('(###Injected code below###)\n')
            for customBlockCode in self.startWorkBlock:
                self.fidout.write(customBlockCode)
            self.fidout.write('(###Injected code above###)\n')
            self.fidout.write('\n')
            # Write out work block
            for lineIndx in range(block[0], block[1]):
                self.fidout.write(self.cleanCode[lineIndx])
            # Inject plasma end-routines
            self.fidout.write('\n')
            self.fidout.write('(###Injected code below###)\n')
            for customBlockCode in self.endWorkBlock:
                self.fidout.write(customBlockCode)
            self.fidout.write('(###Injected code above###)\n')
            self.fidout.write('\n')

        # Last Step - Copy (&clean) the code from the end of the last workblock to the
        # end of the file
        for block in self.cleanCode[self.workBlocks[-1][1]:]:
            self.fidout.write(block)

        self.fidout.close()


if __name__ == "__main__":
    parser = PlasmaGCodeParser()
    parser.injectCode()
