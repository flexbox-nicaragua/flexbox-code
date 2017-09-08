#!/bin/bash
for f in *.log
do
  echo "Processing $f file..."
  # take action on each file. $f store current file name
  tail -100 $f > tmp.log ; cat tmp.log > $f ; rm tmp.log
done


