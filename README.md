# Kubernetes dashboard

<!-- vim-markdown-toc GFM -->

* [Installation](#installation)
* [Joining our cluster](#joining-our-cluster)
    * [Fluentd](#fluentd)
        * [Preparation](#preparation)
            * [Ulimit](#ulimit)
            * [Kernel parameter optimization](#kernel-parameter-optimization)
        * [Installation](#installation-1)

<!-- vim-markdown-toc -->

## Installation

## Joining our cluster

```bash
$ kubeadm join 192.168.57.4:6443 --token peraiv.rdak5meh6lklbof2 --discovery-token-ca-cert-hash sha256:44f06aa4ce1ec31691368b206c86955692738746de826ce9b96cb77cb0caadbb
```


### Fluentd
For Debian based distros the required APT repository files can be found (here)[https://docs.fluentd.org/v1.0/articles/install-by-deb]. For other distributions, files and a guide can be found (here)[https://docs.fluentd.org/v1.0/articles/quickstart].

#### Preparation

##### Ulimit
Check if the `ulimit` is sufficient. Is the output similar to the output below?

```zsh
$ ulimit -n
1024
```

Then add the following lines to `/etc/security/limits.d/fluentd.conf`:

```config
root soft nofile 65536
root hard nofile 65536
* soft nofile 65536
* hard nofile 65536
```

To apply the changes, reboot the computer.

##### Kernel parameter optimization
For high load environments, having loads of Fluentd instances, it is recommended to apply the following settings:

```sysctl
net.core.somaxconn = 1024
net.core.netdev_max_backlog = 5000
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_wmem = 4096 12582912 16777216
net.ipv4.tcp_rmem = 4096 12582912 16777216
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10240 65535
```

Add this to `/etc/sysctl.conf`. Reboot or type `sysctl -p` to apply the changes.


#### Installation

```
kind: Namespace
apiVersion: v1
metadata:
  name: kube-logging
```


```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fluentd
  namespace: kube-logging
  labels:
    app: fluentd
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: fluentd
  labels:
    app: fluentd
rules:
- apiGroups:
  - ""
  resources:
  - pods
  - namespaces
  verbs:
  - get
  - list
  - watch
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: fluentd
roleRef:
  kind: ClusterRole
  name: fluentd
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: fluentd
  namespace: kube-logging
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: kube-logging
  labels:
    app: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      serviceAccount: fluentd
      serviceAccountName: fluentd
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v0.12-debian-elasticsearch
        env:
          - name:  FLUENT_ELASTICSEARCH_HOST
            value: "192.168.57.4"
          - name:  FLUENT_ELASTICSEARCH_PORT
            value: "9200"
          - name: FLUENT_ELASTICSEARCH_SCHEME
            value: "http"
          - name: FLUENT_UID
            value: "0"
        resources:
          limits:
            memory: 512Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      terminationGracePeriodSeconds: 30
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```
