#!/usr/bin/env python

# Parses the postscreen logs and display stats
# jvehent - 20111103

import re
import time
import calendar
import datetime
import getopt
import sys
import urllib
from collections import defaultdict
from decimal import *

def usage():
    print
    print   "   postscreen_stats.py"
    print   "   parses postfix logs to compute statistics on postscreen activity"
    print
    print   "usage: postscreen_stats.py <-y|--year> <-r|--report|-f|--full>"
    print   "   <-f|--file>     log file to parse (default to /var/log/maillog)"
    print   "   <-g|--geoloc>   /!\ slow ! ip geoloc against hostip.info (default disabled)"
    print   "   <-i|--ip>       filters the results on a specific IP"
    print   "   <-r|--report>   report mode {short|full|ip} (default to short)"
    print   "   <-y|--year>     select the year of the logs (default to current year)"
    print


# convert the syslog time stamp in unix format and store it
def gen_unix_ts(syslog_date):
    ts = 0
    unix_ts = 0
    # add the year
    syslog_date = str(YEAR) + " " + syslog_date
    ts = time.strptime(syslog_date, '%Y %b %d %H:%M:%S')
    unix_ts = calendar.timegm(ts)

    # check if the unix_ts is not in the future
    if unix_ts > time.mktime(NOW.timetuple()):
        print   "Time is in the future... what the heck ?"
        print   "Are you really parsing logs from " + YEAR + " ?"
    else:
        return unix_ts

# each client's statistics are stored in the class below
class ClientStat:
    def __init__(self):
        self.logs = defaultdict(int)    # store the logs in a dictionary
        self.dnsbl_ranks = []           # list of ranks triggered when blocked

# VARIABLES
IP_REGEXP = "((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}" \
            "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))"
IP_FILTER = "."
NOW = datetime.datetime.now()
YEAR = NOW.year
REPORT_MODE = "short"
LOGFILE = "/var/log/maillog"
GEOLOC = 0
# the list of clients ips and pointer to instance of class
ip_list = {}


# command line arguments
args_list, remainder = getopt.getopt(sys.argv[1:],
    'gi:f:y:r:h', ['geoloc','ip=','year=','report=','help', 'file='])

for argument, value in args_list:
    if argument in ('-g', '--geoloc'):
        GEOLOC = 1
    if argument in ('-f', '--file'):
        LOG_FILE = value
    if argument in ('-y', '--year'):
        YEAR = value
    if argument in ('-i', '--ip'):
        IP_FILTER = value
        print "Filtering results to match:",IP_FILTER
    if argument in ('-r', '--report'):
        if value in ('short'):
            REPORT_MODE = "short"
        elif value in ('full'):
            REPORT_MODE = "full"
        elif value in ('ip'):
            REPORT_MODE = "ip"
        else:
            print "unknown report type"
            usage()
            sys.exit()
    if argument in ('-h', '--help'):
        usage()
        sys.exit()

maillog = open(LOG_FILE)

