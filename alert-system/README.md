# K8sCop Alert System

_K8sCop fetches ElasticSearch k8s logs, parses the logs to detect specific patterns, and pushes new alerts back to ElasticSearch._

```
$ ./app.py -h
usage: app.py [-h] --elastic ip:port --page-index logs --alerts-index
              alerts --start 2019-2-14-12-30-0 --max-alert-delta 600
              --analysis {static,streaming} [--end 2019-2-14-18-30-0]
              [--fetch-delay {5,10,12}]
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
$ ./app.py -E 192.168.43.139:9200 -I logstash-2019.02.12 -i alerts -s 2019-2-12-19-30-0 
           -D 600 --analysis static -e 2019-2-12-19-45-0
[*] Starting K8sCop in static mode
[+] Connected to ElasticSearch
[*] Initialising fetcher, parser, pusher components
[+] Components initialised
[*] Launching threads
[*] Log data between 2019-02-12 19:30:00 and 2019-02-12 19:45:00
[+] Fetcher is done
[+] Parser is done
[++] [Command execution by kubernetes-admin on kube-apiserver] TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+=] Updated alert TPet52gBWERuYKu0jv0l
[+] Pusher is done
[+] K8sCop is done
```

## Streaming Analysis

```
$ ./app.py -E 192.168.43.139:9200 -I logstash-2019.02.12 -i alerts -s 2019-2-12-19-30-0 
           -D 600 --analysis streaming                  
[*] Starting K8sCop in streaming mode
[+] Connected to ElasticSearch
[*] Initialising fetcher, parser, pusher components
[+] Components initialised
[*] Launching threads
[*] Log data between 2019-02-12 19:30:00 and 2019-02-13 16:40:21.854368
[+] Amount of data fetched: 487
[++] [Command execution by kubernetes-admin on kube-apiserver] L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[*] Log data between 2019-02-13 16:40:21.854368 and 2019-02-13 16:40:31.854368
[+] Amount of data fetched: 0
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[*] Log data between 2019-02-13 16:40:31.854368 and 2019-02-13 16:40:41.854368
[+] Amount of data fetched: 0
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[+=] Updated alert L_eu52gBWERuYKu0mf4_
[*] Log data between 2019-02-13 16:40:41.854368 and 2019-02-13 16:40:51.854368
[+] Amount of data fetched: 0
^C[!] K8sCop force quit
```

## Important

Time must be given in UTC format. 