#!/bin/bash
if [ $# -eq 0 ]; then
  echo "`date`: ERROR: Please start this script with:"
  echo "`date`: ERROR: $0 <file.jsonl> <docker container>"
  exit 1;
fi


CONTAINER=$2
if [ -z "$CONTAINER" ]
then
  CONTAINER="ctlg-manager_solr_1"
fi
docker cp $1 $CONTAINER:/opt/solr/mydata.jsonl
docker exec -it --user=solr $CONTAINER bin/post -c documents mydata.jsonl