for line in maillog:
    # Get postscreen logs only
    if "postfix/postscreen" in line:
        # apply the user defilter filter
        if re.search(IP_FILTER,line):
            # parse the log line
            line_fields = line.split(None, 6)
            
            # parse the ip
            current_ip = '999.999.999.999'
            if re.search(IP_REGEXP, line_fields[6]):
                tmp = re.split(IP_REGEXP, line_fields[6], maxsplit=1)
                current_ip = tmp[1]
                del tmp
    
            if re.match("^CONNECT$", line_fields[5]):
                syslog_date =   line_fields[0] + " " + line_fields[1] + \
                                " " + line_fields[2]
    
                # first time we see the client, initiate a class instance
                # store in in the client_list dictionary
                if current_ip not in ip_list:
                    ip_list[current_ip] = ClientStat()
                    ip_list[current_ip].logs["FIRST SEEN"] = \
                        gen_unix_ts(syslog_date) 
                    ip_list[current_ip].logs["LAST SEEN"] = \
                        gen_unix_ts(syslog_date) 
                    if GEOLOC == 1:
                        # geo localise ip
                        geoloc_url = "http://api.hostip.info/country.php?ip=" \
                            + current_ip
                        ip_list[current_ip].logs["COUNTRY"] = \
                            urllib.urlopen(geoloc_url).read()

                # ip is already known, update the last_seen timestamp
                else:
                    ip_list[current_ip].logs["LAST SEEN"] = \
                        gen_unix_ts(syslog_date) 
                    
                ip_list[current_ip].logs["CONNECT"] += 1
    
            # client must be initialized to continue
            # the string matching is organized to test the most probable
            # value first, to speed things up
            elif current_ip in ip_list:
                    if re.match("^PASS$", line_fields[5]):
                        if re.search("^OLD", line_fields[6]):
                            ip_list[current_ip].logs["PASS OLD"] += 1
    
                            # if the connection count is 2, and the IP has already
                            # been rejected with a code 450 calculate the
                            # reconnection delay
                            if (ip_list[current_ip].logs["CONNECT"] == 2 
                                and ip_list[current_ip].logs["NOQUEUE 450"] > 0):
                                ip_list[current_ip].logs["RECO. DELAY (graylist)"] = \
                                    ip_list[current_ip].logs["LAST SEEN"] \
                                    - ip_list[current_ip].logs["FIRST SEEN"]

                        elif re.search("^NEW", line_fields[6]):
                            ip_list[current_ip].logs["PASS NEW"] += 1 
    
                    elif re.match("^NOQUEUE:$", line_fields[5]):
                        if re.search("too many connections", line_fields[6]):
                            ip_list[current_ip].logs["NOQUEUE too many connections"] += 1
                        elif re.search("all server ports busy", line_fields[6]):
                            ip_list[current_ip].logs["NOQUEUE all server ports busy"] += 1
                        elif re.search("450 4.3.2 Service currently unavailable",line_fields[6]):
                            ip_list[current_ip].logs["NOQUEUE 450 deep protocol test reconnection"] += 1
 
                    elif re.match("^HANGUP$", line_fields[5]):
                        ip_list[current_ip].logs["HANGUP"] += 1
    
                    elif re.match("^DNSBL$", line_fields[5]):
                        ip_list[current_ip].logs["DNSBL"] += 1
                        # store the rank
                        rank_line = line_fields[6].split(None)
                        ip_list[current_ip].dnsbl_ranks.append(rank_line[1])
    
                    elif re.match("^PREGREET$", line_fields[5]):
                        ip_list[current_ip].logs["PREGREET"] += 1
    
                    elif re.match("^COMMAND$", line_fields[5]):
                        if re.search("^PIPELINING", line_fields[6]):
                            ip_list[current_ip].logs["COMMAND PIPELINING"] += 1
    
                        elif re.search("^TIME LIMIT", line_fields[6]):
                            ip_list[current_ip].logs["COMMAND TIME LIMIT"] += 1
    
                        elif re.search("^COUNT LIMIT", line_fields[6]):
                            ip_list[current_ip].logs["COMMAND COUNT LIMIT"] += 1
    
                        elif re.search("^LENGTH LIMIT", line_fields[6]):
                            ip_list[current_ip].logs["COMMAND LENGTH LIMIT"] += 1
    
                    elif re.match("^WHITELISTED$", line_fields[5]):
                        ip_list[current_ip].logs["WHITELISTED"] += 1
    
                    elif re.match("^BLACKLISTED$", line_fields[5]):
                        ip_list[current_ip].logs["BLACKLISTED"] += 1

                    elif re.match("^BARE$", line_fields[5]):
                        if re.search("^NEWLINE", line_fields[6]):
                            ip_list[current_ip].logs["BARE NEWLINE"] += 1

                    elif re.match("^WHITELIST$", line_fields[5]):
                        if re.search("^VETO", line_fields[6]):
                            ip_list[current_ip].logs["WHITELIST VETO"] += 1

