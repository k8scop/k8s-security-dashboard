# Kubernetes dashboard

<!-- vim-markdown-toc GFM -->

* [Installation](#installation)
* [Joining our cluster](#joining-our-cluster)
    * [Fluentd](#fluentd)
        * [Preparation](#preparation)
            * [Ulimit](#ulimit)
            * [Kernel parameter optimization](#kernel-parameter-optimization)
        * [Installation](#installation-1)
* [Mapping kubectl commands API endpoints](#mapping-kubectl-commands-api-endpoints)

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

For Ubuntu 18.04, install the `td-agent` as follows:

```bash
$ curl -L https://toolbelt.treasuredata.com/sh/install-ubuntu-bionic-td-agent3.sh | sh
```

You might need to add the key for the repository. This can be done using `gpg --recv-keys [key]`.

## Mapping kubectl commands API endpoints

|API|kubectl|comment|
|---|-------|-------|
|/api/v1/pods|get pods --all-namespaces||
|/api/v1/namespaces/kube-system/pods|get pods --namespace kube-system||
|/api/v1/namespaces/default/pods/busybox-test|describe busybox-test --namespace default||
|/api/v1/namespaces/default/pods/unsafe-space|describe pods unsafe-space --namespace default||
|/api/v1/pods?includeUninitialized=true|describe pods --all-namespaces||
|/api/v1/namespaces/default/secrets?includeUninitialized=true| Followed by multiple token queries|
|/api/v1/namespaces/default/pods|create -f <pod>| Method create|
