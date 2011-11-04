Postscreen Statistics Parser
============================

Simple script to compute some statistics on Postfix/Postscreen Activity
Run it against your postfix syslogs

Published under GPL v2



Examples:

1. short report on full log file
---------------------------------
<code>
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
</code>

2. get the statistics for a specific IP only
--------------------------------------------
<code>
$ python postscreen_stats.py -f maillog.1 -r ip -i 1.2.3.4
Filtering results to match: 1.2.3.4
1.2.3.4
    connections count: 2
    first seen on 2011-10-22 09:37:54
    last seen on 2011-10-22 09:38:00
    DNSBL count: 1
    DNSBL ranks: ['6']
    HANGUP count: 2
</code>


3. Geo Localisation of blocked IPs
-----------------------------------

Use the '-g' switch to activate geolocalisation against hostip.info. At the moment, there are two big limitations to geolocalisation:
    1. It's slow ! Don't expect to get more than 2/3 IPs per second. So if you have 2000 IPs to geolocalise, it will take a while to run
    2. It only gives the Country of the IP. I didn't find the need to query the whole GPS data, but that's easy enough to change.

<code>
$ python postscreen_stats.py -f 10000maillog -r short -g

=== Postscreen statistics ===
4 COMMAND COUNT LIMIT
2 COMMAND PIPELINING
555 CONNECT
75 DNSBL
28 HANGUP
0 NOQUEUE 450
147 NOQUEUE 450 deep protocol test reconnection
68 PASS NEW
387 PASS OLD
12 PREGREET
8 WHITELISTED

=== Clients statistics ===
3 avg. dnsbl rank
248 clients
0 reconnections

=== First reconnection delay (graylist) ===
delay| <10s   |>10to30s| >30to1m| >1to5m | >5to30m|>30mto2h| >2hto5h|>5hto12h|>12to24h| >24h   |
count|0       |0       |0       |0       |0       |0       |0       |0       |0       |0       |

=== Blocked IPs per country ===
[('US', 56), ('XX', 17), ('RU', 1), ('RO', 1), ('IN', 1)]
</code>
