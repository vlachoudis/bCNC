#!/bin/bash

#Show help
[ -z "$1" ] || [ "$1" = "-h" ] && {
	echo "
	Dummy GRBL simulator (allows connecting and streaming)

	Usage:
		$0 -h		#Show this help
		$0 -c		#Launch GRBL console
		$0 /tmp/ttyFAKE	#Listen at fake serial port
	"
	exit
}

#Create fake tty device and listen on it
[ "$1" != "-c" ] && {
	echo Listening at fake serial port: "$1"
	socat -dd PTY,raw,link="$1",echo=0 "EXEC:'$0' -c,pty,raw,echo=0"
	exit
	}

#Fake Grbl console
echo
echo "Grbl 1.1f ['$' for help]"
while read -s -n 1 byte; do
	echo -n "$byte" >/dev/stderr
	[ "$byte" = '?' ] && echo "<Idle|MPos:0.000,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>"
	[ -z "$byte" ] && echo ok && echo >/dev/stderr
done
