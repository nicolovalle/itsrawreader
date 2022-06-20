#!/usr/bin/env python3

"""

myrawreader.py

Usage: ./myrawreader.py -f <file.raw> [--fromdump] [-e <excludedwords>] [-E <skippedwords>] [-l <lane>] [-i <feeid>] [-o <offset>] [-r <range>] [-O <orbit>] [--message] [--onlyRDH] [--info] [--dumpbin] [--printtable] [--silent] 

Options:
    -h --help                Display this help
    -f <file.raw>            Raw ITS data file
    --fromdump               Use text output of this script as input [default: False]
    -e <excludedwords>       Comma separated list of GBT words not to print [default: none]
    -E <skippedwords>        Comma separated list of GBT words not to decode. Overrides -e [default: none]
    -l <lane>                Comma separated list of HW lanes to print [default: -1]
    -i <feeid>               Comma separated list of feeids to decode (0x format). It uses RDH offset [default: -1]
    -o <offset>              Read from n-th byte (0x format) [default: 0x0]
    -r <range>               Interval of GBT words around the offset (format -n:+m) [default: 0:-1]
    -O <orbit>               Comma seprated list of orbits to decode (0x format) or range (0xABC:0xABC). It uses RDH offset [default: -1]
    --message                Skip data word without problems [default: False]
    --onlyRDH                Read RDH only (skip words according to RDH offset) [default: False]
    --info                   Print info and exit [default: False]    
    --dumpbin                Print ALPIDE words bit by bit [default: False]  
    --printtable             Print RDH summary on text file (name: myrr_table_<filename>.txt). See --info. [default: False]
    --silent                 Do not print [default: False]

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
rawfilename = str(argv["-f"])
fromdump = bool(argv["--fromdump"])
if fromdump:
    import numpy
print_only_message = bool(argv["--message"])
nonprinted_words = str(argv["-e"])
skipped_words = str(argv["-E"])
lanes_to_print = [int (LL) for LL in str(argv["-l"]).split(",")]
selected_feeid = [] if str(argv["-i"]) == '-1' else [int(fe,16) for fe in str(argv["-i"]).split(",")]
myoffset = int(str(argv["-o"]),16)
interval = [int(ir) for ir in str(argv["-r"]).split(":")]
if fromdump and (myoffset > 0 or interval != [0,-1]):
    #print('The offset will be considered w.r.t. the number of lines in the dumped file. Original offset will be ignored.')
    print('Do not change offset while reading dumped file')
    exit()
if ':' not in str(argv["-O"]):
    selected_orbit = [] if str(argv["-O"]) == '-1' else [int(orb,16) for orb in str(argv["-O"]).split(",")]
    selected_orbit_range = []
else:
    selected_orbit = []
    selected_orbit_range = [int(orb,16) for orb in str(argv["-O"]).split(":")]
    
onlyRDH = bool(argv["--onlyRDH"])
printinfo = bool(argv["--info"])
dumpbin = bool(argv["--dumpbin"])
printtable = bool(argv["--printtable"])
silent = bool(argv["--silent"])


if printtable:
    table_file = open('myrr_table_'+rawfilename+'.txt','w')


if printinfo:
    print(Info)
    exit()


if skipped_words != 'none':
    nonprinted_words = skipped_words

filesize = os.path.getsize(rawfilename)
last_offset = '0x'+format(int(filesize)-16,'x').zfill(8)
print("Processing file "+rawfilename)
if not fromdump:
    print("Size: %d. Contains %d lines (up to offset = %s)"%(filesize,filesize/16,last_offset))
interval = [0,numpy.inf] if fromdump else [max(0,myoffset+16*interval[0]), int(filesize)-16 if interval[1]<0 else min(int(filesize)-16, myoffset + interval[1]*16)] 

if fromdump:
    f = open(rawfilename,'r')
else:
    f = open(rawfilename,'rb')

#global variables
GBTWORD = [0,]      #will loop over the file: written by getnext()

OFFSET = '-0x10'

RDHMEM = ''  #not decoded at the moment

RDHversion = 0
RDHsize = 0
RDHfeeid = '0x0'
RDHsource = 0
RDHoffset_new_packet = -1
RDHbc = -1
RDHorbit = '0x0'
RDHtrg = -1
RDHpagecount = 0
RDHstopbit = -1
RDHdet_field = -1
RDHparbit = -1
RDHpacketcounter = -1
RDHlinkid = -1
RDHcruid = -1
RDHdw = -1

BufferRDHdump = []

IsRDHFromDump = False

# used to monitor variable changes
PREV={'RDHpacketcounter':-1, 'RDHoffset_new_packet':-1}  

# Summary
NPrintedWords={'RDH':0, 'RDHstop':0, 'RDHnostop':0, 'TDH':0, 'TDT':0, 'IHW':0, 'TDT':0, 'DDW': 0, 'CDW':0, 'DIA':0, 'STA':0, ' . ':0, '???':0, 'W/E/F/N!':0}

def Exit():

    if max(NPrintedWords.values()) > 0:
        print('\nSummary of printed words:')
    for pw in NPrintedWords:
        if NPrintedWords[pw]>0:
            print("%s:%s %d"%(pw,' '*(12-len(pw)),NPrintedWords[pw]))
    exit()

def getnext(nbyte = 16):

    global word
    global GBTWORD
    global OFFSET
    global IsRDHFromDump
    
    if fromdump:
        if nbyte == 0:
            return
        word = '.'
        i = 0
        while i < int(nbyte/16) and word:
            word = f.readline()
            i += word[0:2] == '0x'
        word = word.replace("-.................","-00"*6)
        word = word.replace("-...","-00000000"*6)
                     
        if not word:
            Exit()
            
        nonOFFSET = re.search(':.*',word).group(0)
        IsRDHFromDump = '|RDH' in word
        OFFSET = word.replace(nonOFFSET,'').replace('\n','')
        try:
            GBTWORD = re.search('.{2}-'*15+'.{2}',word).group(0).split('-')
            GBTWORD = [int(gbt,16) for gbt in GBTWORD]
        except:
            GBTWORD = re.search('.{8}-'*15+'.{8}',word).group(0).split('-')
            GBTWORD = [int(gbt,2) for gbt in GBTWORD]
    else:
        word = f.read(nbyte)  # <class 'bytes'>
        GBTWORD = list(word)[0:nbyte] # <class 'list'>
        OFFSET = '0x'+format(int(OFFSET,16)+nbyte,'x').zfill(8)
        OFFSET = OFFSET.replace('0x-','-0x')
    if int(OFFSET,16) > interval[1]:
        Exit()

getnext(interval[0])
getnext()

def getbits(bit1, bit2, outtype = "d"): 
    #outtype = bit (s)tring / he(x) string / (0x) hex string / (d)ecimal int / (dump) / (dumpbin)

    BitList = [format(B,'b').zfill(8) for B in GBTWORD]
    FullWord = ''
    for B in BitList:
        FullWord = B+FullWord
    FullWord=FullWord.strip()
    Word = FullWord[len(FullWord)-bit2-1:len(FullWord)-bit1]
    if outtype == 's':
        return Word
    elif outtype == 'd':
        Number = int('0b'+Word,2)
        return Number
    elif outtype == 'x':
        Number = int('0b'+Word,2)
        return format(Number,'x')
    elif outtype == '0x':
        Number = int('0b'+Word,2)
        return hex(Number)
    elif outtype == 'dump':
        HexList = [format(B,'x') for B in GBTWORD]
        toret = ''
        for H in HexList:
            toret=toret+H.zfill(2)+"-"
        return toret[:-1]
    elif outtype == 'dumpbin':
        HexList = [format(B,'b') for B in GBTWORD]
        toret = ''
        for H in HexList:
            toret=toret+H.zfill(8)+"-"
        return toret[:-1]
            


def readRDH(index):

    global RDHversion
    global RDHsize
    global RDHfeeid
    global RDHsource
    global RDHoffset_new_packet
    global RDHbc
    global RDHorbit
    global RDHtrg
    global RDHpagecount
    global RDHstopbit
    global RDHdet_field
    global RDHparbit
    global RDHlinkid
    global RDHpacketcounter
    global RDHcruid
    global RDHdw

    if index == 1:
        RDHversion = getbits(0,7)
        RDHsize = getbits(8,15)
        RDHfeeid = getbits(16,31,'0x')
        RDHsource = getbits(40,47)
        RDHoffset_new_packet = getbits(64,79)
        RDHlinkid = getbits(96,103)
        RDHpacketcounter = getbits(104,111)
        RDHcruid = getbits(112,123)
        RDHdw = getbits(124,127)

    elif index == 2:
        RDHbc = getbits(0,11)
        RDHorbit = getbits(32,63,'0x')

    elif index == 3:
        RDHtrg = getbits(0,31)
        RDHpagecount = getbits(32,47)
        RDHstopbit = getbits(48,55)

    elif index == 4:
        RDHdet_field = getbits(0,31)
        RDHparbit = getbits(32,47)




def gettriggers(trg,outtype='list'): 
    #outtype = 'list' or 'string'

    ctp12 = trg & 0xFFF #selecting 12 lowest bits received from CTP
    trglist = {0: 'ORB', 1: 'HB', 2: 'HBr', 3: 'HC', 4:'PhT', 5:'PP', 6:'Cal', 7:'SOT', 8:'EOT', 9:'SOC', 10:'EOC', 11:'TF', 12:'FErst', 13: 'cont', 14: 'running'}
    if outtype == 'list':
        return [trglist[b] for b in trglist if bool( (trg>>b) & 1)]
    elif outtype == 'string':
        toret=''
        for b in trglist:
            if bool( (trg>>b) & 1):
                toret=toret+trglist[b]+' '
        return toret+'(ctp %d)'%(ctp12)
        
    
    
def readword():

    worddict={224:'IHW', 232:'TDH', 240:'TDT', 228:'DDW', 248:'CDW'}
    #ITS Header Word, Trigger Data Heder, Trigger Data Trailer, Diagnostic data word, Calibration Data Word
    marker = getbits(72,79)
    try:
        wordtype = worddict[marker]
    except:
        marker = getbits(77,79)
        worddict={1:' . ', 5:'DIA', 2:' . ', 6:'DIA', 7:'STA'}      
        # Data, Diagnostic data, Status word
  
        try:
            wordtype = worddict[marker]
        except:
            wordtype = '???'

    if wordtype.replace(' ','').replace('|','') in skipped_words:
        return wordtype, 'skipped', -1
    comments = ''
    laneid = -1

    ## Reading ITS header word
    if wordtype == 'IHW':
        nlanes = getbits(0,27,'s').count('1')
        comments = "%d active lanes"%(nlanes)

    ## Reading trigger data header
    if wordtype == 'TDH':
        orbitid = getbits(32,63,'0x')
        continuation = 'continuation' if bool(getbits(14,14)) else ''
        nodata = 'nodata' if bool(getbits(13,13)) else ''
        internal = 'internal' if bool(getbits(12,12)) else ''
        trgtype = gettriggers(getbits(0,11),'string')
        comments = "orbit %s . %s . %s . %s . trg %d"%(orbitid, continuation, nodata, internal,trgtype)

    ## Reading trigger data trailer
    if wordtype == 'TDT':
        violation = 'start_viol' if bool(getbits(67,67)) else ''
        timeout = 'timeout' if bool(getbits(65,65)) else ''
        packet_done = 'packet_done' if bool(getbits(64,64)) else ''
        status_dict = {1:'W!', 2:'E!', 3:'F!'}
        lane_status_bit = [getbits(2*i,2*i + 1) for i in range(27)]
        lane_status = ["%d:%s"%(i,status_dict[lane_status_bit[i]]) for i in range(27) if lane_status_bit[i] in status_dict]
        comments = '%s . %s . %s . %s '%(packet_done, violation, timeout, 'Lanes:' if bool(len(lane_status)) else 'lanes ok')
        for C in lane_status:
            comments = comments + C

    ## Reading diagnostic data word
    if wordtype == 'DDW':
        if getbits(68,71) != 0:
            comments = '??????? expected index = 0'
        else:
            violation = 'violation' if bool(getbits(67,67)) else ''
            timeout = 'timeout' if bool(getbits(65,65)) else ''
            error_summ = 'Lanes in W/E/F' if getbits(0,55,'s').count('1')>0 else 'lanes ok'
            comments = '%s . %s . %s'%(violation, timeout, error_summ)
        
    if wordtype == ' . ':
        #scan_words = [getbits(8*i,8*i+7,'x') for i in range(9)]
        # only first byte is an errr message ??
        scan_words = [getbits(8*i,8*i+7,'x') for i in range(1)]
        error_dict = {'f4': 'Detector timeout', 'f5': '8b10b OoT', 'f6': 'Alp. protocol error', 'f7': 'Lane FIFO overflow', \
                      'f8': 'FSM eror', 'f9': 'Pending det-events limit', 'fA': 'Pending lane-events limit', \
                      'fb': 'Lane protocol error', 'fe': '8b10b in non fatal byte'}
        error_messages = [error_dict[s] for s in scan_words if s in error_dict]
            
        for E in error_messages:
            comments = comments+'E!:'+E+' '

        # Reading inner barrel data    
        b5 = getbits(72,76)
        if marker == 1: #inner
            laneid = int(str(b5))
            comments = comments+"-lane "+str(b5)
        elif marker == 2: #outer

            OBlanesdict={'40':0,  '41':1,  '42':2,  '43':3,  '44':4,  '45':5,  '46':6,\
                         '48':7,  '49':8,  '4a':9,  '4b':10, '4c':11, '4d':12, '4e':13,\
                         '50':14, '51':15, '52':16, '53':17, '54':18, '55':19, '56':20,\
                         '58':21, '59':22, '5a':23, '5b':24, '5c':25, '5d':26, '5e':27}

            try:
                laneid = OBlanesdict[getbits(72,79,'x')]
                comments = comments+"-lane "+str(laneid)
            except:
                laneid = -999
                comments = comments+"-lane ???"
            
            

    return wordtype, comments, laneid


def isROFselected():

    global RDHfeeid
    global RDHorbit
    
    flag1 = len(selected_feeid) == 0 or int(RDHfeeid,16) in selected_feeid
    if len(selected_orbit_range) == 0:
        flag2 = len(selected_orbit) == 0 or int(RDHorbit,16) in selected_orbit
    else:
        flag2 = selected_orbit_range[0] <= int(RDHorbit,16) <= selected_orbit_range[1]

    return flag1 and flag2



def myprint(dump, wtype, comments, laneid=-1):

    if silent:
        return

    global RDHorbit
    global RDHMEM
    global OFFSET
    global BufferRDHdump
    global NPrintedWords

    dump1 = OFFSET+':   '+str(dump)
    if 'RDH' not in wtype:
        dump1 = dump1[:-54]+'-...' if len(dump1) > 9*16 else dump1[:-18]+'-'+'.'*17 

    wtype1 = str(wtype) if len(str(wtype))==5 else ' '+str(wtype)+' '
    comments1 = '-' if comments=='' else str(comments)
    spacing = ' '*45+' ' if dumpbin and wtype != ' . ' else ''
    toprint = '%s %s %s  %s'%(dump1, spacing, wtype1, comments1)
    justdata = wtype == ' . ' and comments[0] == '-'
    flag = not print_only_message or not justdata
    flag = flag and not (wtype.replace(' ','').replace('|','') in nonprinted_words)
    if laneid >= 0 and -1 not in lanes_to_print and laneid not in lanes_to_print:
        flag = False

    if '|RDH' in wtype:
        BufferRDHdump = []

    if 'RDH' in wtype:
        BufferRDHdump.append(toprint)

    if 'RDH' not in wtype and flag and isROFselected():
        print(toprint)
        NPrintedWords[wtype] += 1
        NPrintedWords['W/E/F/N!'] += '!' in toprint

    if 'RDH|' in wtype and isROFselected() and flag:
        for rbuff in BufferRDHdump:
            print(rbuff)
            NPrintedWords['W/E/F/N!'] += '!' in rbuff
        NPrintedWords['RDH'] += 1
        NPrintedWords['RDHstop' if RDHstopbit else 'RDHnostop'] += 1
       
        

rdhflag = True
current_rdh_offset = -1

####################################
############ MAIN LOOP #############
####################################

while word:

    comments=''

    if rdhflag and getbits(0,7) != 6:
        print("SKIPPIN GBT WORD %d: NOT v6 HEADER? [E!] (To be improved)"%(int(OFFSET,16)/16+1))
        getnext()
        continue


    #OPERATIONS WITH WORD

    if not fromdump and (int(OFFSET,16)-current_rdh_offset) == PREV['RDHoffset_new_packet']:
        rdhflag = True
    elif fromdump:
        rdhflag = IsRDHFromDump

    
    if rdhflag:
        readRDH(1)
        current_rdh_offset = int(OFFSET,16)
        PREV['RDHoffset_new_packet'] = RDHoffset_new_packet

        ## checking packet counter jump
        comments="## fee %s . next: %d . pack_count: %d"%(RDHfeeid, RDHoffset_new_packet, RDHpacketcounter)
        if RDHpacketcounter > PREV['RDHpacketcounter']+1:
            comments = comments + ' (E! jump from %d to %d)'%(PREV['RDHpacketcounter'],RDHpacketcounter)
        elif RDHpacketcounter < PREV['RDHpacketcounter']+1:
            comments = comments + ' (N! jump from %d to %d)'%(PREV['RDHpacketcounter'],RDHpacketcounter)
        PREV['RDHpacketcounter'] = RDHpacketcounter
        ##
        if RDHsource != 32:
            comments = comments + ' . E! Source=%d not ITS'%(RDHsource)

        myprint(getbits(0,127,'dump'),"|RDH ",comments)
        getnext()

        readRDH(2)
        comments="## orb %s . bc %s"%(RDHorbit, RDHbc)
        myprint(getbits(0,127,'dump')," RDH ",comments)
        getnext()
    
        readRDH(3)
        comments="## stop: %d . page: %d . trg: %s"%(RDHstopbit, RDHpagecount,gettriggers(RDHtrg,'string'))
        myprint(getbits(0,127,'dump')," RDH ",comments)
        TriggerList = gettriggers(RDHtrg,'string')
        getnext()

        readRDH(4)
        comments="## detfield: %d"%(RDHdet_field)
        myprint(getbits(0,127,'dump')," RDH|",comments)


        if printtable:
            if isROFselected():
                table_file.write("A_,%s,B_,%s,C_,%d,D_,%d,E_,%d,F_,%d,G_,%d,H_,%d,I_,%d,J_,%d\n"%(RDHfeeid,RDHorbit,RDHpacketcounter,RDHpagecount,RDHstopbit,RDHoffset_new_packet,RDHlinkid,RDHcruid,RDHtrg,RDHbc))


        rdhflag = False

    else:
        wordtype, comments, laneid = readword()
         
        if comments != 'skipped':
            dumpbinflag = dumpbin and wordtype == ' . '
            myprint(getbits(0,127,'dumpbin' if dumpbinflag else 'dump'),wordtype,comments,laneid)       
        
        
    if onlyRDH or not isROFselected():
        getnext(RDHoffset_new_packet - RDHsize)
    getnext()
    #end of loop

    


if printtable:
    table_file.close()
