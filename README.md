# MPQUIC-SBD: An implementation of RFC8382 for Shared Bottleneck Detection (SBD) in Multipath QUIC (MPQUIC)

This repository contains the sources of research work regarding Multipath-QUIC SBD.
[Multipath-QUIC from Q. Deconinck et al.](https://github.com/qdeconinck/mp-quic) is a Golang implementation of Multipath-QUIC.
It was initially forked from quic-go (https://github.com/lucas-clemente/quic-go).
Additional scheduler implementations are added in this work.

These schedulers are evaluated in a DASH video streaming scenario:
[Caddyserver](https://caddyserver.com/) is a open source Http server written in Golang making it easy to integrate MP-QUIC.
[AStream](https://github.com/pari685/AStream) serves as open-source DASH client.
AStream was also extended by using MP-QUIC as transport layer protocol.

All source code is targeted to run on Ubuntu 64-bit machines.

## Structure of this repository

Open source adaptations:
* [src/quic-go](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/quic-go) contains extended MP-QUIC implementation written in Golang.
* [src/caddy](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/caddy) contains Caddyserver with integrated MP-QUIC also written in Golang.
* [src/AStream](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/AStream) contains DASH client with interchangeable Transport protocol written in Python 2.7.
* [example](https://github.com/thomaswpp/mpquic-sbd/tree/master/example) contains example files and code for creating segments and representing mpd video.

Review adaptations:
The original repositories have not been integrated as recursive git modules but were copied instead.
Review changes by navigating into the corresponding subfolder and using **git diff**.

Original implementations:
* [src/dash/caddy](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/dash/caddy) is used to build a Caddyserver executable with local MP-QUIC. 
* [src/dash/client/proxy_module](https://github.com/thomaswpp/mpquic-sbd/tree/master/src/client/proxy_module) is a Python module that allows to issue http requests via local MP-QUIC.
Creating a Linux shared object (.so) allows bridging Go code into a Python module.

Example video setup:
* [example](https://github.com/thomaswpp/mpquic-sbd/tree/master/example) contains a DASH-streamable video and a corresponding sample Caddyserver configuration file. 

## Quickstart
```
# Clone repository and build sources
git clone https://github.com/deradev/mpquic-sbd
cd mpquic-sbd
./build.sh

# Run Caddyserver with sample Caddyfile and Multipath-QUIC
./src/dash/caddy/caddy -conf example/Caddyfile -quic -mp
# Run AStream client with sample video target and Multipath-QUIC
python src/AStream/dist/client/dash_client.py -m "https://localhost:4242/output_dash.mpd" -p 'basic' -q -mp
```

## Build

The Go code modules are build with Golang version 1.12.
Here used modules are build *outside* of GOPATH.
Herefore the local setup redirects their modular dependencies to the local implementations.

Build MP-QUIC:
```
cd src/quic-go
go build ./...
```
Notes: Go modules allow recursive build, this module must not necessarily be build explicitely.
The MP-QUIC module can be used by other Go modules via reference in their go.mod.

Build Caddyserver executable:
```
cd src/dash/caddy
go build
```

Build MP-QUIC shared object module:
```
cd src/dash/client/proxy_module
go build -o proxy_module.so -buildmode=c-shared proxy_module.go
```

## Use

### Prepare AStream DASH client
After building the proxy module, copy AStream dependencies.
(Probably also requires path change in line 5 of src/dash/client/proxy_module/conn.py)
```
cp src/dash/client/proxy_module/proxy_module.h src/AStream/dist/client/
cp src/dash/client/proxy_module/proxy_module.so src/AStream/dist/client/
cp src/dash/client/proxy_module/conn.py src/AStream/dist/client/
```

#### Prepare Caddyserver
For DASH video streaming Caddyserver needs setup to serve video chunks.
A file named [*Caddyfile*](https://caddyserver.com/tutorial/caddyfile) must be configured to this end.
Example Caddyfile:
```
https://localhost:4242 {
    root <URL to DASH video files>
    tls self_signed
}
```

#### Run Caddyserver
Run the created executable from src/dash/caddy:
```
# Run Caddyserver on single path.
./caddy -quic
# Or run caddy with multipath.
./caddy -quic -mp
```

#### Run AStream DASH client
Run the AStream client from src/AStream:
```
# Run AStream on single path.
python AStream/dist/client/dash_client.py -m <SERVER URL TO MPD> -p 'basic' -q
# Or run caddy with multipath and SBD.
python AStream/dist/client/dash_client.py -m <SERVER URL TO MPD> -p 'basic' -q -mp
```
#### Run Bulk Transfer client
```
# Run on single path.
python AStream/dist/client/bulk_transfer.py -m <SERVER URL TO MPD> -q

# Or run caddy with multipath
python AStream/dist/client/bulk_transfer.py -m <SERVER URL TO MPD> -q -mp
```

#### Run this project with mininet
In this project we run the experiment with three scenarios built in mininet, which can be seen in the directory network/mininet/.

We implemented three mininet topologies (Fig. x[REF]), where a multihomed client (AStream DASH player) is linked with two access networks and, at the other end-systems, a single-homed video server (Caddy) is linked with an access network. Between client and server, we have the following scenarios:
    - **Scenario 1**: NSB (non-shared bottlenecks) - client and server seperated from two  links, i..
    - **Scenario 2**: SB (shared bottleneck) - ...
    - **Scenario 3**: SHIFT (shifting SB NSB) - it combines SB and NSB scenarios into a single network topology.

```
# Run mininet experiment.
sudo python network/mininet/build_mininet_router<scenario_of_experiment>.py -nm 2 -p 'basic'
```
- **number_of_experiment**: there are three experiments for three different scenarios (1, 2 or 3)
 - **-nm**: is the client interface number, default 2;
 - **-p**: is the DASH algorithm to be executed, which can have three values (basic, netflix or sara);




If you want to change running the experiment with bulk transfer, you will have to uncomment line 196 in the code file of the scenarios (1, 2 or 3);


## References

This repository contains modified source code versions:
* [MP-QUIC](https://github.com/qdeconinck/mp-quic)
* [Caddyserver](https://github.com/caddyserver/caddy)
* [AStream](https://github.com/pari685/AStream)
