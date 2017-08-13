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

# Alermanager config
cat >${ROOT_DIR}/templates/node.tmpl <<EOF
{{ define "slack.node.title" }}[{{ .Status | toUpper }}{{ if eq .Status "firing" }}: {{ .Alerts.Firing | len }}{{ end }}] {{ .GroupLabels.alertname }} on {{ .GroupLabels.cluster }}{{ end }}

{{ define "slack.node.instances" }}{{ range . }}- *{{ .Labels.host }}* ({{ .Labels.instance }})
{{ end }}{{ end }}

{{ define "slack.node.text" }}
{{ .CommonAnnotations.summary }}.

{{ if gt (len .Alerts.Firing) 0 -}}Alerts Firing:
{{ template "slack.node.instances" .Alerts.Firing }}{{- end }}{{ if gt (len .Alerts.Resolved) 0 -}}Alerts Resolved:
{{ template "slack.node.instances" .Alerts.Resolved }}{{ end }}

Grafana: http://localhost:3000/dashboard/db/node?var-cluster={{ .GroupLabels.cluster }}
{{ end }}
EOF

cat >${ROOT_DIR}/alertmanager.yml <<EOF
global:

route:
  receiver: 'slack'
  group_by: ['alertname', 'cluster']
  group_wait: 3s
  group_interval: 3s
  repeat_interval: 30m
  routes:
  - receiver: 'slack'

receivers:
- name: 'slack'
  slack_configs:
  - api_url: 'Slack webbhook url'
    channel: '#channel-name'
    title: '{{ template "slack.node.title" . }}'
    text: '{{ template "slack.node.text" . }}'
    send_resolved: True

templates:
  - ${ROOT_DIR}/templates/node.tmpl
EOF


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
