#!/usr/bin/env python

# Parses the postscreen logs and display stats
# jvehent - 20120419

import re
import time
import calendar
import datetime
import getopt
import sys
import urllib
from collections import defaultdict
from decimal import *
from types import *

def usage():
    print   '''
postscreen_stats.py
    parses postfix logs to compute statistics on postscreen activity

usage: postscreen_stats.py -f mail.log

  -a|--action=   action filter with operators | and &
                      ex. 'PREGREET&DNSBL|HANGUP' = ((PREGREET and DNSBL) or HANGUP)
                      ex. 'HANGUP&DNSBL|PREGREET&DNSBL' 
                          = ((HANGUP and DNSBL) or (PREGREET and DNSBL)
  
  -f|--file=     log file to parse (default to /var/log/maillog)
  
  -g            /!\ slow ! ip geoloc against hostip.info (default disabled)
  
  --geofile=    path to a maxmind geolitecity.dat. if specified, with the -g switch
                  the script uses the maxmind data instead of hostip.info (faster)
  
  -G            when using --geofile, use the pygeoip module instead of the GeoIP module
  
  -i|--ip=      filters the results on a specific IP
  
  --mapdest=    path to a destination HTML file that will display a Google Map of the result
                  /!\ Require the geolocation, preferably with --geofile

  --map-min-conn=   When creating a map, only map the IPs that have connected X number of times
  
  -r|--report=  report mode {short|full|ip|none} (default to short)
  
  -y|--year=    select the year of the logs (default to current year)
  
  --rfc3339     to set the timestamp type to "2012-04-13T08:53:00+02:00" instead of the regular syslog format "Oct 23 04:02:17"

example: $ ./postscreen_stats.py -f maillog.3 -r short -y 2011 --geofile=../geoip/GeoIPCity.dat -G --mapdest=postscreen_report_2012-01-15.html

Julien Vehent (http://1nw.eu/!j) - https://github.com/jvehent/Postscreen-Stats
'''

# convert the syslog time stamp in unix format and store it
def gen_unix_ts(syslog_date):
    ts = 0
    unix_ts = 0
    now_ts = datetime.datetime.now()
    unix_ts = now_ts
    if RFC3339:
        date = syslog_date.split('+', 1)
        # example format: 2012-04-13T08:53:00+02:00
        ts = time.strptime(date[0], '%Y-%m-%dT%H:%M:%S')
        unix_ts = time.mktime(ts)
    else:
        # add the year
        syslog_date = str(YEAR) + " " + syslog_date
        # example format: 2011 Oct 23 04:02:17
        ts = time.strptime(syslog_date, '%Y %b %d %H:%M:%S')
        unix_ts = time.mktime(ts)

    # check if the unix_ts is not in the future
    if unix_ts > time.mktime(now_ts.timetuple()):
        print   "Time is in the future... ?"
        print   "Are you really parsing logs from " + str(YEAR) + " ?"
        sys.exit()
    else:
        return unix_ts

# each client's statistics are stored in the class below
class ClientStat:
    def __init__(self):
        self.logs = defaultdict(int)    # connection logs
        self.actions = defaultdict(int) # postscreen action logs
        self.dnsbl_ranks = []           # list of ranks triggered when blocked
        self.geoloc = defaultdict(int)

    # return true if the object matches the ACTION_FILTER
    def action_filter(self,filter):
        _pass_action_filter = 0
        _and_action_filter = 0
        # if the ACTION_FILTER is defined, iterate through the action 
        # and process only the clients with a matching action
        if filter == None:
            _pass_action_filter = 1
        else:
            for or_action in filter.split("|"):
                if _pass_action_filter == 0:
                    _and_action_filter = 0
                    for and_action in or_action.split("&"):
                        if self.actions[and_action] > 0 and _and_action_filter >= 0:
                            _and_action_filter = 1
                        else:
                            _and_action_filter = -1
                    if _and_action_filter > 0:
                        _pass_action_filter = 1
        if _pass_action_filter == 1:
            return True
        return False

