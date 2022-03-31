test_fname = 'o2_rawtf_run00505582_tf00002528_epn120.tf.raw'

f = open(test_fname,'rb')
word = f.read(16)

GBTWORD=list(word)[0:10]
OFFSET='0x00000000'

RDHversion = 0
RDHsize = 0
RDHfeeid = 0
RDHsource = 0
RDHoffset_new_packet = 0
RDHbc = 0
RDHorbit = 0
RDHtrg = 0
RHDpagecount = 0
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
    global RHDpagecount
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
        RHDpagecount = getbits(32,47)
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
    trglist = {0: 'ORB', 1: 'HB', 2: 'HBr', 3: 'HC', 4:'PhT', 5:'PP', 6:'Cal', 7:'SOT', 8:'EOT', 9:'SOC', 10:'EOC', 11:'TF', 12:'FErst', 13: 'Cont', 14: 'Running'}
    if outtype == 'list':
        return [trglist[b] for b in trglist if bool( (trg>>b) & 1)]
    elif outtype == 'string':
        toret=''
        for b in trglist:
            if bool( (trg>>b) & 1):
                toret=toret+' '+trglist[b]
        return toret
        
    
    
def wordtype():
    worddict={224:'IHW', 232:'TDH', 240:'TDT', 228:'DDW', 248:'CDW'}
    #ITS Header Word, Trigger Data Heder, Trigger Data Trailer, Diagnostic data word, Calibration Data Word
    marker = getbits(72,79)
    try:
        return worddict[getbits(72,79)]
    except:
        worddict={1:' . ', 5:'DIA', 2:' . ', 6:'DIA', 7:'STA'}      
        # Data, Diagnostic data, Status word
  
        try:
            return worddict[getbits(77,79)]
        except:
            return '???'



rdhflag = True
current_rdh_offset = -1
offset_new_packet = -1
comments = ''

while word:


    comments=''

    if rdhflag and getbits(0,7) != 6:
        print("SKIPPING GBT WORD %d: NOT v6 HEADER? [to be implemented]"%(int(OFFSET,16)/16+1))
        getnext()
        continue

    

    #OPERATIONS WITH WORD

    if (int(OFFSET,16)-current_rdh_offset) == offset_new_packet:
        print(' '*48+'-----')# --------expected new packet')
        rdhflag = True

    
    if rdhflag:
        readRDH(1)
        current_rdh_offset = int(OFFSET,16)
        offset_new_packet = RDHoffset_new_packet
        print(getbits(0,79,'dump'),"|RDH|",comments)
        getnext()

        readRDH(2)
        print(getbits(0,79,'dump'),"|RDH|",comments)
        getnext()
        
        readRDH(3)
        comments="fee %s . orb %s . next: %d"%(RDHfeeid, RDHorbit, RDHoffset_new_packet)
        print(getbits(0,79,'dump'),"|RDH|",comments)
        TriggerList = gettriggers(RDHtrg,'string')
        getnext()

        readRDH(4)
        comments="detfield: %d . --%s--"%(RDHdet_field,gettriggers(RDHtrg,'string'))
        print(getbits(0,79,'dump'),"|RDH|",comments)


        rdhflag = False

    else:
        if wordtype() == ' . ':
            scan_words = [getbits(8*i,8*i+7,'x') for i in range(9)]
            error_dict = {'f4': 'Detector timeout', 'f5': '8b10b OoT', 'f6': 'Alp. protocol error', 'f7': 'Lane FIFO overflow', \
                          'f8': 'FSM eror', 'f9': 'Pending det-events limit', 'fA': 'Pending lane-events limit', \
                          'fb': 'Lane protocol error', 'fe': '8b10b in non fatal byte'}
            #error_messages = [error_dict[s] for s in scan_words if s in error_dict]
            # only first byte is an errr message ??
            error_messages = [error_dict[s] for s in scan_words[0:1] if s in error_dict]
            
            
            for E in error_messages:
                comments = comments+' E!:'+E
            
                
        print("%s  %s %s"%(getbits(0,79,'dump'),wordtype(),comments))
        
        
        
    #end of loop
    getnext()

    




