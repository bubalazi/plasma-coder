#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import time
import easygui as eg
import sys
from ConfigParser import SafeConfigParser

sys.dont_write_bytecode = True

__author__ = 'Lyuboslav Petrov'
__date__ = '01-10-2016'
__version__ = 1.0

TITLE = "Plasma GCode Parser"

class PlasmaGCodeParser():
    """
    A Gcode parser to convert gcode generated for a mill to gcode for a floating
    head plasma cutter.
    """
    def __init__(self):

        self._machine_config = None
        self._start_block = None
        self._end_block = None
        self._in_file = None
        self._out_file = None
        self._blocks = None
        self._work_blocks = None
        self._clean_code = None

    @property
    def machine_config(self):
        if self._machine_config is None:
            msg = "Please supply the machine configuration."
            ftypes = [["*.ini", "*.conf", "Configuration files"]  ]
            fname = eg.fileopenbox(msg=msg, title=TITLE, default='*',
                                        filetypes=ftypes)
            parser = SafeConfigParser()
            try:
                parser.read(fname)
            except:
                raise "Problem reading file"
            self._machine_config = parser
        return self._machine_config

    @property
    def start_block(self):
        if self._start_block is None:
            block = self.machine_config.get('routines', 'start').split('\n')
            self._start_block = [item + '\n' for item in block]
        return self._start_block

    @property
    def end_block(self):
        if self._end_block is None:
            block = self.machine_config.get('routines', 'end').split('\n')
            self._end_block = [item + '\n' for item in block]
        return self._end_block

    @property
    def in_file(self):
        if self._in_file is None:
            msg = "Find the GCode file to be converted"
            in_file = eg.fileopenbox(msg=msg, title=TITLE, default='*',
                                        filetypes=None)

            if in_file and len(in_file) > 1:
                self._in_file = open(in_file, 'r')
            else:
                msg = "No File found. Do you want to quit?"
                if not eg.ynbox(msg=msg, title=TITLE, choices=('Yes', 'No')):
                    self.in_file
                else:
                    sys.exit(0)
        return self._in_file

    @property
    def out_file(self):
        if self._out_file is None:
            msg = "Save File"
            out_file = eg.fileopenbox(msg=msg, title=TITLE, default='*',
                                        filetypes=None)

            if out_file and len(out_file) > 1:
                self._out_file = open(out_file, 'w')
            else:
                msg = "No File found. Do you want to quit?"
                if not eg.ynbox(msg=msg, title=TITLE, choices=('Yes', 'No')):
                    self.out_file
                else:
                    sys.exit(0)
        return self._out_file

    @property
    def blocks(self):
        if self._blocks is None:
            self._blocks = self.in_file.readlines()
        return self._blocks

    @property
    def work_blocks(self):
        if self._work_blocks is None:
            work_blocks = []
            startIndx = []
            for indx, block in enumerate(self.blocks):
                if self.is_work_block(block):
                    startIndx.append(indx)
                elif not self.is_work_block(block) and len(startIndx) > 0:
                    endIndx = indx
                    work_blocks.append([startIndx[0], endIndx])
                    startIndx = []
                else:
                    pass
            self._work_blocks = work_blocks
        return self._work_blocks

    @property
    def clean_code(self):
        if self._clean_code is None:
            self._clean_code = []
            for line in self.blocks:
                self._clean_code.append(self.clean_numbering(line))
            for indx, line in enumerate(self._clean_code):
                self._clean_code[indx] = self.clean_M3s(line)
            return self._clean_code

        return self._clean_code

    def is_number(self, character):
        try:
            int(character)
        except ValueError:
            return False
        return True

    def move_over_numbers(self, block, indx):
        while (self.is_number(block[indx]) or block[indx] == '.' or block[indx]==' ') and (indx < len(block)-1):
            indx += 1
        return indx

    def find_end_of_comment(self, block, indx):
        while not block[indx] == ')':
            indx += 1
        return indx + 1

    def crop_block(self, block, startIndx, endIndx):
        return block[0:startIndx] + block[endIndx:]

    def clean_comments(self, block):
        if '(' in block:
            startIndx = block.find('(')
            endIndx = self.find_end_of_comment(block, startIndx)
            block = self.crop_block(block, startIndx, endIndx)
        return block

    def clean_numbering(self, block):
        if 'N' in block.upper():
            startIndx = block.upper().find('N')
            endIndx = self.move_over_numbers(block, startIndx+1)
            block = self.crop_block(block, startIndx, endIndx)
        return block

    def add_numbering(self, code=None):
        pass

    def clean_M3s(self, block):

        if not 'M30' in block:
            m3 = ('M3' in block)
            m03 = ('M03' in block)

            if m3 or m03:
                if m3:
                    startIndx = block.upper().find('M3')
                else:
                    startIndx = block.upper().find('M03')
                endIndx = self.move_over_numbers(block, startIndx+1)
                block = self.crop_block(block, startIndx, endIndx)
        return block

    def is_work_block(self, block):

        g1 = 'G1' in block.upper()
        g2 = 'G2' in block.upper()
        g3 = 'G3' in block.upper()

        if g1 or g2 or g3:
            if g1:
                startIndx = block.upper().find('G1')
                if not self.is_number(block[startIndx+2]):
                    return True
                else:
                    return False
            if g2:
                startIndx = block.upper().find('G2')
                if not self.is_number(block[startIndx+2]):
                    return True
                else:
                    return False
            if g3:
                startIndx = block.upper().find('G3')
                if not self.is_number(block[startIndx+2]):
                    return True
                else:
                    return False
        else:
            return False

    def inject_code(self):

        blockIndx = 0
        for indx, block in enumerate(self.work_blocks):
            # Write out existing code up until the start of this workblock
            for lineIndx in range(blockIndx, block[0]):
                self.out_file.write(self.clean_code[lineIndx])
                blockIndx = block[1]+1
            # Inject plasma initialisation code prior the work block
            self.out_file.write('\n')
            self.out_file.write('(### Start WB {number} ###)\n'.format(number=indx))
            for cc in self.start_block:
                self.out_file.write(cc)
            self.out_file.write('(### ### ###)\n'.format(number=indx))
            self.out_file.write('\n')
            # Write out work block
            for lineIndx in range(block[0], block[1]):
                self.out_file.write(self.clean_code[lineIndx])
            # Inject plasma end-routines
            self.out_file.write('\n')
            self.out_file.write('(### End WB {number} ###)\n'.format(number=indx))
            for cc in self.end_block:
                self.out_file.write(cc)
            self.out_file.write('(### ### ###)\n'.format(number=indx))
            self.out_file.write('\n')

        # Last Step - Copy (&clean) the code from the end of the last workblock to the
        # end of the file
        for block in self.clean_code[self.work_blocks[-1][1]:]:
            self.out_file.write(block)

        self.out_file.close()


if __name__ == "__main__":
    parser = PlasmaGCodeParser()
    parser.inject_code()
