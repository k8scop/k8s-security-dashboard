# K8sCop Alert System

_K8sCop fetches ElasticSearch k8s logs, parses the logs to detect specific patterns, and pushes new alerts back to ElasticSearch._

```
$ ./app.py -h
usage: app.py [-h] --elastic ip:port --page-index logs --alerts-index
              alerts --start 2019-2-14-12-30-0 --max-alert-delta 600
              --analysis {static,streaming} [--end 2019-2-14-18-30-0]
              [--fetch-delay {8,9,10,11,12}]
```

- `-E`: the `ip:port` of the ElasticSearch instance
- `-I`: the index of the logs page
- `-i`: the index of the alerts page
- `-s`: the desired start date and time of the analysis
- `-D`: the maximum delta for alert aggregation in seconds
- `-A`: set the analysis to static or streaming

If the analyis is static, the end date and time of the analysis must be set:

- `-e`: the end date and time of the **static** analysis [optional]

If the analysis is streaming, a delay between log fetches must be set:

- `-d`: the delay between log fetches in seconds for **streaming** analysis [optional]

## Flow Diagram

![](flow.png)

The Fetcher fetches data from ElasticSearch every `d` seconds and puts each entry into the Fetch Queue. 
The Parser gets data from the Fetch Queue, parses each entry and does some magic pattern recognition. 
If a pattern is matched, the entry is put in the Push Queue.
The Pusher gets entries from the Push Queue and pushes the corresponding alert(s) back to ElasticSearch every second.
The Pusher also takes care of alert aggregation: if the same alert has been seen in the last `D` seconds, the two alerts are aggregated. 

## Static Analysis

```
$ ./app.py -E 192.168.3.139:9200 -I filebeat-6.5.4-2019.02.12 -i alerts -s 2019-2-12-12-0-0 -D 600 --analysis static -e 2019-2-12-14-0-0
[*] Starting static K8sCop
[+] Connected to ElasticSearch
[*] Initialising fetcher, parser, pusher components
[+] Components initialised
[*] Fetching initial log bulk
[*] Log data between 2019-02-12 12:00:00 and 2019-02-12 14:00:00
[+] Amount of data fetched: 2541
[+] Log bulk fetched
[*] Parsing log bulk and searching for incidents
[+] Initial log bulk parsed
[*] Pushing alerts
...
[+] Pushed 9 alerts
[+] K8sCop static analysis done
```

## Streaming Analysis

```
$ ./app.py -E 192.168.3.139:9200 -I filebeat-6.5.4-2019.02.12 -i alerts -s 2019-2-12-12-0-0 -D 600 --analysis streaming
[*] Starting streaming K8sCop
[+] Connected to ElasticSearch
[*] Initialising fetcher, parser, pusher components
[+] Components initialised
[*] Fetching initial log bulk
[*] Log data between 2019-02-12 12:00:00 and 2019-02-12 14:17:40.232825
[+] Amount of data fetched: 2723
[+] Log bulk fetched
[*] Parsing log bulk and searching for incidents
[+] Initial log bulk parsed
[*] Pushing alerts
...
[+] Pushed 18 alerts
[*] Making threads
[+] Threads launched
[*] Log data between 2019-02-12 14:17:40.232825 and 2019-02-12 14:17:50.232825
[+] Amount of data fetched: 33
[*] Log data between 2019-02-12 14:17:50.232825 and 2019-02-12 14:18:00.232825
[+] Amount of data fetched: 23
[*] Log data between 2019-02-12 14:18:00.232825 and 2019-02-12 14:18:10.232825
[+] Amount of data fetched: 2
[*] Log data between 2019-02-12 14:18:10.232825 and 2019-02-12 14:18:20.232825
[+] Amount of data fetched: 10
...
```

## Important

Time must be given in UTC format. 