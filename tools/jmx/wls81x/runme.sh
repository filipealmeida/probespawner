#!/usr/bin/env sh


echo THIS NEEDS JAVA \< 1.5, JYTHON ~= 2.2.x and your weblogic.jar on the CLASSPATH
echo -- hit enter to continue --
read blah

CLASSPATH="weblogic.jar:json_simple-1.1.jar:joda-time-1.4.jar:log4j-1.2.17.jar" 
jython wls81x.py wls81x.json


