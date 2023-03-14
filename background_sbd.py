#!/usr/bin/python

import subprocess
import threading
import time
import os
import signal
import sys
import traceback
import tempfile
import random
from datetime import datetime

# usage:
# ./mp_core_sbd_itg_background.py 'SERVER', client_ip, port, expnr, CONFIG, nr_bck_flow, timeout
# SERVER or CLIENT:     string, NB: first start CLIENT for D-ITG, then SERVER
# client_ip
# port
# expnr:                integer, measurement ID, epoch
# CONFIG:               string, measurement config. ID, e.g., MPTCP-Rackspace-Kvantel
# nr_bck_flow:          integer, background flows, it creates the same number for UDP and TCP flows
# timeout:              integer, how long should the backgroudn traffic run in seconds

TCP_FLOWS = int(sys.argv[6])
UDP_FLOWS = int(sys.argv[6])
TIMEOUT   = int(sys.argv[7]) # seconds

def call_with_timeout(command, timeout):
    proc = subprocess.Popen(command)
    try:
        t = threading.Timer(timeout, proc.kill)
        t.start()
        proc.wait()
    except:
        proc.kill()
    finally:
        t.cancel()

#SIGINT
def signal_handler( *args ):
    print 'SIGINT: Quit gracefully'
    sys.exit(0)

#
#'CLIENT', ip, port, expnr, CONFIG
# SERVER 10.0.11.10 20000 1 2-CORE-BCKv4
#
#logfile


    
date = datetime.now().strftime("%Y-%m-%d.%H:%M:%S")

RECVLOGFILE='itg-CLIENT-'+sys.argv[5]+'-'+sys.argv[4]+'-'+date
SENDLOGFILE='itg-SERVER-'+sys.argv[5]+'-'+sys.argv[4]+'-'+date 

#tcpdump: start
def begin_tcpdump( iface, trace_file ):
    process = subprocess.Popen(['/usr/sbin/tcpdump', '-ttttt', '-n', '-i', iface, '-w', trace_file])
    return process

#tcpdump: stop
def end_tcpdump( process ):
    #SIGTERM
    process.terminate() #process.kill()
    (stdout_data, stderr_data) = process.communicate()
    if stdout_data: print stdout_data
    if stderr_data: print stderr_data
    
