#!/bin/bash
set -e
docker build -t goncaloferreirauva/gd-cnr-adapter-service:latest -f ./app/Dockerfile ./app
docker push goncaloferreirauva/gd-cnr-adapter-service:latest