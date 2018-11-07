#!/bin/bash
set -x


####

function install_deps() {
    out=$(slack -v)
    if [[ $1 -ne 0 ]]; then
        brew tap rockymadden/rockymadden
        brew install rockymadden/rockymadden/slack-cli
    fi
}

function setup_slack {
    presence=$(slack presence active | jq .ok)
    if [[ "$presence" != "true" ]]; then
        slack init
    fi
}

####

install_deps

setup_slack
