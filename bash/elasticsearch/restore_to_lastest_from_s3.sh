#/bin/bash
set -e
set -x

####
# Can be used to restore and start a new ES cluster with backups from S3.
# requires jq tool for JSON parsing in bash
# parmas
# 1. ES host name/ip (eg, localhost)
# 2. ES snapshot name (setup - https://www.elastic.co/guide/en/elasticsearch/plugins/2.2/cloud-aws-repository.html)
# 3. ES index name, eg: user
# 
# usage: bash restore_to_latest_from_s3.sh localhost s3_backup_repo user
####

if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters"
fi

HOST=$1
SNAPSHOT_NAME=$2
INDEX_NAME=$3

TMP_FILE='/tmp/all_snapshots.json'

####
function fetch_available_snapshots() {
    curl "http://${HOST}:9200/_snapshot/${SNAPSHOT_NAME}/_all" > ${TMP_FILE}
}

function get_latest_snapshot_name() {
    local last_snapshot_time=$(cat ${TMP_FILE} | jq '.snapshots[] | select(.state=="SUCCESS") |.end_time' | sort -r | head -n 1)
    local last_snapshot_name=$(cat ${TMP_FILE} | jq '.snapshots[] | select(.end_time=='${last_snapshot_time}') | .snapshot' | tr -d '"')
    echo ${last_snapshot_name}
}

function close_index() {
    local response=$(curl -XPOST "http://${HOST}:9200/${INDEX_NAME}/_close" | jq '.acknowledged')
    
    if [[ ${response} != 'true' ]]; then
        echo "Error in closing the index for restore process."
        exit 11
    fi
}

function initate_the_restore_process() {
    local last_snapshot_name=$1
    local response=$(curl -XPOST "http://${HOST}:9200/_snapshot/${SNAPSHOT_NAME}/${last_snapshot_name}/_restore" | jq '.accepted')

    if [[ ${response} != 'true' ]]; then
        echo "Error in initiate restore process."
        exit 12
    fi
}

function wait_for_recovery() {
    # wait untill all shards are recovered to 100%
    while true; do
        ALL_RECOVERED=true
        shard_recovery_percentile=$(curl http://${HOST}:9200/_recovery | jq ".${INDEX_NAME}.shards[].index.files.percent")
        for shard_percent in ${shard_recovery_percentile[@]}; do
            if [[ ${shard_percent} != "\"100.0%\"" ]]; then
                ALL_RECOVERED=false
            fi
        done

        if [[ ${ALL_RECOVERED} == true ]]; then
            echo "All partitions recovered"
            break
        fi
        sleep 1s
    done
}

function open_index() {
    local response=$(curl -XPOST "http://${HOST}:9200/${INDEX_NAME}/_open" | jq '.acknowledged')
    
    if [[ ${response} != 'true' ]]; then
        echo "Error in opening the index for restore process."
        exit 13
    fi
}

####

fetch_available_snapshots

last_snapshot_name=$(get_latest_snapshot_name)

close_index

initate_the_restore_process ${last_snapshot_name}

wait_for_recovery

open_index

echo "Successfully restore ES from S3."
