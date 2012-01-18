#!/usr/bin/env bash
DEBUG="$1"
# replace the SRV list with your own machines
SRV="mail.example.net mail.example.com"
RBL="bl.spamcop.net cbl.abuseat.org b.barracudacentral.org dnsbl.invaluement.com ddnsbl.internetdefensesystems.com dnsbl.sorbs.net http.dnsbl.sorbs.net dul.dnsbl.sorbs.net misc.dnsbl.sorbs.net smtp.dnsbl.sorbs.net socks.dnsbl.sorbs.net spam.dnsbl.sorbs.net web.dnsbl.sorbs.net zombie.dnsbl.sorbs.net dnsbl-1.uceprotect.net dnsbl-2.uceprotect.net dnsbl-3.uceprotect.net pbl.spamhaus.org sbl.spamhaus.org xbl.spamhaus.org zen.spamhaus.org bl.spamcannibal.org psbl.surriel.com ubl.unsubscore.com dnsbl.njabl.org combined.njabl.org rbl.spamlab.com dnsbl.ahbl.org ircbl.ahbl.org dyna.spamrats.com noptr.spamrats.com spam.spamrats.com cbl.anti-spam.org.cn cdl.anti-spam.org.cn dnsbl.inps.de drone.abuse.ch httpbl.abuse.ch dul.ru korea.services.net short.rbl.jp virus.rbl.jp spamrbl.imp.ch wormrbl.imp.ch virbl.bit.nl rbl.suresupport.com dsn.rfc-ignorant.org ips.backscatterer.org spamguard.leadmon.net opm.tornevall.org netblock.pedantic.org black.uribl.com grey.uribl.com multi.surbl.org ix.dnsbl.manitu.net tor.dan.me.uk rbl.efnetrbl.org relays.mail-abuse.org blackholes.mail-abuse.org rbl-plus.mail-abuse.org dnsbl.dronebl.org access.redhawk.org db.wpbl.info rbl.interserver.net query.senderbase.org bogons.cymru.com"
for server in $SRV
do
    ip=$(dig +short $server)
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
            echo "$server ($ip) is in $rbl with code $result"
        fi
        if [[ ! -z "$DEBUG" && -z "$result" ]]
        then
            echo "\`->negative"
        fi
    done
done

