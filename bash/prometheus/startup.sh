#!/bin/bash
# Prometheus install and setup bash script for Debain.
set -x
set -e

ROOT_DIR=/opt/prometheus-1.7.1.linux-amd64/
PROMETHEUS_FILE_SHRINK_RATIO=0.3
PROMETHEUS_MEMORY_CHUNKS=2097152
PROMETHEUS_RETENTION=2920h0m0s
ALERTMANAGER_URL=http://localhost:9093

# Safer to have a seperate attached disk for data, with possibly large size disk
PROMETHEUS_DATA_PATH=/mnt/disks/data/prometheus
mkdir -p ${PROMETHEUS_DATA_PATH}


if [ ! -f "${ROOT_DIR}/node_exporter" ]; then
    cd /tmp && wget https://github.com/prometheus/prometheus/releases/download/v1.7.1/prometheus-1.7.1.linux-amd64.tar.gz
    tar -xf /tmp/prometheus-1.7.1.linux-amd64.tar.gz --directory /opt/
fi

# setup prometheus config
cat >${ROOT_DIR}/prometheus.yml <<EOF
global:
  scrape_interval:     15s # By default, scrape targets every 15 seconds.
  evaluation_interval: 15s # By default, scrape targets every 15 seconds.
  # scrape_timeout is set to the global default (10s).

  # Attach these labels to any time series or alerts when communicating with
  # external systems (federation, remote storage, Alertmanager).
  external_labels:
      monitor: 'example'

# Load and evaluate rules in this file every 'evaluation_interval' seconds.
rule_files:
  - ${ROOT_DIR}/rules/*.rules

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: node
    scrape_interval: 5s
    scrape_timeout: 5s
    # TODO: add any type of prometheus node discovery configs here.
EOF


# setup systemctl script for Prometheus
cat >/lib/systemd/system/prometheus.service <<EOF
[Unit]
Description=Monitoring system and time series database
Documentation=https://prometheus.io/docs/introduction/overview/

[Service]
Restart=always
User=root
Environment=PROMETHEUS_CONFIG=${ROOT_DIR}/prometheus.yml
Environment=PROMETHEUS_FILE_SHRINK_RATIO=${PROMETHEUS_FILE_SHRINK_RATIO}
Environment=PROMETHEUS_MEMORY_CHUNKS=${PROMETHEUS_MEMORY_CHUNKS}
Environment=PROMETHEUS_RETENTION=${PROMETHEUS_RETENTION}
Environment=PROMETHEUS_DATA_PATH=${PROMETHEUS_DATA_PATH}
ExecReload=/bin/kill -HUP $MAINPID
ExecStart=${ROOT_DIR}/prometheus -alertmanager.url=${ALERTMANAGER_URL} -storage.local.retention=${PROMETHEUS_RETENTION} -storage.local.series-file-shrink-ratio=${PROMETHEUS_FILE_SHRINK_RATIO} -storage.local.memory-chunks=${PROMETHEUS_MEMORY_CHUNKS} -config.file=${PROMETHEUS_CONFIG} -storage.local.path=${PROMETHEUS_DATA_PATH}
LimitNOFILE=65536
TimeoutStopSec=20s
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart prometheus
systemctl enable prometheus
