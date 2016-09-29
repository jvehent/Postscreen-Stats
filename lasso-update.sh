#!/bin/bash
set -u
URL=https://www.spamhaus.org/drop/drop.lasso
DROPLASSO=$(mktemp)
ACLFILE=$(mktemp)
POSTSCREEN_ACCESS_FILE=/etc/postfix/postscreen_access.cidr
DATE=$(date +%Y%m%d)

# Try to use wget first, otherwise curl
if ! wget --quiet -O "$DROPLASSO" $URL ;
then
  curl --silent -o "$DROPLASSO" $URL
fi

if [ -e "$DROPLASSO" ] ;
then
  # cut the source file on the semicolon
  # and prepare the destination file
  awk '{print $1}' "$DROPLASSO" |\
    grep -E "^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2}$" |\
    while IFS= read -r network
  do
    echo -e "$network\treject" >> "$ACLFILE"
  done
fi

cp $POSTSCREEN_ACCESS_FILE{,.bkp"$DATE"}
cp "$ACLFILE" $POSTSCREEN_ACCESS_FILE
postfix reload
