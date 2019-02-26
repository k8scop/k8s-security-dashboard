# Kubernetes dashboard

<!-- vim-markdown-toc GFM -->

* [Installation](#installation)
    * [Preparation](#preparation)
    * [Deploying fluent](#deploying-fluent)
    * [Debugging](#debugging)
* [Mapping kubectl commands API endpoints](#mapping-kubectl-commands-api-endpoints)

<!-- vim-markdown-toc -->

## Installation

### Preparation

Create the mount directory for the fluent configuration:

```bash
# mkdir -p /var/share/volumes/fluent/etc
```

Add the files from the `configs/fluent` folder:

```bash
# cp entrypoint.sh Gemfile /var/share/volumes/fluent/.
# cp fluent.conf /var/share/volumes/fluent/etc/.
```

### Deploying fluent

Change the environment variables to connect to the installed elasticsearch installation:

```yaml
     - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1.1-debian-elasticsearch
        env:
          - name:  FLUENT_ELASTICSEARCH_HOST
            value: "192.168.178.65"
          - name:  FLUENT_ELASTICSEARCH_PORT
            value: "9200"
          - name: FLUENT_ELASTICSEARCH_SCHEME
            value: "http"
          - name: FLUENT_UID
            value: "0"
          - name: FLUENT_ELASTICSEARCH_USER # even if not used they are necessary
            value: "foo"
          - name: FLUENT_ELASTICSEARCH_PASSWORD # even if not used they are necessary
            value: "bar"
        resources:
```

Apply the yaml configuration file:

```bash
$ kubectl apply -f fluentd-setup.yml
```

There should be a `kube-logging` namespace, containing a volume(claim), a fluent pod and service account.

### Debugging 

To check the progress or to debug error messages, run the following command:

```bash
$ kubectl --namespace kube-logging logs fluent-[identifier] init-fluentd -f
```

This will stream the init containers' stdout/stderr while installing the required gems.
Omit `init-fluentd` to stream the logs of the actual container.


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
|/api/v1/services?limit=500|get svc --all-namespaces||
|/apis/extensions/v1beta1/daemonsets |get ds --all-namespaces||
|/apis/extensions/v1beta1/namespaces/kube-system/daemonsets|get ds --namespace kube-system||

