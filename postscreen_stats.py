#!/usr/bin/env python

# Parses the postscreen logs and display stats
# jvehent - 20111103

import re
import time
import calendar
import datetime
import getopt
import sys
from decimal import *

def usage():
    print
    print   "   postscreen_stats.py"
    print   "   parses postfix logs to compute statistics on postscreen activity"
    print
    print   "usage: postscreen_stats.py <-y|--year> <-r|--report|-f|--full>"
    print   "   <-f|--file>     log file to parse (default to /var/log/maillog)"
    print   "   <-i|--ip>       filters the results on a specific IP"
    print   "   <-r|--report>   report mode {short|full} (default to short)"
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
        self.count_connect = 0          # how many times we saw this client
        self.timestamp_first_seen = 0   # unix timestamp
        self.timestamp_last_seen = 0    # unix timestamp
        self.count_passold = 0
        self.count_passnew = 0
        self.count_noqueue_maxconn = 0
        self.count_noqueue_ports_busy = 0
        self.count_noqueue_450 = 0      # connection rejected for graylist
        self.count_hangup = 0
        self.count_dnsbl = 0            # how many times did this IP get blocked by DNSBL
        self.dnsbl_ranks = []           # list of ranks triggered when blocked
        self.count_pregreet = 0
        self.count_pipelining = 0
        self.count_command_time_limit = 0
        self.count_command_count_limit = 0
        self.count_command_length_limit = 0
        self.count_whitelisted = 0
        self.count_blacklisted = 0
        self.reconnection_delay = 0


# VARIABLES
IP_REGEXP = "((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}" \
            "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))"
IP_FILTER = "."
NOW = datetime.datetime.now()
YEAR = NOW.year
REPORT_MODE = "short"
LOGFILE = "/var/log/maillog"
# the list of clients ips and pointer to instance of class
ip_list = {}


# command line arguments
args_list, remainder = getopt.getopt(sys.argv[1:],
    'i:f:y:r:h', ['ip=','year=','report=','help', 'file='])

for argument, value in args_list:
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
    
                    ip_list[current_ip].timestamp_first_seen = \
                                    gen_unix_ts(syslog_date)
    
                    ip_list[current_ip].timestamp_last_seen = \
                                    ip_list[current_ip].timestamp_first_seen
                # ip is already known, update the last_seen timestamp
                else:
                    ip_list[current_ip].timestamp_last_seen = \
                                    gen_unix_ts(syslog_date)
                    
                ip_list[current_ip].count_connect += 1
    
    
            # client must be initialized to continue
            # the string matching is organized to test the most probable
            # value first, to speed things up
            elif current_ip in ip_list:
                    if re.match("^PASS$", line_fields[5]):
                        if re.search("^OLD", line_fields[6]):
                            ip_list[current_ip].count_passold += 1
    
                            # if the connection count is 2, and the IP has already
                            # been rejected with a code 450 calculate the
                            # reconnection delay
                            if (ip_list[current_ip].count_connect == 2 
                                and ip_list[current_ip].count_noqueue_450 > 0):
                                ip_list[current_ip].reconnection_delay = \
                                    ip_list[current_ip].timestamp_last_seen \
                                    - ip_list[current_ip].timestamp_first_seen 

                        elif re.search("^NEW", line_fields[6]):
                            ip_list[current_ip].count_passnew += 1 
    
                    elif re.match("^NOQUEUE:$", line_fields[5]):
                        if re.search("too many connections", line_fields[6]):
                            ip_list[current_ip].count_noqueue_maxconn += 1
                        elif re.search("all server ports busy", line_fields[6]):
                            ip_list[current_ip].count_noqueue_ports_busy += 1
                        elif re.search("450 4.3.2 Service currently unavailable",line_fields[6]):
                            ip_list[current_ip].count_noqueue_450 += 1
 
                    elif re.match("^HANGUP$", line_fields[5]):
                        ip_list[current_ip].count_hangup += 1
    
                    elif re.match("^DNSBL$", line_fields[5]):
                        ip_list[current_ip].count_dnsbl += 1
                        # store the rank
                        rank_line = line_fields[6].split(None)
                        ip_list[current_ip].dnsbl_ranks.append(rank_line[1])
    
                    elif re.match("^PREGREET$", line_fields[5]):
                        ip_list[current_ip].count_pregreet += 1
    
                    elif re.match("^COMMAND$", line_fields[5]):
                        if re.search("^PIPELINING", line_fields[6]):
                            ip_list[current_ip].count_pipelining += 1
    
                        elif re.search("^TIME LIMIT", line_fields[6]):
                            ip_list[current_ip].count_command_time_limit += 1
    
                        elif re.search("^COUNT LIMIT", line_fields[6]):
                            ip_list[current_ip].count_command_count_limit += 1
    
                        elif re.search("^LENGTH LIMIT", line_fields[6]):
                            ip_list[current_ip].count_command_length_limit += 1
    
                    elif re.match("^WHITELISTED$", line_fields[5]):
                        ip_list[current_ip].count_whitelisted += 1
    
                    elif re.match("^BLACKLISTED$", line_fields[5]):
                        ip_list[current_ip].count_blacklisted += 1

