#!/bin/bash
# Prometheus node-exporter install and setup bash script for Debain.
set -x
set -e

ROOT_DIR=/opt/node_exporter-0.14.0.linux-amd64/
EXECUTABLE=${ROOT_DIR}/node_exporter

TEXTFILE_COLLECTOR_PATH=${ROOT_DIR}/textfile_collector/
ENABLED_STATS='conntrack,diskstats,entropy,filefd,filesystem,loadavg,mdadm,meminfo,netdev,netstat,sockstat,stat,textfile,time,uname,vmstat,tcpstat'
IGNORED_DEVICES='^(ram|loop|fd)\d+$'


if [ ! -f "${EXECUTABLE}" ]; then
    cd /tmp && wget https://github.com/prometheus/node_exporter/releases/download/v0.14.0/node_exporter-0.14.0.linux-amd64.tar.gz /tmp
    tar -xf /tmp/node_exporter-0.14.0.linux-amd64.tar.gz --directory /opt/
fi

# configure textfile collector
mkdir -p $TEXTFILE_COLLECTOR_PATH


cat >/lib/systemd/system/node-exporter.service <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
ExecStart=${EXECUTABLE} -collectors.enabled ${ENABLED_STATS} -collector.diskstats.ignored-devices="${IGNORED_DEVICES}" -collector.textfile.directory=${TEXTFILE_COLLECTOR_PATH}
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart node-exporter
systemctl enable node-exporter
