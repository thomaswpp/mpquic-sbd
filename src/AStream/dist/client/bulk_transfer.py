#!/usr/local/bin/python
import conn as glueConnection
import read_mpd
import urllib.parse
import urllib.request, urllib.error, urllib.parse
import random
import os
import sys
import errno
import ssl
import timeit
import http.client
import io
import json
import math
from string import ascii_letters, digits
from argparse import ArgumentParser
from multiprocessing import Process, Queue
from collections import defaultdict
from adaptation import basic_dash, basic_dash2, weighted_dash, netflix_dash
from adaptation import basic_dash3
from adaptation.adaptation import WeightedMean
from configure_log_file import configure_log_file, write_json
import config_dash
import dash_buffer
import time

# Constants
DEFAULT_PLAYBACK = 'BASIC'
DOWNLOAD_CHUNK = 1024

# Globals for arg parser with the default values
# Not sure if this is the correct way ....
MPD = None
LIST = False
PLAYBACK = DEFAULT_PLAYBACK
DOWNLOAD = False
SEGMENT_LIMIT = None

def get_bandwidth(data, duration):
    """ Module to determine the bandwidth for a segment
    download"""
    return data * 8/duration


def download_file(segment_url):
    segment_size = glueConnection.download_segment_PM(segment_url)
    if segment_size < 0:
        raise ValueError("invalid segment_size, connection dropped")
    return segment_size


def create_arguments(parser):
    """ Adding arguments to the parser """
    parser.add_argument('-m', '--MPD',                   
                        help="Url to the MPD File")
    parser.add_argument('-l', '--LIST', action='store_true',
                        help="List all the representations")
    parser.add_argument('-p', '--PLAYBACK',
                        default=DEFAULT_PLAYBACK,
                        help="Playback type (basic, sara, netflix, or all)")
    parser.add_argument('-n', '--SEGMENT_LIMIT',
                        default=SEGMENT_LIMIT,
                        help="The Segment number limit")
    parser.add_argument('-d', '--DOWNLOAD', action='store_true',
                        default=False,
                        help="Keep the video files after playback")
    parser.add_argument('-q', '--QUIC', action='store_true',
                        default=False,
                        help="Use QUIC as protocol")
    parser.add_argument('-mp', '--MP', action='store_true',
                        default=False,
                        help="Activate multipath in QUIC")
    parser.add_argument('-nka', '--NO_KEEP_ALIVE', action='store_true',
                        default=False,
                        help="Keep alive connection to Server")
    parser.add_argument('-s', '--SCHEDULER',
                        default='lowRTT',
                        help="Scheduler in multipath usage (lowRTT, RR, redundant)")
    parser.add_argument('-c', '--CC',
                        default='olia',
                        help="Congestion control scheme")
    parser.add_argument('-f', '--fec', action='store_true', default=False,
                        help='Enable FEC')
    parser.add_argument('-b', '--BITRATE', default=None,
                        help='Force to use a specific bitrate')
    parser.add_argument('--fecConfig', default='xor4',
                        help='FEC configuration to use')

def main():

    # insira a url de um arquivo grande armazenado la no servidor
    file_url = "https://10.0.2.2:4242/teste.mkv"
    
    parser = ArgumentParser(description='Process Client parameters')
    create_arguments(parser)

    args = parser.parse_args()
    globals().update(vars(args))
    configure_log_file(playback_type=PLAYBACK.lower())

    config_dash.JSON_HANDLE['playback_type'] = PLAYBACK.lower()
    if QUIC:
        config_dash.JSON_HANDLE['transport'] = 'quic'
    else: 
        config_dash.JSON_HANDLE['transport'] = 'tcp'
    if MP:
        config_dash.JSON_HANDLE['scheduler'] = SCHEDULER
    else:
        config_dash.JSON_HANDLE['scheduler'] = 'singlePath'
    # if fec:
    #     config_dash.JSON_HANDLE['fecConfig'] = fecConfig
    # else:
    #     config_dash.JSON_HANDLE['fecConfig'] = 'none'
    # config_dash.JSON_HANDLE['congestionControl'] = CC
    if not MPD:
        print("ERROR: Please provide the URL to the MPD file. Try Again..")
        return None

    glueConnection.setupPM(QUIC, MP, not NO_KEEP_ALIVE, SCHEDULER)
    glueConnection.startLogging(1000)
    try:
        start_time = timeit.default_timer()
        file_size = download_file(file_url)
        file_download_time = timeit.default_timer() - start_time
    except IOError as e:
        print("Unable to save segment %s" % e)
        return None
    print("throughput: %f" % get_bandwidth(file_size, file_download_time))
    glueConnection.stopLogging()
    glueConnection.closeConnection()
    
if __name__ == "__main__":
    sys.exit(main())
