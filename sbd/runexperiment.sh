#!/bin/bash

for file in $(find -type f)
  do
   if [[ $file == ./conn*.csv ]] || [[ $file == ./diff*.csv ]] || [[ $file == ./data*.csv ]]; then
	echo "Remove a file: \"$file\""
	rm $file
   fi
done

#
# for i in {0..2}; do
#     d=$[$i + 1]
#     cmd=$(printf 'go run app/main.go conn%s.csv diff%s.csv data%s.csv %s ' "$d" "$d" "$d" "$i")
#     echo $cmd
#     $cmd
# done

for i in {0..0}; do
    d=$[$i + 3]
    cmd=$(printf 'go run app/main.go %s ' "$d")
    echo $cmd
    $cmd
done
