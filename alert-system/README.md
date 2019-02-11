# The Alert System

_The Alert System fetches the latest ElasticSearch k8s logs, parses the logs to detect specific patterns, and pushes new alerts back to ElasticSearch._

```
$ ./app.py -E localhost:9200 -I filebeat-6.5.4-2019.02.08 -i alerts -s 2019-2-9-10-0-0 -d 10 -D 600
```

- `-E`: the URL of the ElasticSearch instance
- `-I`: the index of the latest logs
- `-i`: the alerts index
- `-s`: the desired start date and time of the analysis
- `-d`: the delay between log fetches in seconds
- `-D`: the maximum delta for alert aggregation in seconds

## Flow Diagram

![](flow.png)

The Fetcher fetches data from ElasticSearch every `d` seconds and puts each entry into the Fetch Queue. 
The Parser gets data from the Fetch Queue, parses each entry and does some magic pattern recognition. 
If a pattern is matched, the entry is put in the Push Queue.
The Pusher gets entries from the Push Queue and pushes the corresponding alert(s) back to ElasticSearch every second.
The Pusher also takes care of alert aggregation: if the same alert has been seen in the last `D` seconds, the two alerts are aggregated. 