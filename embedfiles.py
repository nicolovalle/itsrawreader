#!/usr/bin/env python3

"""

embedfiles.py

Usage: ./myrawreader.py -r <file.raw> -d <dump.txt> [-o <outfile.raw>] 

Options:
    -h --help                Display this help
    -r <file.raw>            Raw data source
    -d <dum.txt>             Dumped text file
    -o <outfile.raw>         Output raw file [default: default]

"""

Info = """

    v1.2 - 17Jun22

     * Decoded GBT Words: RDH,.,IHW,TDH,TDT,DDW,CDW,DIA,STA (to be used with -e, -E)

     * TRIGGER LIST:      {0: 'ORB', 1: 'HB', 2: 'HBr', 3: 'HC', 4:'PhT', 5:'PP', 6:'Cal', 7:'SOT', 8:'EOT', 9:'SOC', 10:'EOC', 11:'TF', 12:'FErst', 13: 'cont', 14: 'running'}

     * TABLE FILE:
       A_       B_       C_               D_           E_         F_                   G_        H_       I_     J_  
       RDHfeeid,RDHorbit,RDHpacketcounter,RDHpagecount,RDHstopbit,RDHoffset_new_packet,RDHlinkid,RDHcruid,RDHtrg,RDHbc

     * APE Errors on APLIDE words not fully reliable. Raised as soon as an APE is in the first byte of GBT word.

     * --fromdump
       Be careful when using dumps together with options exploiting RDH offsets.
       The offsets are fake if the dump is a skimmed version of the raw file.
       
"""
 
import docopt
import sys
import os
import re

argv = docopt.docopt(__doc__,version="1.0")
rawfilename = str(argv["-r"])
dumptxtname = str(argv["-d"])
outfilename = str(argv["-o"])
if outfilename == 'default':
    outfilename = 'merged_'+rawfilename+'_'+dumptxtname+'.raw'



NEWWORDS = {}

### reading words form text

dumptxt = open(dumptxtname,'r')

Lines = dumptxt.readlines()

for L in Lines:
    
    if L[0:2] != '0x':
        continue

    L = L.replace("-.................","-00"*6)
    L = L.replace("-...","-00000000"*6)

    nonOffset = re.search(':.*',L).group(0)
    Offset = L.replace(nonOffset,'').replace('\n','')

    
    try:
        GBTword = re.search('.{2}-'*15+'.{2}',L).group(0).split('-')
        GBTword = [int(gbt,16) for gbt in GBTword]
    except:
        print(GBTword)
        GBTword = re.search('.{8}-'*15+'.{8}',L).group(0).split('-')
        GBTword = [int(gbt,2) for gbt in GBTword]

    NEWWORDS[int(Offset,16)] = GBTword



rawfile = open(rawfilename,'rb')
outfile = open(outfilename,'wb')

OFFSET = 0

for OS in NEWWORDS:


    Data = rawfile.read(OS - OFFSET)
    outfile.write(Data)
    Data = rawfile.read(16)
    outfile.write(bytearray(NEWWORDS[OS]))

    OFFSET = OS + 16

    


rawfile.close()
outfile.close()

