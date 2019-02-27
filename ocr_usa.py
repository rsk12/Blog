
# coding: utf-8

# In[1]:


import re
import os
import sys
import time
import pytesseract as tess
##from subprocess import Popen


# In[2]:


# Modifies the string
def Transform(string):
# old build - when the whole label was scaned
    new = re.sub(' {3,}','<TAB>', string)
    new = re.sub('(<TAB>)?[\n\r](<TAB>)?','\n',new)
    new = re.sub('\n{2,}','<MUL>\n',new)
    new = re.sub(r'<([A-Z]+)>',r'<D><\1><D>',new)
    new = re.sub('\n','<D>',new)
    new = re.sub('(<D>){2,}','<D>',new)

#EXTRA PRECAUTIONS

## Causing a problem by inserting <D> in between Tracking ID (type 1, refer to regex)
    new = new.replace('\\', '') # alternate
    new = re.sub('\r', '<D>', new)
    new = re.sub('\n','<D>',new)
    new = re.sub('</br>|</BR>','<D>', new)
    new = re.sub('(<D>){2,}','<D>',new)

    return new

# Defines search space for Name
def Get_CheckPoints(string):
    Codes = ['AL', 'AK', 'AZ', 'AR', 'AA', 'AE', 'AP', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'AB', 'BC', 'MB', 'NB', 'NL', 'NT', 'NS', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT']
    address_last_line = r'[a-zA-Z. ]*(,)?( [A-Z]{2},? )[0-9]{3,}[-]?[0-9]*'
    check_point=[]
    dlim = '<D>'

    part = string.split(dlim)
    # print part
    # write_debug(str(part))
    
    for i in range(len(part)):
        # ADDRESS LINE
        ## Have to find a line containing the State Code ([A-Z]{2} ) followed by the zip code 

        match = re.search(address_last_line, part[i])
        if match:
            # print "\n"+part[i]
            # print match.group(2)
            if match.group(2).strip(' ,') in Codes:
                check_point.append(i)
        else:
            match = re.search('([A-Z]{2}),? [0-9]{4,}[-]?[0-9]*', part[i]) #TX 50123-8988
            if match:# print part[i], match.group(1)
                if match.group(1) in Codes:
                    check_point.append(i)

    if not len(check_point):
        print ("\tSorry, didn't recognize a lable.")
        return 1

    # write_debug(str(check_point))
    return check_point

# Searches for a Tracking ID
def Get_TrackingId(string):
    dlim = '<D>'
    number = ''
    U_track = r' ?tracking.*[ \d]{2,}$'

    # EXCLUSIVELY FOR FedEx
    F_num = r'^\d{4} \d{4} \d{4}$'

    part = string.split(dlim)
    for i in range(len(part)):
        part[i] = part[i].strip()

        # TRACKING ID
        
        ## SINCE <D> is getting inserted in between....code might not get in here
        ## getting handled by the next condition...where strip('#:-/\\\' ') is used

        match = re.search(U_track, part[i].lower()) ## Tracking #: 1Z Y4Y 657......
        if match:
            # print part[i]+" : 1stTrack"
            if ':' in part[i]:
                number = part[i].split(':')[1].strip()
            elif '#' in part[i]:
                number = part[i].split('#')[1].strip()

        if not number:
            match = re.search(r' ?usps | ?ups | ?tracking ?| ?trk| tracking | delivery ', part[i].strip().lower())
            if match:
                # print part[i]+" : 2ndTrack"
                for j in range(i+1, len(part)):
                    part[j] = part[j].strip('#:-/\\\' ')
                    # print "\t"+part[j]
                    if re.search(r'^[A-Z0-9 ]{4,}\d{3,} \d{2,}$', part[j]):
                        # print part[j]
                        number = part[j]
                        break

                    elif re.search(r'^[0-9]{10,}$', part[j].strip()):
                        number = part[j]

        if not number:
            # print part[i]
            match = re.search(F_num, part[i].strip())
            if match:
                number = match.group(0)

            else:
                match = re.search('\d{9,}', part[i].strip())
                if match:
                    number = match.group(0)


    if not number:
        number = "Sorry, didn't locate Tracking ID."

    return number
    


# Removes titles off names
def Refine(name):
    titles = ['Mr','Ms','Mrs','Miss','Dr']

    for title in titles:
        if re.search(r'^'+title.lower()+r'[. ]+', name.lower()):
            l = len(title)
            name = name[l:].strip('. ')
            break

    return name

# Searches for a name in the defined search space
def Get_Name(string, check_point):
    fullname = r'^([a-zA-Z]{2,}[. ]+[a-zA-Z]{2,}){1,4}$'
    dlim = '<D>'
    name = ''

    part = string.split(dlim)
    

    i = check_point[-1]
    if len(check_point)==2:
        limit = check_point[0]
    else:
        limit = 0

    while i > limit:
        i-=1

        part[i] = part[i].strip()
        # print part[i]

        if re.search(r'^ship |^ship$', part[i].lower()):
            frame = part[i][4:].strip()
            if re.search(fullname, frame):
                # print 'FOUND FRAME'
                name = frame
            break

        # Specifically for FedEx
        if re.search(r'^bill sender', part[i].lower()):
            break

        if re.search(r'^to[^a-z]+[a-z \.]+', part[i].lower()):
            # print "\tto condition"
            # removes 'TO'
            frame = part[i][2:].strip()
            # removes "'#:.;
            while len(frame) and not frame[0].isalpha():
                frame = frame[1:]

            if re.search(fullname, frame):
                # print 'FOUND FRAME'
                name = frame
                break
            elif re.search('^[a-zA-Z]{4,}$', frame):
                name = frame
                break

        if re.search(fullname, part[i]):
            name = part[i]

        elif name=='' and re.search('^[a-zA-Z]{4,}$', part[i]):
            name = part[i]

    if not name:
        if re.search(fullname, part[0]):
            name = part[0]
            name = Refine(name)
        else:
            name = "Sorry, didn't locate Name."
    else:
        name = Refine(name)

    return name



# Gets all Details 
def Examine(string):
    info = {}

    check_point = Get_CheckPoints(string)
    if check_point==1:
        return info
    name = Get_Name(string, check_point)

    number = Get_TrackingId(string)	
    
    
    info["name"] = name
    info["track_id"] = number
    
    # print info
    return info



def main():
    fout = open('details.txt', 'a')
    #folder = sys.argv[1].strip('/')+'/'
    PATH = os.getcwd()
    folder = PATH+'/./test/'
    images = os.listdir(folder)

    for image in images:
        source = folder+image
        result = image.split('.')[0]+".txt"
        print ("\nProcessing "+image)
        print ("\tRunning OCR")
        startO = time.time()
        
        ## tesseract ##
        
        string = tess.image_to_string(source)

        ## tesseract ##
        
        p1 = time.time()-startO
        print ("\tOCR took - "+str(p1))
        startE = time.time()
        #if not fail:
        if not 0:

            string = Transform(string)
            print ("\tGetting Details")
            info = Examine(string)

            p2 = time.time()-startE
            print ("\tReading and Extraction took - "+str(p2))

            print ("\t"+str(info))
            print ("\tTOTAL TIME - "+str(p1+p2))

            # fr.close()
            print ("\twriting result to file")
            fout.write("\n"+image+"\n\t"+str(info))

    fout.close


# Run ` $ python extract.py labels `
if __name__ == '__main__':
    main()

