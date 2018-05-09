#!/bin/bash

echo "remove exited containers"
docker ps --filter status=dead --filter status=exited -aq | xargs docker rm -v
echo "remove unused images"
docker images --no-trunc | grep -v 'hour' | awk '{ print $3 }' | xargs docker rmi
