#!/usr/bin/pythonmpquic-sbd

import time
import sys
import argparse

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.util import dumpNodeConnections

from datetime import datetime

with_background = 1
number_of_interface_client = 2
download = False
playback = 'basic'
PATH_DIR = "/Workspace/mininet/mpquic-sbd/"

TC_QDISC_RATE = 20
TC_QDISC_LATENCY = 20


class LinuxRouter( Node ):
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


class NetworkTopo( Topo ):
    "A LinuxRouter connecting three IP subnets"

    def build( self, **_opts ):

        r1 = self.addHost('r1', cls=LinuxRouter, ip='10.0.0.1/30')
        r2 = self.addHost('r2', cls=LinuxRouter, ip='10.0.0.2/30')
        self.addLink(r1, r2, intfName1='r1-eth0', intfName2='r2-eth0')

        client = self.addHost('client', ip='10.0.1.2/24', defaultRoute='via 10.0.1.1')
        server = self.addHost('server', ip='10.0.2.2/24', defaultRoute='via 10.0.2.1')
        
        client1 = self.addHost('client1', ip='10.0.5.2/24', defaultRoute='via 10.0.5.1')
        client2 = self.addHost('client2', ip='10.0.7.2/24', defaultRoute='via 10.0.7.1')

        server1 = self.addHost('server1', ip='10.0.6.2/24', defaultRoute='via 10.0.6.1')
        server2 = self.addHost('server2', ip='10.0.8.2/24', defaultRoute='via 10.0.8.1')


        # client
        self.addLink( client, r1, intfName2='r1-eth1', params2={ 'ip' : '10.0.1.1/24' } )
        self.addLink( client, r1, intfName1='client-eth1', params1={ 'ip' : '10.0.3.2/24' }, intfName2='r1-eth2', params2={ 'ip' : '10.0.3.1/24' } )
        
        if number_of_interface_client > 2:
            self.addLink( client, r1, intfName1='client-eth2', params1={ 'ip' : '10.0.9.2/24' }, intfName2='r1-eth5', params2={ 'ip' : '10.0.9.1/24' } )

        if number_of_interface_client > 3:
            self.addLink( client, r1, intfName1='client-eth3', params1={ 'ip' : '10.0.11.2/24' }, intfName2='r1-eth6', params2={ 'ip' : '10.0.11.1/24' } )

        if number_of_interface_client > 4:
            self.addLink( client, r1, intfName1='client-eth4', params1={ 'ip' : '10.0.13.2/24' }, intfName2='r1-eth7', params2={ 'ip' : '10.0.13.1/24' } )

        # server
        self.addLink( server, r2, intfName2='r2-eth1', params2={ 'ip' : '10.0.2.1/24' } )

        self.addLink( client1, r1, intfName1='client1-eth0', params1={ 'ip' : '10.0.5.2/24' }, intfName2='r1-eth3', params2={ 'ip' : '10.0.5.1/24' } )
        self.addLink( client2, r1, intfName1='client2-eth0', params1={ 'ip' : '10.0.7.2/24' }, intfName2='r1-eth4', params2={ 'ip' : '10.0.7.1/24' } )

        #h4
        self.addLink( server1, r2, intfName1='server1-eth0', params1={ 'ip' : '10.0.6.2/24' }, intfName2='r2-eth3', params2={ 'ip' : '10.0.6.1/24' } )
        #h5
        #h6
        self.addLink( server2, r2, intfName1='server2-eth0', params1={ 'ip' : '10.0.8.2/24' }, intfName2='r2-eth4', params2={ 'ip' : '10.0.8.1/24' } )

