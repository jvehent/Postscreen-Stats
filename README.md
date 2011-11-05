Postscreen Statistics Parser
============================

Simple script to compute some statistics on Postfix/Postscreen Activity
Run it against your postfix syslogs

Published under GPL v2



Examples:

Short report on full log file
---------------------------------

    $ python postscreen_stats.py -f maillog.1 -r short -y 2011
    === Postscreen statistics ===
    0 BLACKLISTED
    33 COMMAND COUNT LIMIT
    0 COMMAND LENGTH LIMIT
    16 COMMAND PIPELINING
    6 COMMAND TIME LIMIT
    11010 CONNECT
    536 DNSBL
    503 HANGUP
    42 NOQUEUE MAXCONN
    0 NOQUEUE PORT BUSY
    2258 NOQUEUE REJECT 450 (graylist)
    1600 PASS NEW
    8391 PASS OLD
    239 PREGREET
    84 WHITELISTED
    === Clients statistics ===
    4 avg. dnsbl rank
    840 came back count
    2131 clients
    32245 seconds avg. reco. delay
    === First reconnection delay (graylist) ===
    delay| <10s   |>10to30s| >30to1m| >1to5m | >5to30m|>30mto2h| >2hto5h|>5hto12h|>12to24h| >24h   |
    count|12      |21      |21      |196     |261     |88      |40      |29      |53      |119     |
       % |1.4     |2.5     |2.5     |23      |31      |10      |4.8     |3.5     |6.3     |14      |


Get the statistics for a specific IP only
--------------------------------------------

    $ python postscreen_stats.py -f maillog.1 -r ip -i 1.2.3.4
    Filtering results to match: 1.2.3.4
    1.2.3.4
        connections count: 2
        first seen on 2011-10-22 09:37:54
        last seen on 2011-10-22 09:38:00
        DNSBL count: 1
        DNSBL ranks: ['6']
        HANGUP count: 2



Geo Localisation of blocked IPs
-----------------------------------


Use the '-g' switch to activate geolocalisation against hostip.info. At the moment, there are two big limitations to geolocalisation:
1. It's slow ! Don't expect to get more than 2/3 IPs per second. So if you have 2000 IPs to geolocalise, it will take a while to run
2. It only gives the Country of the IP. I didn't find the need to query the whole GPS data, but that's easy enough to change.

    $ python postscreen_stats.py -f maillog.1 -r short -g
    
    === Postscreen statistics ===
    1 BARE NEWLINE
    33 COMMAND COUNT LIMIT
    16 COMMAND PIPELINING
    6 COMMAND TIME LIMIT
    11010 CONNECT
    536 DNSBL
    503 HANGUP
    2258 NOQUEUE 450 deep protocol test reconnection
    42 NOQUEUE too many connections
    1600 PASS NEW
    8391 PASS OLD
    239 PREGREET
    84 WHITELISTED
    
    === Clients statistics ===
    4 avg. dnsbl rank
    2131 clients
    
    === Blocked IPs per country ===
    [('XX', 238), ('US', 162), ('IN', 21), ('ID', 10), ('RU', 9), ('EU', 5), ('VN', 4), ('BR', 3), ('DE', 3), ('CO', 3), ('CA', 3), ('KR', 3), ('UK', 3), ('JP', 2), ('RO', 2), ('CN', 2), ('IT', 2), ('AR', 2), ('AU', 2), ('KZ', 2), ('MX', 2), ('FR', 1), ('BG', 1), ('BO', 1), ('NL', 1), ('PT', 1), ('TW', 1), ('TR', 1), ('TN', 1), ('LT', 1), ('PA', 1), ('PK', 1), ('PH', 1), ('PL', 1), ('CM', 1), ('IQ', 1), ('CZ', 1), ('ES', 1), ('SZ', 1), ('KE', 1), ('MW', 1), ('SA', 1), ('UA', 1)]

