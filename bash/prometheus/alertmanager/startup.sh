#!/bin/bash
# Prometheus alertmanager install and setup bash script for Debain.
set -x
set -e

ROOT_DIR=/opt/alertmanager-0.8.0.linux-amd64/
EXECUTABLE=${ROOT_DIR}/alertmanager


if [ ! -f "${EXECUTABLE}" ]; then
    cd /tmp && wget https://github.com/prometheus/alertmanager/releases/download/v0.8.0/alertmanager-0.8.0.linux-amd64.tar.gz
    tar -xf /tmp/alertmanager-0.8.0.linux-amd64.tar.gz --directory /opt/
fi


# setup systemctl script for alertmanager
cat >/lib/systemd/system/alertmanager.service <<EOF
[Unit]
Description=Prometheus Alertmanager
After=network.target

[Service]
Restart=always
User=root
ExecReload=/bin/kill -HUP $MAINPID
WorkingDirectory=${ROOT_DIR}
ExecStart=${EXECUTABLE}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart alertmanager
systemctl enable alertmanager