# done with the log file
maillog.close


# additional reports shown in full mode only
if REPORT_MODE in ('full','ip'):

    for client in ip_list:
        print   client
        for action in sorted(ip_list[client].logs):
            if action in ('FIRST SEEN','LAST SEEN'):
                print "\t",action,":",datetime.datetime.fromtimestamp\
                    (int(ip_list[client].logs[action])).strftime('%Y-%m-%d %H:%M:%S')
            else:
                print "\t",action,":",ip_list[client].logs[action]
            if action in ('DNSBL'):
                print "\tDNSBL ranks:",ip_list[client].dnsbl_ranks

# normal report mode
if REPORT_MODE in ('short','full'):
    postscreen_stats = defaultdict(int)
    clients = defaultdict(int)
    comeback = {'<10s':0, '>10s to 30s':0, '>30s to 1min':0, '>1min to 5min':0,
                '>5 min to 30min':0, '>30min to 2h':0, '>2h to 5h':0,
                '>5h to 12h':0, '>12h to 24h':0, '>24h':0}
    blocked_countries = defaultdict(int)
     
    # basic accounting, browse through the list of objects and count
    # the occurences
    for client in ip_list:
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

        for action in sorted(ip_list[client].logs):
            if action not in ('FIRST SEEN','LAST SEEN', 'RECO. DELAY (graylist)', 'COUNTRY'):
                postscreen_stats[action] += ip_list[client].logs[action]

        # calculate the average DNSBL trigger level
        if ip_list[client].logs["DNSBL"] > 0:
            for rank in ip_list[client].dnsbl_ranks:
                clients["avg. dnsbl rank"] += int(rank)

        # if client was blocked at any point, add its country to the count
        if ( GEOLOC == 1 and
            (ip_list[client].logs["BLACKLISTED"] > 0
            or ip_list[client].logs["DNSBL"] > 0
            or ip_list[client].logs["PREGREET"] > 0
            or ip_list[client].logs["COMMAND PIPELINING"] > 0
            or ip_list[client].logs["COMMAND TIME LIMIT"] > 0
            or ip_list[client].logs["COMMAND COUNT LIMIT"] > 0
            or ip_list[client].logs["COMMAND LENGTH LIMIT"] > 0)):
            blocked_countries[ip_list[client].logs["COUNTRY"]] += 1

    if clients["reconnections"] > 0:
        clients["seconds avg. reco. delay"] /= clients["reconnections"]

    if (postscreen_stats["DNSBL"] > 0 and clients["avg. dnsbl rank"] > 0):
        clients["avg. dnsbl rank"] /= postscreen_stats["DNSBL"]

    # display
    print "\n=== Postscreen statistics ==="
    for stat in sorted(postscreen_stats):
        print postscreen_stats[stat],stat

    print "\n=== Clients statistics ==="
    for stat in sorted(clients):
        print clients[stat],stat

    print "\n=== First reconnection delay (graylist) ==="
    print "delay| <10s   |>10to30s| >30to1m| >1to5m | >5to30m|>30mto2h| >2hto5h|>5hto12h|>12to24h| >24h   |";
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
        sys.stdout.write(str(Decimal(comeback['<10s'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>10s to 30s'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>30s to 1min'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>1min to 5min'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>5 min to 30min'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>30min to 2h'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>2h to 5h'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>5h to 12h'])/dec_cameback * 100).ljust(8) + "|")
        sys.stdout.write(str(Decimal(comeback['>12h to 24h'])/dec_cameback * 100).ljust(8) + "|")
        print str(Decimal(comeback['>24h'])/dec_cameback * 100).ljust(8) + "|"

    if GEOLOC == 1:
        print "\n=== Blocked IPs per country ==="
        from operator import itemgetter
        sorted_countries = blocked_countries.items()
        sorted_countries.sort(key = itemgetter(1), reverse=True)
        print sorted_countries