# VARIABLES
IP_REGEXP = "((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}" \
            "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))"
IP_FILTER = "."
ACTION_FILTER = None
NOW = datetime.datetime.now()
YEAR = NOW.year
REPORT_MODE = "short"
LOG_FILE = "/var/log/maillog"
GEOLOC = 0
GEOFILE = ""
MAPDEST = ""
RFC3339 = False
MAP_MIN_CONN = 0

# position of 'postfix/postscreen' inside the logs
LOG_CURSOR = 5

# the list of clients ips and pointer to instance of class
ip_list = {}


# command line arguments
args_list, remainder = getopt.getopt(sys.argv[1:],
    'a:gGi:f:y:r:h', ['action=','geoloc','geofile=',
    'mapdest=','ip=','year=','report=','help', 'file=',
    'rfc3339','map-min-conn='])

for argument, value in args_list:
    if argument in ('-a', '--action'):
        ACTION_FILTER = str(value)
    elif argument in ('-g', '--geoloc'):
        GEOLOC = 1
    elif argument in ('--geofile'):
        GEOFILE = value
        if GEOLOC < 2:
            GEOLOC = 2
    elif argument in ('-G'):
        GEOLOC = 3
    elif argument in ('-f', '--file'):
        LOG_FILE = value
    elif argument in ('-y', '--year'):
        YEAR = value
    elif argument in ('--rfc3339'):
        RFC3339 = True
        LOG_CURSOR = 3
    elif argument in ('-i', '--ip'):
        IP_FILTER = value
        print "Filtering results to match:",IP_FILTER
    elif argument in ('-r', '--report'):
        if value in ('short','full','ip','none'):
            REPORT_MODE = value
        else:
            print "unknown report type"
            usage()
            sys.exit()
    elif argument in ('--mapdest'):
        MAPDEST = value
        print "Google map will be generated at",MAPDEST
    elif argument in ('--map-min-conn'):
	    MAP_MIN_CONN = int(value)
    elif argument in ('-h', '--help'):
        usage()
        sys.exit()

if GEOLOC > 0 and GEOFILE not in "":
    if GEOLOC == 2:
        import GeoIP
        gi = GeoIP.open(GEOFILE,GeoIP.GEOIP_MEMORY_CACHE)
    elif GEOLOC == 3:
        import pygeoip
        gi = pygeoip.GeoIP(GEOFILE,pygeoip.MEMORY_CACHE)
    print "using MaxMind GeoIP database from",GEOFILE

maillog = open(LOG_FILE)

