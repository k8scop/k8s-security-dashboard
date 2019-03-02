# K8sCop

_K8sCop fetches ElasticSearch k8s logs, parses the logs to detect and label interesting events, and pushes alerts back to ElasticSearch._

## Introduction

K8sCop is designed to make the analysis of Kubernetes audit logs easier.
The system classifies logs into labelled events using regular expressions and provides more clarity about Kubernetes events. 
K8sCop can perform a static analysis on a specific date range or streaming analysis in (almost) real time. It makes use of the Python Elasticsearch client and is multi-threaded for extra speed.

## Usage

```
$ ./app.py -h
usage: app.py [-h] --elastic ES --pages PAGES --alerts ALERTS --start START
              --analysis {static,streaming} [--end END]
              [--fetch-delay {3,5,8,10,12}]
```

- `-E`: the `ip:port` of the ElasticSearch instance
- `-I`: the index of the logs page
- `-i`: the index of the alerts page
- `-s`: the desired start date and time of the analysis
- `-A`: set the analysis to static or streaming

If the analysis is static, the end date and time of the analysis must be set:

- `-e`: the end date and time of the **static** analysis [optional]

If the end date and time is not given, the end date and time is automatically set to _utcnow_. 

If the analysis is streaming, a delay between log fetches must be set, because of potential Elasticsearch latency:

- `-d`: the delay between log fetches in seconds for **streaming** analysis [optional]

## Elasticsearch Indices

In our current logging architecture, logs get stored into Elasticsearch under an index with prefix _logstash_ and the date of the log prepended, like `logstash-2019.03.02`. 
K8sCop receives the prefix of the logs page as parameter and does the appending of the date on its own. 

For storing the alert, K8sCop receives the desired prefix for the alerts page and does the appending of the date by looking at the timestamp of the alert. 

## Flow Diagram

![](images/k8scop.png)

The Fetcher fetches data from ElasticSearch every `d` seconds and puts each entry into the Fetch Queue. 
The Parser gets data from the Fetch Queue, parses each entry and does regex pattern matching. 
If a pattern is matched, an alert specifc to the pattern is put in the Push Queue.
The Pusher gets alerts from the Push Queue and pushes them back to ElasticSearch every second.

In this implementation of K8sCop, there are multiple push queues and associated pushers running on separate threads for the different types of alerts. 


## Example How-to-Run

### Static Analysis

```
$ ./app.py -E 172.16.137.133:9200 -I logstash -i alerts -s 2019-2-1-0-0-0 
           -e 2019-3-2-0-0-0 --analysis static
```

### Streaming Analysis

```
$ ./app.py -E 172.16.137.133:9200 -I logstash -i alerts -s 2019-2-1-0-0-0 
           --analysis streaming   
```

### Important

Time must be given in UTC format. 

## Mapping RequestURI to Kubectl command

Part of this mapping is used for regex detection in the logs. 

|API|kubectl|comment|
|---|-------|-------|
|/api/v1/pods|get pods --all-namespaces||
|/api/v1/namespaces/kube-system/pods|get pods --namespace kube-system||
|/api/v1/namespaces/default/pods/busybox-test|describe busybox-test --namespace default||
|/api/v1/namespaces/default/pods/unsafe-space|describe pods unsafe-space --namespace default||
|/api/v1/pods?includeUninitialized=true|describe pods --all-namespaces||
|/api/v1/namespaces/default/secrets?includeUninitialized=true| Followed by multiple token queries|
|/api/v1/namespaces/default/secrets/exec-token-qjp9l|get secret details||
|/api/v1/namespaces/default/pods|create -f <pod>| Method create|
|/api/v1/services?limit=500|get svc --all-namespaces||
|/apis/extensions/v1beta1/daemonsets |get ds --all-namespaces||
|/apis/extensions/v1beta1/namespaces/kube-system/daemonsets|get ds --namespace kube-system||

## Sample from Kibana

![](images/alerts.png)

## Future Work

- Turn K8sCop into a system daemon
- Create an interface for adding new rules
- Correlate multiple events to detect more complex attacks
- Integrate triggers
- Make K8sCop interact with Kubernetes itself