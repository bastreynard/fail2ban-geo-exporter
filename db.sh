#!/bin/bash
export MYSQL_USER="root"
export MYSQL_PASSWORD="_sqlrootpassword_"
if [ -z "$1" ]; then
echo "Possible args are \"geo\", \"total\" \"jails\", \"clear\" or \"custom\""
exit 0;
fi
if [ $1 == "geo" ]; then
docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT * FROM banned_ips"
docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT COUNT(*) FROM banned_ips"
elif [ $1 == "total" ]; then
docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT * FROM total_metrics"
elif [ $1 == "jails" ]; then
docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT * FROM jails"
elif [ $1 == "clear" ]; then
docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "TRUNCATE TABLE banned_ips"
elif [ $1 == "custom" ]; then
docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "$2"
fi