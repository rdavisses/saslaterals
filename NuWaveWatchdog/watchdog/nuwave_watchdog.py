from nuWave.wd import watchdog
import os
import sys
from datetime import datetime
from time import sleep
import pyautogui
import json
import io
import smtplib
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText  
from email.mime.image import MIMEImage
import psutil

'''
cdef enum RETCODES:
    BadAddress = -3
    NotOpened = -2
    NotResponsive = -1
    CanceledByUser = 0
    PointWritten = 1
    JustStarted = 2
    BkgSaved = 3
    UserStopped = 4
    CollectPaused = 5
'''

'''
    int timeout:            number of seconds used to evaluate a stalled system. If process status has not changed in this amount of time, 
                            consider it process locked / broken
    str itype:              instrument type to be monitored. Can be one of {all, ir, uv, ra}. In most cases, leave as default of all. In the 
                            future, can be used to split the process amongst multiple control instruments
    str address:            Must match the listening address of the nuWave instance (see Advanced->Server Settings from nuWave homepage menu bar)
                            Default value presented here is the default value for nuWave to serve
    int port:               Must match the listening port fo the nuWave instance (see Advanced->Server Settings from nuWave homepage menu bar)
                            Default value presented here is the default value for nuWave to serve
    int warningDuration:    Duration the Warning UI Dialog will display prior to returning to your calling function. This dictates the length of 
                            time in seconds that the user will have to cancel the operation 
    int socketTO:           Length of time (seconds) reserved to try and connect to the NuWave instance. This will fail if there is no nuWave instance
                            available (and the RETCODES::NotOpened status will be returned). 5 seconds (default) should be the MINIMUM length of time 
                            as the connection can be slow based upon system status.
'''
 
 
 
 
# DEFAULT PARAMS ====================
_timeout=400                # seconds
_itype="all"                # please be careful! options are "all", "ir", "uv", "ra" (lower case must be enforced)
_address="127.0.0.1"        # this is internal feed back loop for same machine
_port=55556                 # should be range (49152–65535) according to IANA
_warningDuration=60         # seconds
_socketTO=5                 # seconds (Please Ensure This is Greater than 5 seconds)
# ===================================




def screenshot(save_to_file = False):
    try:
        now = datetime.now()
        nowms = now.replace(microsecond=0)
        nowmsstr = str(nowms)
        filename = nowmsstr.replace(":", "_") + '.png'
        
        ss = pyautogui.screenshot()
        ss_io = io.BytesIO()
        ss.save(ss_io, format='PNG')
        
        if save_to_file:
            folder_path = "C:\\Scripts\\Screenshots\\"
            
            if not (os.path.isdir(folder_path)):
                os.makedirs(folder_path)
                
            ss.save(folder_path + filename)
        return(ss_io, filename)
    except:
        return None, ""


def sendEmail(ss_io, filename, return_code, restart_type = ''):
    # give a restart_type of "PC restart" or "NuWave restart"
    try:
        if len(sys.argv) == 1:
            return              #nowhere to send emails
        
        args = sys.argv
        email_json = args[1] #args[0]is name of script
        with open(email_json,'r') as f:
            email_dict = json.load(f)
        
        email_addresses = email_dict["Recipients"]
        title = email_dict["Title"]
        
        subject = title + ': Watchdog has triggered - ' + restart_type
        
        msg = MIMEMultipart()
        msg['From'] = 'aams@spectrumenvsoln.com'
        msg['To'] = ", ".join(email_addresses)
        msg['Subject'] = subject
        
        if ss_io: #if screenshot succesfully taken
            body = "{site} Watchdog encountered return code {return_code}, which initiates a {restart_type}. See attached screenshot.".format(
                site = title,
                return_code = return_code,
                restart_type = restart_type
            )
            attachment = MIMEImage(ss_io.getvalue())
            attachment.add_header(
                "Content-Disposition", "attachment", filename=filename
            )
            msg.attach(attachment)
        else:
            body = "{site} Watchdog encountered return code {return_code}, which initiates a {restart_type}. Failed to take screenshot.".format(
                site = title,
                return_code = return_code,
                restart_type = restart_type
            )
        
        msg.attach(MIMEText(body, 'html'))
        text = msg.as_string()
        
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login('aams@spectrumenvsoln.com','Spectrum1')
        
        for email in email_addresses:
            server.sendmail('aams@spectrumenvsoln.com',email,text)
        
        server.quit()
    except: 
        #log that email failed?
        pass


def get_PID(process_name):
    for proc in psutil.process_iter():
        if process_name in proc.name():
            return proc.pid  
    return -1
       
        
@watchdog.gotime(   timeout=_timeout, 
                    itype=_itype, 
                    address=_address, 
                    port=_port, 
                    warningDuration=_warningDuration, 
                    socketTO=_socketTO  
                )
def main(status, *args, **kwargs):
    
    #print(kwargs['PID'], kwargs['CWD']) # these will always be present in kwargs
                                        # if for some reason, an error occurs, PID = -1, CWD = ""
                                        
    if (status == 0): #canceled by user
        pass
    elif (status > 0): # good status
        pass
    elif (status < 0): # bad status
        if (status == -2) | (status == -3) | (status == -1 and kwargs['PID'] == -1):
            #statuses worthy of pc restart
            ss_io, filename = screenshot(save_to_file = True)
            sendEmail(ss_io, filename, status, restart_type = 'PC restart')
            os.system("shutdown -t 3 -r")
        elif (status == -1):
            #statuses worthy of nuwave restart only
            ss_io, filename = screenshot(save_to_file = True)
            sendEmail(ss_io, filename, status, restart_type = 'NuWave restart')
            
            # taskkil nuwave, then omtalk and omnic
            os.system("taskkill /F /PID %d"%kwargs['PID'])         # taskill via PID. Probably should check that PID != -1 (unknown error) prior to this
            sleep(10)                                              # necessary, otherwise last steps don't run
            try:
                omTalk_PID = get_PID('OmTalk.exe')
                if omTalk_PID != -1:
                    os.system("taskkill /F /PID %d"%omTalk_PID)
                    sleep(5)
                omnic_PID = get_PID("omnic32.exe")
                if omnic_PID != -1:
                    os.system("taskkill /F /PID %d"%omnic_PID)
                    sleep(5) 
            except:
                pass
            finally:
                os.system("%s autoStart"%str('"' + kwargs['CWD'] + '"')) # cwd points to the NuWave executable, so pass it autoStart keyword to start collection immediately

if __name__ == "__main__":
    #could add additional keyword parsing here
    __version__ = 8.94      #released with nuwave 8.94
    main()