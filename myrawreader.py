#!/usr/bin/env python3

"""

myrawreader.py

Usage: ./myrawreader.py -f <file.raw> [-e <excludedwords>] [-l <lane>] [-i <feeid>] [--message] [-t <tempdirectory>] [--append] [--silent] [--merge]

Options:
    -h --help                Display this help
    -f <file.raw>            Raw ITS data file
    -e <excludedwords>       Comma separated list of GBT words not to print [default: none]
    -l <lane>                Comma separated list of lanes to print [default: -1]
    -i <feeid>               Comma separated list of feeids to print (0xABCD) [default: -1]
    --message                Skip data word without problems [default: False]
    -t <tempdirectory>       Temp directory where the final file is built [default: no]
    --append                 Do not erase the tempdirectory [default: False]
    --silent                 Do not print here
    --merge                  Merge the created temp files into myrawreaderoutpur.dat [default: False]

                          

"""

#RDH,.,IHW,TDH,TDT,DDW,CDW,DIA,STA
 
import docopt
import sys
import os


argv = docopt.docopt(__doc__,version="1.0")
rawfilename = str(argv["-f"])
print_only_message = bool(argv["--message"])
excluded_words = str(argv["-e"])
lanes_to_print = [int (LL) for LL in str(argv["-l"]).split(",")]
feeid_to_print = str(argv["-i"]).split(",")
tdir = str(argv["-t"])
appendfiles = bool(argv["--append"])
silent = bool(argv["--silent"])
merge = bool(argv["--merge"])

if merge and tdir == 'no':
    print("What are you asking me to merge? Please enable text file production!")
    exit()
if appendfiles and tdir == 'no':
    print("What should I append? Please anable text file production!")
    exit()

print("Processing file %s"%(rawfilename))

if tdir != 'no':
    if not os.path.exists(tdir):
        os.makedirs(tdir)
        print("New directory "+tdir+" created")
    elif not appendfiles:
        os.system('rm -f '+tdir+'/*')

f = open(rawfilename,'rb')
word = f.read(16)

GBTWORD=list(word)[0:10]
OFFSET='0x00000000'

RDHMEM = ''

RDHversion = 0
RDHsize = 0
RDHfeeid = 0
RDHsource = 0
RDHoffset_new_packet = 0
RDHbc = 0
RDHorbit = 0
RDHtrg = 0
RDHpagecount = 0
RDHstopbit = 0
RDHdet_field = 0
RDHparbit = 0



def getbits(bit1, bit2, outtype = "d"): 
    #outtype = bit (s)tring / he(x) string / (0x) hex string / (d)ecimal / (dump) 
    BitList = [format(B,'b').zfill(8) for B in GBTWORD]
    FullWord = ''
    for B in BitList:
        FullWord = B+FullWord
    FullWord=FullWord.strip()
    #return FullWord
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
        toret = OFFSET+":   "
        for H in HexList:
            toret=toret+H.zfill(2)+"-"
        return toret+'...'
            


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

    if index == 1:
        RDHversion = getbits(0,7)
        RDHsize = getbits(8,15)
        RDHfeeid = getbits(16,31,'0x')
        RDHsource = getbits(40,47)
        RDHoffset_new_packet = getbits(64,79)

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



def getnext():
    global word
    global GBTWORD
    global OFFSET
    word = f.read(16)
    GBTWORD = list(word)[0:10]
    OFFSET = '0x'+format(int(OFFSET,16)+16,'x').zfill(8)


def gettriggers(trg,outtype='list'): # list or string
    ctp12 = trg & 4095 
    # 4095: 12'b1 --> selecting 12 lowest bits received from CTP
    trglist = {0: 'ORB', 1: 'HB', 2: 'HBr', 3: 'HC', 4:'PhT', 5:'PP', 6:'Cal', 7:'SOT', 8:'EOT', 9:'SOC', 10:'EOC', 11:'TF', 12:'FErst', 13: 'cont', 14: 'running'}
    if outtype == 'list':
        return [trglist[b] for b in trglist if bool( (trg>>b) & 1)]
    elif outtype == 'string':
        toret=''
        for b in trglist:
            if bool( (trg>>b) & 1):
                toret=toret+' '+trglist[b]
        return toret+' (ctp %d)'%(ctp12)
        
    
    
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

    comments = ''
    laneid = -1

    ## Reading ITS header word
    if wordtype == 'IHW':
        nlanes = getbits(0,27,'s').count('1')
        comments = "%d active lanes"%(nlanes)

    ## Reading trigger data header
    if wordtype == 'TDH':
        orbitid = getbits(32,36,'0x')
        continuation = 'continuation' if bool(getbits(14,14)) else ''
        nodata = 'nodata' if bool(getbits(13,13)) else ''
        internal = 'internal' if bool(getbits(12,12)) else ''
        trgtype = getbits(0,11)
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
            OBlanesdict={'40': 0, '46': 6, '48': 7, '4e': 13, '50': 14, '56': 20, '58': 21, '5e': 27, \
                         '43': 3,                   '4b': 10, '53': 17,                     '5b': 24, \
                         '41': 1, '42': 2, '44': 4, '45': 5,  '49': 8,  '4a': 9,  '4c': 11, '4d': 12, \
                         '51': 15,'52': 16,'54': 18,'55': 19, '59': 22, '5a': 23, '5c': 25, '5d': 26}
            try:
                laneid = OBlanesdict[getbits(72,79,'x')]
                comments = comments+"-lane "+str(laneid)
            except:
                laneid = -999
                comments = comments+"-lane ???"
            
            

    return wordtype, comments, laneid

    



