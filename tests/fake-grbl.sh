#!/bin/sh
#Usage: fake-grbl.sh /tmp/ttyFAKE

[ -n "$1" ] && {
	socat -d-d PTY,raw,link="$1",echo=0 "EXEC:'$0',pty,raw,echo=0"
	exit
	}

echo
echo "Grbl 1.1f ['$' for help]"
while read -s -n 1 line; do
	echo -n "$line" >/dev/stderr
	[ "$line" = '?' ] && echo "<Idle|MPos:0.000,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>"
	[ -z "$line" ] && echo ok && echo >/dev/stderr
done
