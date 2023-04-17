#!/usr/bin/python

import csv
import socket
import signal
import select
import sys
import os
import inspect
import tempfile
import time
import subprocess
import random
from threading import Thread

BUFSIZE = 1024*8

#socket option patch
TCP_MULTIPATH_DEBUG = 10001     #/* MPTCP DEBUG on/off */
TCP_MULTIPATH_ENABLED = 26      #/* MPTCP DISABLED on/off */
TCP_MULTIPATH_NDIFFPORTS = 10007       #/* MPTCP NDIFFPORTS */
TCP_MULTIPATH_PATHMANAGER = 10008      #/* MPTCP PATHMANAGER */

#ss
def query_ss(epoch, port):
    cmd = ["/sbin/ss", "-into", "state", "established", '( sport = :%d )' % port]
    output_field = ['ts', 'sack', 'coupled', 'wscale', 'rto', 'rtt', 'mss', 'cwnd', 'ssthresh', 'send', 'RATE', 'retrans', 'unacked', 'rcv_space']

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p.wait()
    line = p.stdout.readlines()

    #parse line to cvs: IP + CWND
    results = []
    idx = 1
    while idx < len(line) and len(line) > 2:
        ss_values = [epoch, str(time.time())]

        #IP
        x = line[idx].strip().split(' ')
        x = [i for i in x if i != '']
        ip = x[3]
        ss_values.append(ip)

        #TCP stuff
        cwnd = line[(idx+1)].strip().split()
        values = {}
        for x in cwnd:
            if not 'Kbps' in x and not 'Mbps' in x:
                if ':' in x:
                    parts = x.split(":")
                    values[parts[0]] = parts[1]
                else:
                    values[x] = x
            elif 'Kbps' in x:
                #normalize: Mbps
                x=x.split("Kbps")
                x = float(x[0])/1000.0
                values['RATE'] = str(x)
            elif 'Mbps' in x:
                x=x.split("Mbps")
                values['RATE'] = x[0]

        # append fields in our order to ss_values
        for f in output_field:
            ss_values.append(f)
            if values.has_key(f):
               ss_values.append(values[f])
            else:
               ss_values.append('') #default value

        # append to results array
        results.append(ss_values)

        idx+=2
    return results


def monitor_sockets(stop_flag, first_port, flows, filename, epoch):
    print 'MONITORING SS - START'
    csvfile   = None
    csvwriter = None
    errors_occured = False
    try:
        # open file
        csv_filename = "ss-SERVER-DL-" + filename + ".csv"
        csvfile      = open(csv_filename, "wt")
        csvwriter    = csv.writer(csvfile, delimiter='\t')

        while stop_flag['ok']:
            for i in range(flows):
                try:
                    results = query_ss(epoch, first_port + i)
                    for ss_values in results:
                        csvwriter.writerow(ss_values)
                except:
                    errors_occured = True # just keep going, and report later

            # wait a bit before polling again to avoid 100% cpu
            time.sleep(0.02)
    except:
        errors_occured = True
        traceback.print_exc()
    finally:
        try:
            csvfile.close()
        except:
            pass

        # signal that we are done
        print 'MONITORING SS - DONE', 'WITH ERRORS' if errors_occured else ''
        stop_flag['ended'] = True


def start_ss_monitoring(first_port, flows, filename, epoch):
    stop_flag = { 'ok': True, 'ended': False }
    thread = Thread(name = 'ss_monitor', target = monitor_sockets, args=(stop_flag, first_port, flows, filename, epoch, ) )
    thread.start()
    return stop_flag


def end_ss_monitoring(stop_flag):
    stop_flag['ok'] = False
    while not stop_flag['ended']:
        time.sleep(0.1)

# -----------------------------------------------------------------------------

#SIGINT
def signal_handler( *args ):
    print 'SIGINT: Quit gracefully'
    sys.exit(0)


#tcpdump: start
def begin_tcpdump( iface, trace_file ):
    process = subprocess.Popen(['tcpdump', '-ttttt', '-n', '-s', '150', '-i', iface, 'tcp', '-w', trace_file])
    return process


#tcpdump: stop
def end_tcpdump( process ):
    #SIGTERM
    process.terminate() #process.kill()
    (stdout_data, stderr_data) = process.communicate()
    if stdout_data: print stdout_data
    if stderr_data: print stderr_data