rdhflag = True
current_rdh_offset = -1
offset_new_packet = -1
comments = ''


def myprint(dump, wtype, comments, laneid=-1):

    global RDHorbit
    global RDHMEM

    dump1 = str(dump)
    wtype1 = str(wtype) if len(str(wtype))==5 else ' '+str(wtype)+' '
    comments1 = '-' if comments=='' else str(comments)
    # PLACEHOLDER: THE LANES MUST BE DECODED!
    comments1 = comments1.replace("lane ???","")
    justdata = wtype == ' . ' and comments[0] == '-'
    flag = not print_only_message or not justdata
    flag = flag and not (wtype.replace(' ','').replace('|','') in excluded_words)
    if laneid >= 0 and -1 not in lanes_to_print and laneid not in lanes_to_print:
        flag = False
    if "-1" not in feeid_to_print and RDHfeeid not in feeid_to_print:
        flag = False
    if flag and not silent:
        print('%s %s  %s'%(dump1, wtype1, comments1))

    if tdir != 'no':
    	tfile = open(tdir+'/'+str(int(str(RDHorbit),16)).zfill(30)+'.txt','a')
    	if flag:
    	    tmsg = '%s %s %s\n'%(dump1, wtype1, comments1)
    	    if wtype == '|RDH ':
    	        RDHMEM = tmsg
    	    elif wtype == ' RDH ' and RDHMEM  != '':
    	        tfile.write(RDHMEM)
    	        tfile.write(tmsg)
    	        RDHMEM = ''
    	    else:
    	        tfile.write(tmsg)
    	tfile.close()


#### MAIN LOOP

while word:

    comments=''

    if rdhflag and getbits(0,7) != 6:
        print("SKIPPING GBT WORD %d: NOT v6 HEADER? [to be implemented]"%(int(OFFSET,16)/16+1))
        getnext()
        continue

    

    #OPERATIONS WITH WORD

    if (int(OFFSET,16)-current_rdh_offset) == offset_new_packet:
        #if not silent:
            #print(' '*48+'-----')# --------expected new packet')
        rdhflag = True

    
    if rdhflag:
        readRDH(1)
        current_rdh_offset = int(OFFSET,16)
        offset_new_packet = RDHoffset_new_packet
        comments="## fee %s . next: %d"%(RDHfeeid, RDHoffset_new_packet)
        myprint(getbits(0,79,'dump'),"|RDH ",comments)
        getnext()

        readRDH(2)
        comments="## orb %s . bc %s"%(RDHorbit, RDHbc)
        myprint(getbits(0,79,'dump')," RDH ",comments)
        getnext()
    
        readRDH(3)
        comments="## stop_bit: %d . page_count: %d"%(RDHstopbit, RDHpagecount)
        myprint(getbits(0,79,'dump')," RDH ",comments)
        TriggerList = gettriggers(RDHtrg,'string')
        getnext()

        readRDH(4)
        comments="## detfield: %d . --%s--"%(RDHdet_field,gettriggers(RDHtrg,'string'))
        myprint(getbits(0,79,'dump')," RDH|",comments)


        rdhflag = False

    else:
        wordtype, comments, laneid = readword()
         
        myprint(getbits(0,79,'dump'),wordtype,comments,laneid)       
        #print("%s  %s %s"%(getbits(0,79,'dump'),wordtype,comments))
        
        
        
    #end of loop
    getnext()

    



if tdir != 'no' and merge:
    os.system('rm -f ./myrawreaderoutput.dat')
    os.system('for i in $(ls '+tdir+'/*.txt); do echo ==NEW ORBIT== >> myrawreaderoutput.dat; cat $i >> myrawreaderoutput.dat; done')

