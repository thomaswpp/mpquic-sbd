# MPQUIC-SBD: Multipath QUIC (MPQUIC) with support of Shared Bottleneck Detection (SBD) from the RFC8382 standard
 
This repository contains open software artefacts we have implemented and joined with other repositories for research purposes of the following publication: 

> **[1] A First Look at Adaptive Video Streaming over Multipath QUIC with Shared Bottleneck Detection. To appear in Proceedings of The 14th ACM Multimedia Systems Conference (MMSys’23), June 07-10, 2023, BC, Vancouver, Canada.**


To enable SBD support in MPQUIC protocol, we have implemented the [RFC8382 standard](https://www.rfc-editor.org/rfc/rfc8382.html) in golang into the [MPQUIC implementation](https://multipath-quic.org), which in turn is extended from the [QUIC implementation](https://github.com/lucas-clemente/quic-go). 


## 1. This repository

This repository contains the following open-source code: 
* [src/quic-go](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/quic-go): the popular [MPQUIC implementation](https://multipath-quic.org/) in golang we extend to include SBD.
* [src/caddy](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/caddy): the [Caddy HTTP server implementation](https://caddyserver.com/) in golang.
* [src/AStream](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/AStream): a [DASH player](https://github.com/pari685/AStream) emulator in python. 
* [example](https://github.com/thomaswpp/mpquic-sbd/tree/master/example): files and scripts to process the video segments and manifest MPD files.
* [src/dash/client/proxy_module](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/dash/client/proxy_module): a client-side proxy module which provides an interface through a shared object (`.so`) to enable MPQUIC implementations (in golang) underneath the AStream DASH player (in python).

All the source code files are targeted to run on Linux 64-bit hosts.

## 2. Guidelines

To run MPQUIC-SBD:

 1. If you want to **reproduce our experimental setup and measurements in [1]**, you should use our VM (QEMU/KVM image) ready to run the experiments. For more instructions, go to Section 3.

 2. If you have your own experimental environment, you can download and install the MPQUIC-SBD artefacts by yourself. For more instructions, go to Section 4.

## 3. Quickstart to reproduce the experiments from a prepared VM image

The VM image is a KVM ([Kernel-based Virtual Machine](https://www.linux-kvm.org)) with Ubuntu 14.04 LTS inside, in which we have extended from the default [MPQUIC implementation](https://github.com/qdeconinck/mp-quic) to enable the SBD support based on [RFC8382](https://www.rfc-editor.org/rfc/rfc8382.html). All the required files (i.e., source code files, video segments files and MPD, scripts) and tools are installed and ready to run from that VM image.



### 3.1 Prepare the experimental environment

To reproduce the experiments and measurements in [1], you have to firstly: 

 1. Have a Linux host. For ease install, we suggest a user-friendly Linux such as Ubuntu. For instance, we installed Ubuntu 20.04.5 LTS in our host, which is consisted of a server node HP Proliant ML30 Gen9, Intel Xeon 4-Core 3GHz, 8GB RAM, 1TB hard disk.
 2. Download our prepare VM (QEMU/KVM) image from:
 ```
 https://drive.google.com/drive/folders/15Ei5wULQDCXceoCVAE-vPrl5-oS8Ugi1?usp=share_link
 ```
 3. Install the KVM package on your Linux host. Instructions are available at the [KVM webpage](https://www.linux-kvm.org).

 4. Install the Virtual Manager Machine `virt-manager` to launch the VM. Instructions are available at the [virt-manager webpage](https://virt-manager.org/).

### 3.2 Launching the VM 

To launch the VM from `virt-manager` in your Linux host, open a terminal prompt and enter:
```
$ sudo virt-manager
```

Then, click on 'File' -> 'New Virtual Machine' to create a new VM in your disk: 
 1. Choose how you would like to install the operating system. Choose the option ‘Local install media (ISO image or CDROM)’, then select from your folder the prepared VM image file (QEMU/KVM) you downloaded. 
 2. Choose the operating you are installing by entering/selecting in the textbox 'Generic default'.
 3. Choose the memory and CPU settings. For instance, we defined ~7GB RAM and 4 CPUs cores for the VM to run the experiments.
 4. To begin the installation, give a name to your VM (e.g., 'mpquic-sbd'), keep the default network configurations (NAT). 
 5. Then, click on ‘Finish’ button.

Once you created your VM from our QEMU/KVM image, then click on the right-button on your mouse over the VM and select the option 'run'. 

### 3.3 Login the VM

Login the VM with following user credentials:

User: `mininet`

Password: `mininet`

### 3.4 Run our experiments 

To run our experimental setup in [1]:

```
$ cd Workspace/mpquic-sbd/
```

As we discuss in [1] (Figure 4 in [1]), our experiments regards network scenarios where a multihomed client (AStream DASH player) is linked with two access networks and, at the other end-system, a single-homed video server (Caddy HTTP server) is linked with an access network. Thus, we have a MPQUIC session of 2 subflows for the DASH client to download the video segment files from the HTTP server.

Specifically, we implemented three network scenarios on mininet emulator (source files can be found in network/mininet/), in which the the paths of 2 MPQUIC subflows between client and server can be of:
 - **`<1>`**: NSB (non-shared bottlenecks) - each subflow pass through distinct bottleneck links, i.e., they do not share network resources.
 - **`<2>`**: SB (shared bottleneck) - the 2 MPQUIC subflows flow through the same bottleneck link, i.e., they share the same network resource.
 - **`<3>`**: SHIFT (shifting SB-NSB) - we alternate the bottlenecks by shifting between SB and NSB for each 40 seconds along with the MPQUIC session.

To run the experiments for video transmission over MPQUIC-SBD on mininet emulator:

```
$ sudo python network/mininet/build_mininet_router<scenario>.py -nm 2 -p '<ABR>'
```
where:
 - **`<scenario>`**: is the number of the desired experiment. Enter `1` for NSB, `2` for SB, or `3` for SHIFT. 
 - **`-nm`**: is the number of client network interface controller. Unless you changed the network scenarios, always enter `2`, since the DASH client is dual-homed in our experiments.
- **`-p`**: is the ABR (Adaptive Bit Rate) algorithm to run on the DASH client application (AStream). We have three available ABR algorithm implementations in AStream: `'basic'`, which is a throughput-based algorithm (TBA); `'netflix'`, which is buffer-based algorithm (BBA), or `'sara'` which is hybrid TBA/BBA algorithm.

To run experiments of bulk transfers (typically, a long-lived session with continuous transmission) over MPQUIC-SBD on mininet emulutator, you have to uncomment line 196 in the source code files (available in network/mininet/) of the above-mentioned network scenarios (1, 2 or 3). Then, run again the command line above.


## 3.5 Verify the experimental results 

Note:
> **It is important to notice that AStream only emulates a DASH video player. It is not a DASH player of production. This means that you will not see any video window screen during the experiments. Moreover, while the AStream request and download the video segments, it does not save them in the file system, i.e., upon finishing an experiment, there are no dowloaded video segment files stored in the AStream's folders at the client node.**
> **You can find the video files in the server node in `dash/video/run/`.**

The experimental results must be processed from the output files generated by AStream in `Workspace/mpquic-sbd/ASTREM_LOGS`:

* `ASTREAM_<DATE>.json`: this file stores the results processed by AStream. It includes: video segment information for each downloaded segment, transport protocol information, playback information, and video metadata.
* `DASH_BUFFER_LOG_<DATE>.csv`: this file store the events regarding the AStream buffer manipulation. It provides for each event: epoch time, current playback time, current buffer size, current playback state,	action	bitrate.
* `output_<ABR>_<DATE>.txt`: this is a log file with all the events occurred during the AStream execution. It includes: timestamp, the corresponding code line, type of log, and textual description of the event. To extract results, this log file has to be parsed. 

In the next section, we provide instruction on how to deploy MPQUIC-SBD in your experimental environment. If you do not want to reproduce our experiments but just want to install our artefacts in your system, then follow the instructions of the next section. 

## 4. Deploy MPQUIC-SBD in your experimental environment

### 4.1 Clone and build

To clone our repository and build sources:
```
$ git clone https://github.com/thomaswpp/mpquic-sbd.git
$ cd mpquic-sbd
$ ./build.sh
```

### 4.2 Build the applications individually

**If you built all from `./build.sh`, then it is done.**

Otherwise, if you want to build the applications individually, follow instructions bellow.

The Go modules are implemented from golang version 1.12. 
Here, the used modules are built *outside* of `GOPATH`.
The local setup redirects the modular dependencies to the local implementations.

To build MPQUIC-SBD:
```
$ cd src/quic-go
$ go build ./...
```
The Go modules allow recursive build, so that this module must not necessarily be build explicitely.
The MPQUIC module can be used by other Go modules via reference in their go.mod.

To build Caddy server:
```
$ cd src/dash/caddy
$ go build
```

To build the client proxy module in a shared object (.so) to enable MPQUIC (in go) to work transparently underneath AStream DASH player (in python):
```
$ cd src/dash/client/proxy_module
$ go build -o proxy_module.so -buildmode=c-shared proxy_module.go
```

After building the proxy module, copy AStream dependencies.
(Probably also requires path change in line 5 of src/dash/client/proxy_module/conn.py)
```
$ cp src/dash/client/proxy_module/proxy_module.h src/AStream/dist/client/
$ cp src/dash/client/proxy_module/proxy_module.so src/AStream/dist/client/
$ cp src/dash/client/proxy_module/conn.py src/AStream/dist/client/
```

### 4.3 Configure and run the video server

For the DASH streaming, Caddy server needs a configuration to serve the video segments. 
To this end, a file named [*Caddyfile*](https://caddyserver.com/tutorial/caddyfile) must be configured.

Example of a Caddyfile:
```
https://localhost:4242 {
    root <URL to DASH video files>
    tls self_signed
}
```

Run the server from `src/dash/caddy`.

For a single-path server:
```
$ ./caddy -quic
```

For a multi-path server:
```
$ ./caddy -quic -mp
```
 
### 4.4 Run the DASH client

Run the AStream client from `src/AStream`.

For a single-path client:
```
$ python AStream/dist/client/dash_client.py -m <SERVER URL TO MPD> -p 'basic' -q
```

For a multi-path client:
```
$ python AStream/dist/client/dash_client.py -m <SERVER URL TO MPD> -p 'basic' -q -mp
```

The parameter `<SERVER URL TO MPD>` has to be entered in doble quotes like this: 
```
$ python AStream/dist/client/dash_client.py -m "https://localhost:4242/output_dash.mpd" -p 'basic' -q -mp
```

### 4.5 Bulk transfers

If you want to experiment MPQUIC-SBD in bulk transfers, you have to use the script `bulk_transfer.py`.

For a single-path client:
```
python AStream/dist/client/bulk_transfer.py -m <SERVER URL TO MPD> -q
```

For a multi-path client:
```
python AStream/dist/client/bulk_transfer.py -m <SERVER URL TO MPD> -q -mp
```

# Acknowledgements

This repository contains open software artefacts we have joined with other repositories. 
We are thankful to:

- **AStream: a rate adaptation model for DASH.** Available at https://github.com/pari685/AStream
- **Caddy Server.** Available at https://caddyserver.com
- **Multipath QUIC.** Available at https://multipath-quic.org
- **MAppLE: MPQUIC Application Latency Evaluation platform.** Available at https://github.com/vuva/MAppLE
- **Multipath-QUIC schedulers for video streaming applications.** Available at https://github.com/deradev/mpquicScheduler
