#!/usr/bin/env python3

"""

embedfiles.py

Usage: ./myrawreader.py [-r <file.raw>] -d <dump.txt> [-o <outfile.raw>] 

Options:
    -h --help                Display this help
    -r <file.raw>            Raw data source [default: none]
    -d <dum.txt>             Dumped text file
    -o <outfile.raw>         Output raw file [default: default]

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




outfile = open(outfilename,'wb')

OFFSET = 0

if (rawfilename != 'none'):

    rawfile = open(rawfilename,'rb')
    
    for OS in NEWWORDS:

        Data = rawfile.read(OS - OFFSET)
        outfile.write(Data)
        Data = rawfile.read(16)
        outfile.write(bytearray(NEWWORDS[OS]))

    OFFSET = OS + 16

    
    totalsize = os.path.getsize(rawfilename)

    Data = rawfile.read(totalsize - OFFSET)
    outfile.write(Data)

    rawfile.close()

else:

    for OS in NEWWORDS:
        outfile.write(bytearray(NEWWORDS[OS]))
        

outfile.close()

