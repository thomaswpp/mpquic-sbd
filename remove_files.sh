#!/bin/bash

for file in $(find -type f)
  do
   if  [[ $file == ./dados/output*.csv ]] || [[ $file == ./dados/output*.pcap ]] || [[ $file == ./dados/rtt*.csv ]] || [[ $file == ./dados/stats*.csv ]] || [[ $file == ./dados/diff*.csv ]] || [[ $file == ./out ]] || [[ $file == ./dados/group*.csv ]] || [[ $file == ./output_dash.mpd ]]; then
	echo "Remove a file: \"$file\""
	rm $file
   fi
done
