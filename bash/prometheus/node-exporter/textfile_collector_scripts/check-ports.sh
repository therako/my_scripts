#!/bin/bash
# Usage: bash check-ports.sh 80 443

# list of ports to check in the local vm
PORTS="${@:1}"

ROOT_DIR=/tmp
TEXTFILE_COLLECTOR_PATH=${ROOT_DIR}/textfile_collector
SCRIPT_PATH=${ROOT_DIR}/scripts
SCRIPT_NAME=check-ports
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
PORTS="${PORTS}"

EOF

# Literal script executable setup
cat >>${SCRIPT_FILE} <<'EOF'
while true
do
    for PORT in ${PORTS[@]}; do
        RESULT_PATH=${TEXTFILE_COLLECTOR_PATH}/port_${PORT}.prom
        ts=$(date +%s%3N)
        timeout 1 curl localhost:${PORT} > /dev/null
        if [ $? == "0" ]; then
                echo $(date) ": up"
                echo "port_${PORT}{} 1 ${ts}" >> ${RESULT_PATH}.\$\$
        else
                echo $(date) ": down"
                echo "port_${PORT}{} 0 ${ts}" >> ${RESULT_PATH}.\$\$
        fi
        
        mv ${RESULT_PATH}.\$\$ ${RESULT_PATH}
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