#close sockets
def close_sockets(sockets):
    for s in sockets:
        try:
            s.close()
        except:
            pass


def log_recv_data_to_file(host, port, recv_data, filename):
  log_file = "goodput-CLIENT-DL-" + filename
  min_time = max_time = None
  with open(log_file, "at") as csvfile: # append not to overwrite previous data from other flows there
    w = csv.writer(csvfile, delimiter='\t')
    for ts_len in recv_data:
      w.writerow([ts_len[0], ts_len[1], host, port])
      if not min_time:
        min_time = ts_len[0]
        max_time = ts_len[0]
      else:
        min_time = min(min_time, ts_len[0])
        max_time = max(max_time, ts_len[0])

  log_file = "time-CLIENT-DL-" + filename
  with open(log_file, "at") as csvfile: # append not to overwrite previous data from other flows there
    w = csv.writer(csvfile, delimiter='\t')
    w.writerow([max_time - min_time, host, port])


# open and listen on sockets (or single socket if MPTCP)
def create_tcp_sockets(mode, proto, server_addr_list, first_port_start, flows, msg_size, ndiffs):
  sockets = []
  try:
    port = first_port_start
    for server_addr in server_addr_list:
      socket_family = socket.AF_INET6 if ':' in server_addr else socket.AF_INET # v6 or v4
      for i in range(flows):
        s = socket.socket(socket_family, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        ndiff = ndiffs.split('-')
        if proto == 'TCP':
            # TCP congestion control: TCP is always reno!
            TCP_CONGESTION = 13
            s.setsockopt(socket.IPPROTO_TCP, TCP_CONGESTION, "reno")
        
            # make sure MPTCP is disabled!
            # s.setsockopt(socket.IPPROTO_TCP, TCP_MULTIPATH_DEBUG, 0)
            # s.setsockopt(socket.IPPROTO_TCP, TCP_MULTIPATH_ENABLED, 0)
        elif proto == 'MPTCP':
            # enable MPTCP
            s.setsockopt(socket.IPPROTO_TCP, TCP_MULTIPATH_DEBUG, 0) # don't want debugging
            s.setsockopt(socket.IPPROTO_TCP, TCP_MULTIPATH_ENABLED, 1)
            s.setsockopt(socket.IPPROTO_TCP, TCP_MULTIPATH_NDIFFPORTS, int(ndiff[0]) )

        #MAX RMEM and WMEM BUFSIZE
        #s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, msg_size)
        #s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, msg_size)

        if mode == 'SERVER':
            s.bind(('', port))
            s.listen(1)
            print 'Listening on TCP socket: %s:%d' % (server_addr, port)
        elif mode == 'CLIENT':
            print 'Connecting to TCP socket: %s:%d' % (server_addr, port)
            s.connect((server_addr, port))
            
        port += 1
        sockets.append(s)
    return sockets
  except:
      close_sockets(sockets) # close any that might have been opened
      raise                  # before passing on the exception


#waits for connections on all sockets
def accept_with_timeout(sockets, timeout):
    try:
        conns = []
        not_yet_connected = list(sockets) # make a copy
        while not_yet_connected:
            ready = select.select(not_yet_connected, [], [], timeout)
            if not ready[0]: # timed out
                close_sockets(conns) # close any that might have been opened
                return []

            for sock in ready[0]:
                conn, addr = sock.accept()
                print 'Client connected from: %s:%d' % (addr[0], addr[1])
                conns.append(conn)
                not_yet_connected.remove(sock)
        return conns
    except:
        close_sockets(conns) # close any that might have been opened
        raise                # before passing on the exception


#waits for incoming connections, when all are connected starts sending
def send_over_sockets(sockets, msg_size, server_port, flows, filename, epoch):
    
    print 'SERVER - WAIT FOR CLIENTS'
    conns = accept_with_timeout(sockets, 20 * 60) # 20 minutes timeout
    if not conns:
        print 'SERVER - TIMED OUT'
        return
    
    print 'SERVER - SEND'
    try:
        remaining_msg = {} # for every socket: how much is left?
        for conn in conns:
            remaining_msg[conn] = msg_size

        send_start_time = {} # for every socket: when to start sending?
        for conn in conns[1:]: # the first socket starts right away
            send_start_time[conn] = time.time() + random.uniform(0, 5)

        # t = start_ss_monitoring(server_port, flows, filename, epoch)
        try:
            to_send = bytearray(os.urandom(BUFSIZE))
            while remaining_msg:
                sendready = select.select([], remaining_msg.keys(), [], 180)
                if not sendready[1]: # timed out
                    raise RuntimeError("select: not ready to send")

                for conn in sendready[1]:
                    if conn in send_start_time:
                        if send_start_time[conn] <= time.time():
                            del send_start_time[conn]
                        else:
                            continue # not ready yet, skip for now

                    remain = remaining_msg[conn]
                    to_send_now = min(BUFSIZE, remain)
                    sent_now = conn.send(to_send[0:to_send_now])
                    if sent_now == 0:
                        raise RuntimeError("send: nothing sent")
                    remain -= sent_now
                    if remain <= 0:
                        del remaining_msg[conn]
                    else:
                        remaining_msg[conn] = remain
        finally:
            pass
            # end_ss_monitoring(t)
    except:
        close_sockets(conns) # close sockets that have been opened
        raise                # before passing on the exception


def recv_from_sockets(sockets, msg_size):
    print 'CLIENT - RECV'
    recv_data = {}     # for every socket: array of pairs - when was how mich received?
    remaining_msg = {} # for every socket: how much is left?
    for conn in sockets:
        remaining_msg[conn] = msg_size
        recv_data[conn] = []
        
    while remaining_msg:
        recvready = select.select(remaining_msg.keys(), [], [], 180)
        if not recvready[0]: # timed out
            raise RuntimeError("select: not ready to receive")

        for conn in recvready[0]:
            recvdata_now = conn.recv(BUFSIZE)
            trecv = time.time()
            remaining_msg[conn] -= len(recvdata_now)
            if remaining_msg[conn] <= 0:
                del remaining_msg[conn]
            #log recv data
            recv_data[conn].append([trecv, len(recvdata_now)])

    return recv_data   


#server
def main(server_addr_list, server_port_start, data, epoch, mode, proto, filename, flows):  
    filename = filename + '-' + str(epoch)
    msg_size = int(data * 1024 * 1024)

    #tcpdump
    trace_file = 'trace-' + mode + '-DL-' + filename
    # dump = begin_tcpdump('any', trace_file)
    time.sleep(5)
    try:
        sockets = create_tcp_sockets(mode, proto, server_addr_list, server_port_start, flows, msg_size, filename)
        try:
            if mode == 'SERVER':
                send_over_sockets(sockets, msg_size, server_port_start, len(server_addr_list) * flows, filename, epoch)
            elif mode == 'CLIENT':
                recv_data = recv_from_sockets(sockets, msg_size)
                #Write to file
                for conn, goodput in recv_data.items():
                    host, port = conn.getsockname() #faster_plot_script expects local port
                    # log_recv_data_to_file(host, port, goodput, filename)
            print 'DONE'
            time.sleep(3) # cool off period before terminating trace
        finally:
            close_sockets(sockets)
    finally:
        #stop tcpdump
        # end_tcpdump(dump)
        time.sleep(3)
        print "COPY..."
        # subprocess.call('mv *TCP* /home/nornetpp/mp-core/mp-core-sbd-data', shell=True)


#usage:
def usage():
    this_script_filename = inspect.getfile(inspect.currentframe())
    print str(this_script_filename) + " [server IPs] [first port] [data amount (MB)] [epoch (int)] [mode SERVER/CLIENT] [proto TCP/MPTCP] [filename] [flows (int)]"
    sys.exit(0)


#SERVER:
if __name__ == '__main__':

     #SIGINT 
     signal.signal(signal.SIGINT, signal_handler)

     if len(sys.argv) == 9:
          server_addr_list = sys.argv[1].split(',')
          server_port_start = int(sys.argv[2])
          data = float(sys.argv[3])
          epoch = int(sys.argv[4])
          mode = sys.argv[5]
          proto = sys.argv[6]
          filename = sys.argv[7]
          flows = int(sys.argv[8])

          if mode != 'CLIENT' and mode != 'SERVER':
              usage()
          elif proto != 'TCP' and proto != 'MPTCP':
              usage()
          else:
              main(server_addr_list, server_port_start, data, epoch, mode, proto, filename, flows)
     else:
          usage()   

