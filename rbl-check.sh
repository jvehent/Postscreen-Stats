#!/bin/bash
DEBUG="$1"
# Replace the SRV list with your own machines' full Internet DNS names
SRV="localhost"
# Build up the RBL list using the bash += append operator
RBL="bl.spamcop.net b.barracudacentral.org zen.spamhaus.org free.v4bl.org "
RBL+="dnsbl.sorbs.net spam.dnsbl.sorbs.net truncate.gbudb.net all.s5h.net "
RBL+="dnsbl-1.uceprotect.net dnsbl-2.uceprotect.net dnsbl-3.uceprotect.net "
RBL+="bl.spamcannibal.org psbl.surriel.com ubl.unsubscore.com db.wpbl.info "
RBL+="dyna.spamrats.com noptr.spamrats.com spam.spamrats.com "
RBL+="dnsbl.inps.de drone.abuse.ch httpbl.abuse.ch korea.services.net "
RBL+="short.rbl.jp virus.rbl.jp spamrbl.imp.ch wormrbl.imp.ch virbl.bit.nl "
RBL+="ips.backscatterer.org spamguard.leadmon.net dnsbl.tornevall.org "
RBL+="ix.dnsbl.manitu.net tor.dan.me.uk bad.psky.me rbl.efnetrbl.org "
RBL+="dnsbl.dronebl.org access.redhawk.org hostkarma.junkemailfilter.com "
RBL+="rbl.interserver.net query.senderbase.org bogons.cymru.com "
for server in $SRV
do
    # Resolve the DNS name into an Internet IP address
    ip=$(dig +short $server)
    # Testing IP address = 127.0.0.2
    #ip="127.0.0.2"
    # Reverse the IP address octets for DNSbl check format
    r_ip=$(echo $ip|awk -F"." '{for(i=NF;i>0;i--) printf i!=1?$i".":"%s",$i}')
    for rbl in $RBL
    do
        if [ ! -z "$DEBUG" ]
        then
            echo "testing $server ($ip) against $rbl"
        fi
        result=$(dig +short $r_ip.$rbl)
        if [ ! -z "$result" ]
        then
            # Some DNSbls return multiple results, change newlines to spaces
            echo -n "$server ($ip) is in $rbl with result ${result//$'\n'/ }"
            # Also try to get any TXT DNS records
            text=$(dig +short $r_ip.$rbl TXT)
            if [ ! -z "$text" ]
            then
                echo " and text ${text//$'\n'/ }"
            else
                echo ""
            fi
        fi
        if [[ ! -z "$DEBUG" && -z "$result" ]]
        then
            echo "\`->negative"
        fi
    done
done
