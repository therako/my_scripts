#!/bin/bash
# Usage: bash gpu-utilization.sh

# generates prometheus node-exported text files for GPU utilization using nvidia-smi

ROOT_DIR=/opt/node_exporter-0.14.0.linux-amd64/
TEXTFILE_COLLECTOR_PATH=${ROOT_DIR}/textfile_collector
SCRIPT_PATH=${ROOT_DIR}/scripts
SCRIPT_NAME=gpu-utilization
SCRIPT_FILE=${SCRIPT_PATH}/${SCRIPT_NAME}.sh
REFRESH_INTERVAL=10s

mkdir -p $SCRIPT_PATH
mkdir -p $TEXTFILE_COLLECTOR_PATH

# Initial variable setups
cat >${SCRIPT_FILE} <<EOF
#!/bin/bash
set -x

ROOT_DIR=${ROOT_DIR}
TEXTFILE_COLLECTOR_PATH=${TEXTFILE_COLLECTOR_PATH}
SCRIPT_PATH=${SCRIPT_PATH}

EOF

# Literal script executable setup
cat >>${SCRIPT_FILE} <<'EOF'
while true
do
    for METRIC in gpu memory; do
        TEXT_COLLECTOR_PATH=${TEXTFILE_COLLECTOR_PATH}/gpu_utilization_${METRIC}.prom
        ts=`date +%s%3N`
        res=$(nvidia-smi -i 0 --query-gpu="utilization.${METRIC}" --format=csv,noheader,nounits)
        echo "gpu_utilization_${METRIC}{} ${res} ${ts}" >> ${TEXT_COLLECTOR_PATH}.\$\$
        
        mv ${TEXT_COLLECTOR_PATH}.\$\$ ${TEXT_COLLECTOR_PATH}
    done
    sleep ${REFRESH_INTERVAL}
done
EOF

chmod +x ${SCRIPT_FILE}


# setup systemctl runner for the script
cat >/lib/systemd/system/ne-${SCRIPT_NAME}.service <<EOF
[Unit]
Description=Node Exporter metric - ${SCRIPT_NAME}

[Service]
ExecStart=${SCRIPT_FILE}
Restart=always
User=root
EOF

systemctl daemon-reload
systemctl restart ne-${SCRIPT_NAME}
systemctl enable ne-${SCRIPT_NAME}