def generate_script(f, client_ip, port):
    next_port = port
    lines = ""

    bottleneck1 = False
    #upper or bottom
    if '10.0.5.2' in client_ip: #or '10.0.2.10' in client_ip or '10.0.5.10' in client_ip or '10.0.7.10' in client_ip: #or '10.0.5.10' in client_ip or '10.0.10.10' in client_ip: #Only if SSB: in client_ip or '10.0.6.10' in clie$
        bottleneck1 = True
    
    bottleneck2 = False
    if '10.0.7.2' in client_ip:
        bottleneck2 = True

    bottleneck3 = False
    if '10.0.9.2' in client_ip:
        bottleneck3 = True

    #NSB3
    bottleneck4 = False
    if '10.0.11.10' in client_ip or '10.0.14.10' in client_ip:
        bottleneck4 = True
        
    #NSB4
    bottleneck5 = False
    if '10.0.16.10' in client_ip or '10.0.19.10' in client_ip:
        bottleneck5 = True
        
    #NSB5
    bottleneck6 = False
    if '10.0.21.10' in client_ip or '10.0.24.10' in client_ip:
        bottleneck5 = True    
        

    # H=0.8
    # 1s/1s: -E 90 -B V 1.4 280 E 1000
    # 2s/2s: -E 72 -B V 1.4 560 E 2000    
    # 3s/3s: -E 90 -B V 1.4 840 E 3000
    # 4s/4s: -E 90 -B V 1.4 1120 E 4000
    # 5s/5s: -E 72 -B V 1.4 1400 E 5000
    # 6s/6s: -E 90 -B V 1.4 1680 E 6000
    # 7s/7s: -E 90 -B V 1.4 1960 E 7000
    # 8s/8s: -E 90 -B V 1.4 2240 E 8000
    # 9s/9s: -E 90 -B V 1.4 2520 E 9000
    # 10s/10s: -E 90 -B V 1.4 2800 E 10000

    #LCN-SBD bck: -n 1000 200 -E 90 -B V 1.4 1400 E 5000: 5s/5s on/off (H=0.8) at average -E 90pps with packet size (-n) normal distributed    
    #on/off UDP

    same_seed = 0.1
    
    for i in range(UDP_FLOWS):
 

        #Upper bottleneck (NSB2 or SB):
        if bottleneck1:
            seed_b1 = random.random()
            seed_b11 = random.random()
            # UDP on/off: 10% of the bottleneck (20Mbps) --- 3.5Mbps -> 375pps ; 5.5Mbps -> 575pps
            # UDP on/off: 400kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1
            # UDP on/off: 1200kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 140 E 500\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1
            ## TCP on/off rate-limited
            # lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 400 200 -E 75 -B V 1.6 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs    
            # next_port += 1
            
            ### TCP ###
            ##TCP
            # lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 1000\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b1) # timeout in msecs
            # next_port += 1


        if bottleneck2:
            seed_b2 = random.random()
            seed_b21 = random.random()
            seed_b22 = random.random()
            seed_b23 = random.random()
            # UDP on/off: 10% of the bottleneck (20Mbps) - 3Mbps
            # UDP on/off: 400kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1

            # UDP on/off: 1200kbps each
            # 280 1000
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #random.random()) # timeout in msecs
            next_port += 1

            ## TCP on/off rate-limited
            #lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -e 500 -E 95 -B V 0.95 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs    
            #next_port += 1
            
            #### TCP ###
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, same_seed) #seed_b22) # timeout in msecs
            next_port += 1
            #TCP
            # lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b2) # timeout in msecs
            # next_port += 1

        #Bottom bottleneck (NSB)
        if bottleneck3:
            seed_b2 = random.random()
            seed_b21 = random.random()
            seed_b22 = random.random()
            seed_b23 = random.random()
            # UDP on/off: 10% of the bottleneck (20Mbps) - 3Mbps
            # UDP on/off: 400kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 1120 E 4000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 1120 E 4000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1


            # UDP on/off: 1200kbps each
            # 280 1000
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1


            ## TCP on/off rate-limited
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -e 500 -E 95 -B V 0.95 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs    
            next_port += 1
            
            ### TCP ###
            # TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b22) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b2) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b23) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b23) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b23) # timeout in msecs
            next_port += 1

            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b23) # timeout in msecs
            next_port += 1

        if bottleneck4:
            seed_b3 = random.random()
            seed_b31 = random.random()
            seed_b32 = random.random()
            seed_b33 = random.random()
            # UDP on/off: 10% of the bottleneck (20Mbps) - 3Mbps
            # UDP on/off: 400kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            # UDP on/off: 1200kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            ## TCP on/off rate-limited
            #lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 300 400 -O 99 -B V 1.7 140 E 500\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs    
            #next_port += 1
            
            #### TCP ###
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b33) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b31) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b32) # timeout in msecs
            next_port += 1

        if bottleneck5:
            seed_b4 = random.random()
            seed_b41 = random.random()
            seed_b42 = random.random()
            seed_b43 = random.random()
            seed_b44 = random.random()
            seed_b45 = random.random()
            # UDP on/off: 10% of the bottleneck (20Mbps) - 3Mbps
            # UDP on/off: 400kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            # UDP on/off: 1200kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            ## TCP on/off rate-limited
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -e 450 -E 105 -B V 1.5 2800 E 10000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs    
            next_port += 1
            
            ### TCP ###
            ###TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b44) # timeout in msecs
            next_port += 1
            ###TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b42) # timeout in msecs
            next_port += 1
            ###TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b43) # timeout in msecs
            next_port += 1
            ###TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b4) # timeout in msecs
            next_port += 1

        if bottleneck6:
            seed_b5 = random.random()
            seed_b51 = random.random()
            seed_b52 = random.random()
            seed_b53 = random.random()
            seed_b54 = random.random()
            # UDP on/off: 400kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 280 E 1000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 560 E 2000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 50 -B V 1.4 840 E 3000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            # UDP on/off: 1200kbps each
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -n 1000 200 -E 150 -B V 1.4 1400 E 5000\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -e 1131 -N 31 300 -B V 1.2 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b51) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -e 1101 -N 51 300 -B V 1.2 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b51) # timeout in msecs
            next_port += 1
            # TCP on/off rate-limited
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 300 200 -O 96 -B V 1.3 140 E 500\n".format(client_ip, next_port, TIMEOUT * 1000, random.random()) # timeout in msecs    
            next_port += 1

            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -e 1170 -E 61 -B V 1.0 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b51) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -e 1195 -E 25 -B V 1.1 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b52) # timeout in msecs
            next_port += 1
            lines += "-a {0} -rp {1} -T UDP -t {2} -s {3} -e 1179 -E 35 -B V 1.3 70 E 250\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b5) # timeout in msecs
            next_port += 1
            
            ### TCP ###
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b53) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b52) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b51) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b54) # timeout in msecs
            next_port += 1
            #TCP
            lines += "-a {0} -rp {1} -T TCP -t {2} -s {3} -n 1000 200 -C 2500\n".format(client_ip, next_port, TIMEOUT * 1000, seed_b5) # timeout in msecs
            next_port += 1

       
    print lines
    f.write(lines)
    f.flush()

#SIGINT 
signal.signal(signal.SIGINT, signal_handler)

#client
if sys.argv[1] == 'CLIENT':
    print "CLIENT"

    try:
        program=["/usr/local/bin/ITGRecv"]
        call_with_timeout(program, TIMEOUT)
    except:
        traceback.print_exc()

#server
if sys.argv[1] == 'SERVER':
    print "SERVER"

    try:
        # script_file = tempfile.NamedTemporaryFile()
        # generate_script(script_file, sys.argv[2], int(sys.argv[3]))
        filename = sys.argv[8]
        path = '/home/thomas/Workspace/mestrado/mpquic-sbd5/client/'
        filename = path + filename
        user='thomas'
        recv_log_file = "/home/" + user + "/mp-core/mp-core-sbd-data/mpquic-sbd/" + RECVLOGFILE
        send_log_file = "/home/" + user + "/mp-core/mp-core-sbd-data/mpquic-sbd/" + SENDLOGFILE
        options =["/usr/local/bin/ITGSend", filename, '-l', send_log_file, '-x', recv_log_file]

        print options
        call_with_timeout(options, TIMEOUT+3) # kill 3 seconds later, itg has auto shutdown
    except:
        traceback.print_exc()
    # finally:
    #     with open(recv_log_file + '.txt', 'wt') as f:
    #       text = subprocess.check_output(["/usr/local/bin/ITGDec", recv_log_file])
    #       f.write(text)
    #     with open(send_log_file + '.txt', 'wt') as f:
    #       text = subprocess.check_output(["/usr/local/bin/ITGDec", send_log_file])
    #       f.write(text)
