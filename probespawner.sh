#!/usr/bin/env sh

for i in `find . -name \*.jar`; do
  CLASSPATH=${CLASSPATH}:${i}
done
export CLASSPATH

if [ $# -gt 0 ] && [ -s $1 ]; then
  file=$1
  jython probespawner.py --configuration=${file}
else
  echo Usage: $0 \<JSONCONFIGURATION\>
fi

