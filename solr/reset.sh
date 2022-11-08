docker stop ctlg-manager_solr_1
docker rm ctlg-manager_solr_1
docker volume rm ctlg-manager_solr
docker-compose up -d
sleep 10
./fields.sh