def run():
    "Test linux router"
    topo = NetworkTopo()
    net = Mininet(topo=topo)  # controller is used by s1-s3
    net.start()

    #configuration r1
    
    net[ 'r1' ].cmd("route add default gw 10.0.0.2")
    net[ 'r1' ].cmd("tc qdisc add dev r1-eth0 root netem limit 1000 rate {0}Mbit".format(TC_QDISC_RATE))
      

    #configuration r2
    net[ 'r2' ].cmd("route add default gw 10.0.0.1")
    net[ 'r2' ].cmd("tc qdisc add dev r2-eth0 root netem limit 67 delay {0}ms rate {1}Mbit".format(TC_QDISC_LATENCY, TC_QDISC_RATE))
    

    #configuration client
    # This creates two different routing tables, that we use based on the source-address.
    net[ 'client' ].cmd("ip rule add from 10.0.1.2 table 1")
    net[ 'client' ].cmd("ip rule add from 10.0.3.2 table 2")
    # Configure the two different routing tables
    net[ 'client' ].cmd("ip route add 10.0.1.0/24 dev client-eth0 scope link table 1")
    net[ 'client' ].cmd("ip route add default via 10.0.1.1 dev client-eth0 table 1")

    net[ 'client' ].cmd("ip route add 10.0.3.0/24 dev client-eth1 scope link table 2")
    net[ 'client' ].cmd("ip route add default via 10.0.3.1 dev client-eth1 table 2")
       
    if number_of_interface_client > 2:
        net[ 'client' ].cmd("ip rule add from 10.0.9.2 table 3")
        net[ 'client' ].cmd("ip route add 10.0.9.0/24 dev client-eth2 scope link table 3")
        net[ 'client' ].cmd("ip route add default via 10.0.9.1 dev client-eth2 table 3")
    if number_of_interface_client > 3:
        net[ 'client' ].cmd("ip rule add from 10.0.11.2 table 4")
        net[ 'client' ].cmd("ip route add 10.0.11.0/24 dev client-eth3 scope link table 4")
        net[ 'client' ].cmd("ip route add default via 10.0.11.1 dev client-eth3 table 4")
    if number_of_interface_client > 4:
        net[ 'client' ].cmd("ip rule add from 10.0.13.2 table 5")
        net[ 'client' ].cmd("ip route add 10.0.13.0/24 dev client-eth4 scope link table 5")
        net[ 'client' ].cmd("ip route add default via 10.0.13.1 dev client-eth4 table 5")

    # default route for the selection process of normal internet-traffic
    net[ 'client' ].cmd("ip route add default scope global nexthop via 10.0.1.1 dev client-eth0")

    #configuration server
    # This creates two different routing tables, that we use based on the source-address.
    net[ 'server' ].cmd("ip rule add from 10.0.2.2 table 1")
    
    # Configure the two different routing tables
    net[ 'server' ].cmd("ip route add 10.0.2.0/24 dev server-eth0 scope link table 1")
    net[ 'server' ].cmd("ip route add default via 10.0.2.1 dev server-eth0 table 1")

    # default route for the selection process of normal internet-traffic
    net[ 'server' ].cmd("ip route add default scope global nexthop via 10.0.2.1 dev server-eth0")

    print "Dumping host connections"

    print "Testing network connectivity"

    print "Testing bandwidth between client and h4"

    info( '*** Routing Table on Router:\n' )

    user='mininet'

    #Run experiment
    print net[ 'server' ].cmd("cd /home/" + user + PATH_DIR)
    print net[ 'server' ].cmd("pwd")
    print net[ 'server' ].cmd("./run.sh")

    net[ 'client' ].cmd("cd /home/" + user + PATH_DIR)
    print net[ 'client' ].cmd("./run.sh")

    net[ 'server' ].cmd("nice -n -10 src/dash/caddy/caddy -conf /home/" + user + "/Caddyfile -quic -mp >> out &")

    
    for i in range(1,3):
       net['client{0}'.format(i)].cmd("cd /home/" + user + PATH_DIR) 
       net['server{0}'.format(i)].cmd("cd /home/" + user + PATH_DIR) 


    if with_background == 1:

        net['client1'].cmd("nice -n -10 ./background_sbd_original.py 'CLIENT' 10.0.5.2 9999 1 2 1 3000 &") 
        net['client2'].cmd("nice -n -10 ./background_sbd_original.py 'CLIENT' 10.0.7.2 9980 2 2 1 3000 &") 

        net['server1'].cmd("nice -n -10 python tcp_core_original.py 10.0.6.2 9999 20000 1 SERVER TCP teste.pcap 1 &") 
        net['server2'].cmd("nice -n -10 python tcp_core_original.py 10.0.8.2 9999 20000 1 SERVER TCP teste.pcap 1 &") 
        
        time.sleep(5)

        print net['server1'].cmd("nice -n -10 ./background_sbd_original.py 'SERVER' 10.0.5.2 9999 1 2 1 3000 &") 
        print net['server2'].cmd("nice -n -10 ./background_sbd_original.py 'SERVER' 10.0.7.2 9980 2 2 1 3000 &") 

        print net['client1'].cmd("nice -n -10 python tcp_core_original.py 10.0.6.2 9999 20000 1 CLIENT TCP testec.pcap 1 &") 
        print net['client2'].cmd("nice -n -10 python tcp_core_original.py 10.0.8.2 9999 20000 1 CLIENT TCP testec.pcap 1 &") 

    
    time.sleep(20)
    file_mpd = 'output_dash.mpd'
    if playback == 'sara':
        file_mpd = 'output_dash2.mpd'
        
    start = datetime.now()
    file_out = 'dados/out_{0}_{1}.txt'.format(playback, start.strftime("%Y-%m-%d.%H:%M:%S"))
    print(file_out)

    if download:
        cmd = "nice -n -10 python3 src/AStream/dist/client/dash_client.py -m https://10.0.2.2:4242/{0} -p '{1}' -d -q -mp >> {2} &".format(file_mpd, playback, file_out)
    else: 
        cmd = "nice -n -10 python3 src/AStream/dist/client/dash_client.py -m https://10.0.2.2:4242/{0} -p '{1}' -q -mp >> {2}".format(file_mpd, playback, file_out)
        #file_mpd = '4k60fps.webm'
        #cmd = "nice -n -10 python3 src/AStream/dist/client/bulk_transfer.py -m https://10.0.2.2:4242/{0} -p '{1}' -q -mp >> {2} &".format(file_mpd, playback, file_out)

    net[ 'client' ].cmd(cmd)


    end = datetime.now()
    print(divmod((end - start).total_seconds(), 60))

    while True:
        bg_pid = net['client1'].cmd('pgrep -f "/usr/local/bin/ITGRecv"')
        bg_pid += net['client1'].cmd('pgrep -f "/usr/local/bin/ITGSend"')
        bg_pid += net['client1'].cmd('pgrep -f "python tcp_core_original.py"')
        bg_pid += net['client1'].cmd('pgrep -f "python tcp_core.py"')
        lpid = [s for s in bg_pid.split('\r\n') if s.isdigit()]
        print('PID: ', lpid)
        if len(lpid) != 8:
            cmd = 'echo "Error! process quantities other diff 8 {0}"'.format(datetime.now())
            print(net[ 'client1' ].cmd(cmd))
        time.sleep(10)

    CLI( net )
    net.stop()

if __name__ == '__main__':


    parser = argparse.ArgumentParser(description='Mode execute Mininet')
    parser.add_argument('--background', '-b',
                   metavar='background',
                   type=int,
                   default=1,
                   help='execute with background or not')

    parser.add_argument('--number_client', '-nm',
                   metavar='number_client',
                   type=int,
                   default=2,
                   help='the number of interface client')

    parser.add_argument('--download', '-d',
                   metavar='download',
                   type=bool,
                   default=False,
                   help="Keep the video files after playback")

    parser.add_argument('--playback', '-p',
                   metavar='playback',
                   type=str,
                   default='basic',
                   help="Playback type (basic, sara, netflix, or all)")


    # Execute the parse_args() method
    args                       = parser.parse_args()
    with_background            = args.background
    number_of_interface_client = args.number_client
    download                   = args.download
    playback                   = args.playback


    setLogLevel( 'info' )
    run()



# src/dash/caddy/caddy -conf /home/mininet/Caddyfile -quic -mp
# python src/AStream/dist/client/dash_client.py -m https://10.0.1.2:4242/output_dash.mpd -p 'basic' -q -mp >> out
# sudo mn --custom build_mininet_router3.py --topo networkTopo --controller=remote,ip=127.0.0.1 --link=tc -x