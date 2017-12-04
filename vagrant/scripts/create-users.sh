#!/bin/sh

id -u treadmld &>/dev/null || useradd treadmld
id -u tm_user1 &>/dev/null || useradd tm_user1
id -u tm_user2 &>/dev/null || useradd tm_user2
id -u tinydns &>/dev/null || useradd tinydns
id -u tinydnslog &>/dev/null || useradd tinydnslog
id -u tinydnstcp &>/dev/null || useradd tinydnstcp