maillog.close


# additional reports shown in full mode only
if REPORT_MODE in ('full'):

    for client in ip_list:
        print   client
        print   "\tconnections count:", ip_list[client].count_connect
        print   "\tfirst seen on",
        print   datetime.datetime.fromtimestamp(int(ip_list[client].\
                timestamp_first_seen)).strftime('%Y-%m-%d %H:%M:%S')

        if ip_list[client].count_connect > 1: 
            print   "\tlast seen on",
            print   datetime.datetime.fromtimestamp(int(ip_list[client].\
                    timestamp_last_seen)).strftime('%Y-%m-%d %H:%M:%S')
            print   "\treconnection delay (graylist):",
            print   ip_list[client].reconnection_delay,"seconds"

        if ip_list[client].count_passnew > 0:
            print   "\tPASS NEW count:",ip_list[client].count_passnew
        if ip_list[client].count_passold > 0:
            print   "\tPASS OLD count:",ip_list[client].count_passold
        if ip_list[client].count_whitelisted > 0:
            print   "\tWHITELISTED count:",ip_list[client].count_whitelisted
        if ip_list[client].count_blacklisted > 0:
            print   "\tBLACKLISTED count:",ip_list[client].count_blacklisted
        if ip_list[client].count_dnsbl > 0:
            print   "\tDNSBL count:",ip_list[client].count_dnsbl
        if ip_list[client].count_dnsbl > 0:
            print   "\tDNSBL ranks:",ip_list[client].dnsbl_ranks
        if ip_list[client].count_pregreet > 0:
            print   "\tPREGREET count:",ip_list[client].count_pregreet
        if ip_list[client].count_noqueue_maxconn > 0:
            print   "\tNOQUEUE maxcon count:",ip_list[client].count_noqueue_maxconn
        if ip_list[client].count_noqueue_ports_busy > 0:
            print   "\tNOQUEUE port busy count:",ip_list[client].count_noqueue_ports_busy
        if ip_list[client].count_noqueue_450 > 0:
            print   "\tNOQUEUE REJECT 450 (graylist):",ip_list[client].count_noqueue_450
        if ip_list[client].count_hangup > 0:
            print   "\tHANGUP count:",ip_list[client].count_hangup
        if ip_list[client].count_pipelining > 0:
            print   "\tCOMMAND PIPELINING count:",ip_list[client].count_pipelining
        if ip_list[client].count_command_time_limit > 0:
            print   "\tCOMMAND TIME LIMIT count:",ip_list[client].count_command_time_limit
        if ip_list[client].count_command_count_limit > 0:
            print   "\tCOMMAND COUNT LIMIT count:",ip_list[client].count_command_count_limit
        if ip_list[client].count_command_length_limit > 0:
            print   "\tCOMMAND LENGTH LIMIT count:",ip_list[client].count_command_length_limit

