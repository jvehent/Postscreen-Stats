Postscreen Statistics Parser
============================

Simple script to compute some statistics on Postfix/Postscreen Activity
Run it against your postfix syslogs

Published under GPL v2

Usage
-------

    postscreen_stats.py
        parses postfix logs to compute statistics on postscreen activity

    usage: postscreen_stats.py <-y|--year> <-r|--report|-f|--full>
   
    <-a|--action>   action filter with operators | and &
                        ex. 'PREGREET&DNSBL|HANGUP' => ((PREGREET and DNSBL) or HANGUP)
                        ex. 'HANGUP&DNSBL|PREGREET&DNSBL' 
                            => ((HANGUP and DNSBL) or (PREGREET and DNSBL)

    <-f|--file>     log file to parse (default to /var/log/maillog)

    <-g|--geoloc>   /!\ slow ! ip geoloc against hostip.info (default disabled)

    <--geofile>     path to a maxmind geolitecity.dat. if specified, with the -g switch
                   the script uses the maxmind data instead of hostip.info (faster)

    <-G>            when using --geofile, use the pygeoip module instead of the GeoIP module

    <-i|--ip>       filters the results on a specific IP

    <--mapdest>     path to a destination HTML file that will display a Google Map of the result
                    /!\ Require the geolocation, preferably with --geofile

    <-r|--report>   report mode {short|full|ip} (default to short)

    <-y|--year>     select the year of the logs (default to current year)

    Julien Vehent (http://1nw.eu/!j) - https://github.com/jvehent/Postscreen-Stats


Basic usage
--------------

Generate a report form a syslog postfix log file.
If you are parsing logs from a year that is not the current year, use the -y option to specify the year of the logs.

    $ python postscreen_stats.py -f maillog.1 -r short -y 2011
    === unique clients/total postscreen actions ===
    2131/11010 CONNECT
    1/1 BARE NEWLINE
    30/33 COMMAND COUNT LIMIT
    13/16 COMMAND PIPELINING
    6/6 COMMAND TIME LIMIT
    463/536 DNSBL
    305/503 HANGUP
    12/15 NON-SMTP COMMAND
    1884/2258 NOQUEUE 450 deep protocol test reconnection
    1/42 NOQUEUE too many connections
    1577/1600 PASS NEW
    866/8391 PASS OLD
    181/239 PREGREET
    5/84 WHITELISTED
    
    === clients statistics ===
    4 avg. dnsbl rank
    505 blocked clients
    2131 clients
    840 reconnections
    32245.4285714 seconds avg. reco. delay
    
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

There are 3 GeoIP modes:
 1. Use hostip.info online geoip service. This is free but slow and not very accurate
 2. Use Maxmind's GeoIP database. You can use either the free version of the DB from their website, or get a paid version. 

To use hostip.info, just set the -g option.
To use maxmind, set the --geofile to point to your Maxmind DB (ie. --geofile=/path/to/GeoIPCity.dat)
By default, geofile use the GeoIP python module, but if you prefer to use pygeoip instead, set the -G option as well.
    
    $ ./postscreen_stats.py -r short --geofile=../geoip/GeoIPCity.dat -G -f maillog.3 -y 2011
   
   [....]
 
    === Top 20 Countries of Blocked Clients ===
     167 (33.00%) United States
      59 (12.00%) India
      33 ( 6.50%) Russian Federation
      26 ( 5.10%) Indonesia
      23 ( 4.60%) Pakistan
      21 ( 4.20%) Vietnam
      20 ( 4.00%) China
      13 ( 2.60%) Brazil
      11 ( 2.20%) Korea, Republic of
       9 ( 1.80%) Belarus
       8 ( 1.60%) Turkey
       7 ( 1.40%) Iran, Islamic Republic of
       7 ( 1.40%) Ukraine
       6 ( 1.20%) Kazakstan
       6 ( 1.20%) Chile
       5 ( 0.99%) Italy
       5 ( 0.99%) Romania
       4 ( 0.79%) Poland
       4 ( 0.79%) Spain
       3 ( 0.59%) Afghanistan

Geo IP database installation
-----------------------------------
Using the MaxMind free database at http://www.maxmind.com/app/geolitecity
    1. Download the database and extract GeoLiteCity.dat at the location of your choice
    2. install the GeoIP maxmind package
        # aptitude install python-geoip
    3. launch postscreen_stats with --geofile="/path/to/geolistcity.dat"

Google Map of the blocked IPs
-----------------------------------
You can use the --geomap option to create an HTML file with a map of the blocked IPs.
    $ ./postscreen_stats.py -f maillog.3 -r none -y 2011 --geofile=../geoip/GeoIPCity.dat -G --mapdest=postscreen_report_2012-01-15.html

    Google map will be generated at postscreen_report_2012-01-15.html
    using MaxMind GeoIP database from ../geoip/GeoIPCity.dat
    Creating HTML map at postscreen_report_2012-01-15.html
