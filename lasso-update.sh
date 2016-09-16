#! /bin/sh
URL=http://www.spamhaus.org/drop/drop.lasso
DROPLASSO=$(mktemp)
ACLFILE=$(mktemp)
POSTSCREEN_ACCESS_FILE=/etc/postfix/postscreen_access.cidr
DATE=$(date +%Y%m%d)

wget --quiet $URL -O $DROPLASSO

if [ -e $DROPLASSO ]
then
  # cut the source file on the semicolon
  # and prepare the destination file
  for network in $(cat $DROPLASSO | awk '{print $1}' |\
    grep -E "^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2}$")
  do
    echo -e "$network\treject" >> $ACLFILE
  done
fi

cp $POSTSCREEN_ACCESS_FILE{,.bkp$DATE}
cp $ACLFILE $POSTSCREEN_ACCESS_FILE
postfix reload