# normal report mode
if REPORT_MODE in ('short','full'):
    postscreen = {}
    postscreen["CONNECT"] = 0
    postscreen["PASS NEW"] = 0
    postscreen["PASS OLD"] = 0
    postscreen["WHITELISTED"] = 0
    postscreen["BLACKLISTED"] = 0
    postscreen["DNSBL"] = 0
    postscreen["PREGREET"] = 0
    postscreen["NOQUEUE MAXCONN"] = 0
    postscreen["NOQUEUE PORT BUSY"] = 0
    postscreen["NOQUEUE REJECT 450 (graylist)"] = 0
    postscreen["HANGUP"] = 0
    postscreen["COMMAND PIPELINING"] = 0
    postscreen["COMMAND TIME LIMIT"] = 0
    postscreen["COMMAND COUNT LIMIT"] = 0
    postscreen["COMMAND LENGTH LIMIT"] = 0
    clients = {}
    clients["seconds avg. reco. delay"] = 0
    clients["clients"] = 0
    clients["came back count"] = 0
    clients["avg. dnsbl rank"] = 0
    comeback = {'<10s':0, '>10s to 30s':0, '>30s to 1min':0, '>1min to 5min':0,
                '>5 min to 30min':0, '>30min to 2h':0, '>2h to 5h':0,
                '>5h to 12h':0, '>12h to 24h':0, '>24h':0}
    
    # basic accounting, browse through the list of objects and count
    # the occurences
    for client in ip_list:
        clients["clients"] += 1
        if ip_list[client].reconnection_delay > 0:
            clients["came back count"] += 1
            clients["seconds avg. reco. delay"] += ip_list[client].reconnection_delay
            if ip_list[client].reconnection_delay < 10:
                comeback['<10s'] += 1;
            elif 10 < ip_list[client].reconnection_delay <= 30:
                comeback['>10s to 30s'] += 1;
            elif 30 < ip_list[client].reconnection_delay <= 60:
                comeback['>30s to 1min'] += 1;
            elif 60 < ip_list[client].reconnection_delay <= 300:
                comeback['>1min to 5min'] += 1;
            elif 300 < ip_list[client].reconnection_delay <= 1800:
                comeback['>5 min to 30min'] += 1;
            elif 1800 < ip_list[client].reconnection_delay <= 7200:
                comeback['>30min to 2h'] += 1;
            elif 7200 < ip_list[client].reconnection_delay <= 18000:
                comeback['>2h to 5h'] += 1;
            elif 18000 < ip_list[client].reconnection_delay <= 43200:
                comeback['>5h to 12h'] += 1;
            elif 43200 < ip_list[client].reconnection_delay <= 86400:
                comeback['>12h to 24h'] += 1;
            else:
                comeback['>24h'] += 1;

        postscreen["CONNECT"] += ip_list[client].count_connect
        postscreen["PASS NEW"] += ip_list[client].count_passnew
        postscreen["PASS OLD"] += ip_list[client].count_passold
        postscreen["WHITELISTED"] += ip_list[client].count_whitelisted
        postscreen["BLACKLISTED"] += ip_list[client].count_blacklisted
        postscreen["DNSBL"] += ip_list[client].count_dnsbl
        if ip_list[client].count_dnsbl > 0:
            for rank in ip_list[client].dnsbl_ranks:
                clients["avg. dnsbl rank"] += int(rank)
        postscreen["PREGREET"] += ip_list[client].count_pregreet
        postscreen["NOQUEUE MAXCONN"] += ip_list[client].count_noqueue_maxconn
        postscreen["NOQUEUE PORT BUSY"] += ip_list[client].count_noqueue_ports_busy
        postscreen["NOQUEUE REJECT 450 (graylist)"] += ip_list[client].count_noqueue_450
        postscreen["HANGUP"] += ip_list[client].count_hangup
        postscreen["COMMAND PIPELINING"] += ip_list[client].count_pipelining
        postscreen["COMMAND TIME LIMIT"] += ip_list[client].count_command_time_limit
        postscreen["COMMAND COUNT LIMIT"] += ip_list[client].count_command_count_limit
        postscreen["COMMAND LENGTH LIMIT"] += ip_list[client].count_command_length_limit

    if clients["came back count"] > 0:
        clients["seconds avg. reco. delay"] /= clients["came back count"]

    if (postscreen["DNSBL"] > 0 and clients["avg. dnsbl rank"] > 0):
        clients["avg. dnsbl rank"] /= postscreen["DNSBL"]

    # display
    print "=== Postscreen statistics ==="
    for stat in sorted(postscreen):
        print postscreen[stat],stat

    print "=== Clients statistics ==="
    for stat in sorted(clients):
        print clients[stat],stat

    print "=== First reconnection delay (graylist) ==="
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
    if clients["came back count"] > 0:
        getcontext().prec = 2
        dec_cameback = Decimal(clients["came back count"])
    
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