for line in maillog:
    # Get postscreen logs only
    if "/postscreen[" in line:
        # apply the user defilter filter
        if re.match(IP_FILTER,line):
            # parse the log line
            line_fields = line.split(None, LOG_CURSOR+1)
            
            # parse the ip
            current_ip = '999.999.999.999'
            if re.search(IP_REGEXP, line_fields[LOG_CURSOR+1]):
                tmp = re.split(IP_REGEXP, line_fields[LOG_CURSOR+1], maxsplit=1)
                current_ip = tmp[1]
                del tmp
    
            if re.match("^CONNECT$", line_fields[LOG_CURSOR]):
                if RFC3339:
                    syslog_date = line_fields[0]
                else:
                    syslog_date = line_fields[0] + " " + line_fields[1] + \
                                " " + line_fields[2]
    
                # first time we see the client, initiate a class instance
                # store in in the client_list dictionary
                if current_ip not in ip_list:
                    ip_list[current_ip] = ClientStat()
                    ip_list[current_ip].logs["FIRST SEEN"] = \
                        gen_unix_ts(syslog_date) 
                    ip_list[current_ip].logs["LAST SEEN"] = \
                        gen_unix_ts(syslog_date)
                    # perform geo localisation
                    if GEOLOC > 0:
                        if GEOLOC == 1:
                            # geo localise ip
                            geoloc_url = "http://api.hostip.info/country.php?ip=" \
                                + current_ip
                            ip_list[current_ip].geoloc["country_code"] = \
                                urllib.urlopen(geoloc_url).read()
                        elif GEOLOC > 1:
                            ip_list[current_ip].geoloc = gi.record_by_addr(current_ip)

                # ip is already known, update the last_seen timestamp
                else:
                    ip_list[current_ip].logs["LAST SEEN"] = \
                        gen_unix_ts(syslog_date) 
                    
                ip_list[current_ip].logs["CONNECT"] += 1
    
            # client must be initialized to continue
            # the string matching is organized to test the most probable
            # value first, to speed things up
            elif current_ip in ip_list:
                    if re.match("^PASS$", line_fields[LOG_CURSOR]):
                        if re.search("^OLD", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["PASS OLD"] += 1
    
                            # if the connection count is 2, and the IP has already
                            # been rejected with a code 450 calculate the
                            # reconnection delay
                            if (ip_list[current_ip].logs["CONNECT"] == 2 
                                and ip_list[current_ip].\
                                actions["NOQUEUE 450 deep protocol test reconnection"] > 0):
                                ip_list[current_ip].logs["RECO. DELAY (graylist)"] = \
                                    ip_list[current_ip].logs["LAST SEEN"] \
                                    - ip_list[current_ip].logs["FIRST SEEN"]

                        elif re.search("^NEW", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["PASS NEW"] += 1 
    
                    elif re.match("^NOQUEUE:$", line_fields[LOG_CURSOR]):
                        if re.search("too many connections",
                            line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["NOQUEUE too many connections"] += 1
                        elif re.search("all server ports busy",
                            line_fields[LOG_CURSOR]):
                            ip_list[current_ip].actions["NOQUEUE all server ports busy"] += 1
                        elif re.search("450 4.3.2 Service currently unavailable",
                            line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["NOQUEUE 450 deep protocol test reconnection"] += 1
 
                    elif re.match("^HANGUP$", line_fields[LOG_CURSOR]):
                        ip_list[current_ip].actions["HANGUP"] += 1
    
                    elif re.match("^DNSBL$", line_fields[LOG_CURSOR]):
                        ip_list[current_ip].actions["DNSBL"] += 1
                        # store the rank
                        rank_line = line_fields[LOG_CURSOR+1].split(None)
                        ip_list[current_ip].dnsbl_ranks.append(rank_line[1])
    
                    elif re.match("^PREGREET$", line_fields[LOG_CURSOR]):
                        ip_list[current_ip].actions["PREGREET"] += 1
    
                    elif re.match("^COMMAND$", line_fields[LOG_CURSOR]):
                        if re.search("^PIPELINING", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["COMMAND PIPELINING"] += 1
    
                        elif re.search("^TIME LIMIT", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["COMMAND TIME LIMIT"] += 1
    
                        elif re.search("^COUNT LIMIT", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["COMMAND COUNT LIMIT"] += 1
    
                        elif re.search("^LENGTH LIMIT", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["COMMAND LENGTH LIMIT"] += 1
    
                    elif re.match("^WHITELISTED$", line_fields[LOG_CURSOR]):
                        ip_list[current_ip].actions["WHITELISTED"] += 1
    
                    elif re.match("^BLACKLISTED$", line_fields[LOG_CURSOR]):
                        ip_list[current_ip].actions["BLACKLISTED"] += 1

                    elif re.match("^BARE$", line_fields[LOG_CURSOR]):
                        if re.search("^NEWLINE", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["BARE NEWLINE"] += 1

                    elif re.match("^NON-SMTP$", line_fields[LOG_CURSOR]):
                        if re.search("^COMMAND", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["NON-SMTP COMMAND"] += 1

                    elif re.match("^WHITELIST$", line_fields[LOG_CURSOR]):
                        if re.search("^VETO", line_fields[LOG_CURSOR+1]):
                            ip_list[current_ip].actions["WHITELIST VETO"] += 1

# done with the log file
maillog.close


# additional reports shown in full mode only
if REPORT_MODE in ('full','ip'):
    for client in ip_list:
        print client
        for log in sorted(ip_list[client].logs):
            if log in ('FIRST SEEN','LAST SEEN'):
                print "\t",log,":",datetime.datetime.fromtimestamp\
                    (int(ip_list[client].logs[log])).strftime('%Y-%m-%d %H:%M:%S')
            else:
                print "\t",log,":",ip_list[client].logs[log]
        print "\t--- postscreen actions ---"
        for action in sorted(ip_list[client].actions):
            print "\t",action,":",ip_list[client].actions[action]
            if action in ('DNSBL'):
                print "\tDNSBL ranks:",ip_list[client].dnsbl_ranks
        if GEOLOC > 0:
            print "\tGeoLoc:",ip_list[client].geoloc
        print


# store the list of blocked clients for map generation
if MAPDEST not in "" and GEOLOC > 1:
    blocked_clients = defaultdict(int)

postscreen_stats = defaultdict(int)
clients = defaultdict(int)
comeback = {'<10s':0, '>10s to 30s':0, '>30s to 1min':0, '>1min to 5min':0,
            '>5 min to 30min':0, '>30min to 2h':0, '>2h to 5h':0,
            '>5h to 12h':0, '>12h to 24h':0, '>24h':0}
blocked_countries = defaultdict(int)


# normal report mode
if REPORT_MODE in ('short','full','none'):
     
    # basic accounting, browse through the list of objects and count
    # the occurences
    for client in ip_list:
        # go to the next client if this one doesn't match the action filter
        if not ip_list[client].action_filter(ACTION_FILTER):
            continue

        clients["clients"] += 1
        # calculate the average reconnection delay (graylist)
        if ip_list[client].logs["RECO. DELAY (graylist)"] > 0:
            clients["reconnections"] += 1
            clients["seconds avg. reco. delay"] += ip_list[client].logs["RECO. DELAY (graylist)"]
            if ip_list[client].logs["RECO. DELAY (graylist)"] < 10:
                comeback['<10s'] += 1;
            elif 10 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 30:
                comeback['>10s to 30s'] += 1;
            elif 30 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 60:
                comeback['>30s to 1min'] += 1;
            elif 60 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 300:
                comeback['>1min to 5min'] += 1;
            elif 300 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 1800:
                comeback['>5 min to 30min'] += 1;
            elif 1800 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 7200:
                comeback['>30min to 2h'] += 1;
            elif 7200 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 18000:
                comeback['>2h to 5h'] += 1;
            elif 18000 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 43200:
                comeback['>5h to 12h'] += 1;
            elif 43200 < ip_list[client].logs["RECO. DELAY (graylist)"] <= 86400:
                comeback['>12h to 24h'] += 1;
            else:
                comeback['>24h'] += 1;

        for action in sorted(ip_list[client].actions):
            postscreen_stats[action] += ip_list[client].actions[action]


        # calculate the average DNSBL trigger level
        if ip_list[client].actions["DNSBL"] > 0:
            for rank in ip_list[client].dnsbl_ranks:
                clients["avg. dnsbl rank"] += int(rank)

        # if client was blocked at any point, add its country to the count
        if ( GEOLOC > 0 and
            ip_list[client].geoloc > 0 and
            (ip_list[client].actions["BLACKLISTED"] > 0
            or ip_list[client].actions["DNSBL"] > 0
            or ip_list[client].actions["PREGREET"] > 0
            or ip_list[client].actions["COMMAND PIPELINING"] > 0
            or ip_list[client].actions["COMMAND TIME LIMIT"] > 0
            or ip_list[client].actions["COMMAND COUNT LIMIT"] > 0
            or ip_list[client].actions["COMMAND LENGTH LIMIT"] > 0
            or ip_list[client].actions["BARE NEWLINE"] > 0
            or ip_list[client].actions["NON-SMTP COMMAND"] > 0)):

            blocked_countries[ip_list[client].geoloc["country_name"]] += 1
            clients["blocked clients"] += 1
            if MAPDEST not in "" and GEOLOC > 1:
                blocked_clients[client] = 1

    # calculate the average reconnection delay
    if clients["reconnections"] > 0:
        clients["seconds avg. reco. delay"] /= clients["reconnections"]

    # calculate the average DNSBL trigger rank
    if (postscreen_stats["DNSBL"] > 0 and clients["avg. dnsbl rank"] > 0):
        clients["avg. dnsbl rank"] /= postscreen_stats["DNSBL"]

if REPORT_MODE in ('short','full'):
    # display unique clients and total postscreen actions
    print "\n=== unique clients/total postscreen actions ==="
    # print the count of CONNECT first (apply the ACTION_FILTER)
    print str(len([cs.logs['CONNECT'] for cs in ip_list.itervalues() \
        if (cs.logs['CONNECT'] > 0 and cs.action_filter(ACTION_FILTER))])) \
        + "/" + str(sum([cs.logs['CONNECT'] for cs in ip_list.itervalues() \
        if (cs.logs['CONNECT'] > 0 and cs.action_filter(ACTION_FILTER))])) \
        + " CONNECT"
    # then print the list of actions, ACTION_FILTER was applied earlied
    # when the postscreen_stats dictionary was built
    for action in sorted(postscreen_stats):
        print str(len([cs.actions[action] for cs in ip_list.itervalues() \
            if (cs.actions[action] > 0 and cs.action_filter(ACTION_FILTER))])) \
            + "/" + str(postscreen_stats[action]),action

    print "\n=== clients statistics ==="
    for stat in sorted(clients):
        print clients[stat],stat

    print "\n=== First reconnection delay (graylist) ==="
    print   "delay| <10s   |>10to30s| >30to1m| >1to5m | >5to30m|" + \
            ">30mto2h| >2hto5h|>5hto12h|>12to24h| >24h   |"
    # display the absolute values
    sys.stdout.write("count|")
    sys.stdout.write(str(comeback['<10s']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>10s to 30s']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>30s to 1min']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>1min to 5min']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>5 min to 30min']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>30min to 2h']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>2h to 5h']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>5h to 12h']).ljust(8) + "|")
    sys.stdout.write(str(comeback['>12h to 24h']).ljust(8) + "|")
    print str(comeback['>24h']).ljust(8) + "|"

    # calculate and display the percentages
    if clients["reconnections"]> 0:
        getcontext().prec = 2
        dec_cameback = Decimal(clients["reconnections"])
    
        sys.stdout.write("   % |")
        sys.stdout.write(str(Decimal(comeback['<10s'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>10s to 30s'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>30s to 1min'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>1min to 5min'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>5 min to 30min'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>30min to 2h'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>2h to 5h'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>5h to 12h'])\
                            /dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>12h to 24h'])\
                            /dec_cameback * 100).ljust(8) + "|")
        print str(Decimal(comeback['>24h'])\
                            /dec_cameback * 100).ljust(8) + "|"

    if GEOLOC > 0:
        total_blocked = Decimal(clients["blocked clients"])
        print "\n=== Top 20 Countries of Blocked Clients ==="
        from operator import itemgetter
        sorted_countries = blocked_countries.items()
        sorted_countries.sort(key = itemgetter(1), reverse=True)
        count_format = ""
        for i in range(20):
            if i < len(sorted_countries):
                country,clients = sorted_countries[i]
                if count_format in "":
                    count_format = "%" + str(len(str(clients))) + "d"
                client_percent = "(%5.2f%%)" % float(Decimal(clients)/total_blocked*100)
                print count_format % clients, client_percent, country

# generate the HTML for the google map and store it in a file
if MAPDEST not in "" and GEOLOC > 1:
    fd = open(MAPDEST,"w")
    mapcode = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <title>Postscreen GeoMap of Blocked IPs</title>
        <script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>
        <script type="text/javascript">
            window.onload = function() {
                var center = new google.maps.LatLng(0,0);
                var mapOptions = {
                    zoom: 2,
                    center: center,
                    mapTypeId: google.maps.MapTypeId.TERRAIN
                };
                var myMap = new google.maps.Map(
                    document.getElementById('map'),mapOptions
                    );
'''
    fd.write(mapcode)

    incr = 0
    for client in blocked_clients:
        if  type(ip_list[client].geoloc) is not NoneType \
            and ip_list[client].geoloc.has_key('latitude') \
            and ip_list[client].geoloc.has_key('longitude') \
	        and (ip_list[client].logs['CONNECT'] >= MAP_MIN_CONN):

            mapcode = '''
                ip[''' + str(incr) + '''] = new google.maps.LatLng(''' \
                    + str(ip_list[client].geoloc['latitude']) + "," \
                    + str(ip_list[client].geoloc['longitude']) + ''');
                var marker_ip'''+str(incr)+''' = new google.maps.Marker({
                        position: ip''' + str(incr) + ''',
                        map: myMap,
                        title: "''' + str(client) + '''"
                        });
                var desc_ip''' + str(incr) + ''' = '<div id="content">' +
                    '<div id="siteNotice"></div><h2 id="firstHeading" class="firstHeading">' +
                    ' ''' + str(client) + '''</h2><div id="bodyContent">' +
                    ' '''
            fd.write(mapcode)

            for log in sorted(ip_list[client].logs):
                if log in ('FIRST SEEN','LAST SEEN'):
                    mapcode = '<p>' + log + ": " + str(datetime.datetime.fromtimestamp\
                        (int(ip_list[client].logs[log])).strftime('%Y-%m-%d %H:%M:%S'))\
                        + '''</p>' +
                    ' '''
		    fd.write(mapcode)
                else:
                    mapcode = '<p>' + log + ": " + str(ip_list[client].logs[log]) + '''</p>' +
                    ' '''
		    fd.write(mapcode)

            for action in sorted(ip_list[client].actions):
                if ip_list[client].actions[action] > 0:
                    mapcode = '<p>' + action + ": " + str(ip_list[client].actions[action]) + '''</p>' +
                    ' '''
		    fd.write(mapcode)
                    if action in ('DNSBL'):
                        mapcode = '<p>' + "DNSBL ranks: "
			fd.write(mapcode)
                        for rank in ip_list[client].dnsbl_ranks: 
                            mapcode = " " + str(rank) + ","
			    fd.write(mapcode)
                        mapcode = '''</p>' +
                    ' '''
		    fd.write(mapcode)

            if ip_list[client].geoloc.has_key('city'):
                mapcode = '<p>' + 'Location: ' + \
                    re.escape(str(ip_list[client].geoloc['city'])) + ", " + \
                    re.escape(str(ip_list[client].geoloc['country_code'])) +  '''<p> ' +
                    ' '''
		fd.write(mapcode)
                    
            mapcode = '''</div></div>';
                info_window[''' + str(incr) + '''] = new google.maps.InfoWindow({
                    content: desc_ip[''' + str(incr) + '''],
                    maxWidth: 500
                });
                google.maps.event.addListener(marker_ip'''+str(incr)+''', 'click', function() {
                    infowindow'''+str(incr)+'''.open(myMap,marker_ip'''+str(incr)+''');
                });
'''
            incr += 1
	    fd.write(mapcode)

    mapcode = '''
            }
        </script>
        <style type="text/css">
            #map {
                width:100%;
                height:800px;
            }
        </style>
        
    </head>
    <body>
        <h1>Postscreen Map of Blocked IPs</h1>
        <div id="map">
        </div>
        <p>mapping ''' + str(incr) + ''' blocked IPs</p>
        <p>generated using <a href="https://github.com/jvehent/Postscreen-Stats">Postscreen-Stats</a> by <a href="http://1nw.eu/!j">Julien Vehent</a></p>
    </body>
</html>
'''
    fd.write(mapcode)
    fd.close()
    print "Creating HTML map at",MAPDEST
