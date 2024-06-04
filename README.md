# Fail2ban Geo Exporter

Collect informations about a running fail2ban instance, along with location data for every IPs logged, using http://ip-api.com.

The parsed log and additional geo data is stored in a mysql database for easy Grafana visualization.

For now it exports only the banned IPs from the sshd jail.

## Docker Install

There is a ready to use `docker-compose.yml` that will setup 2 containers:

- `mysql`: Container for storing fail2ban data
- `f2b-geo-exporter`: Container running the python parser/exporter periodically

Update the MYSQL_ROOT_PASSWORD to your liking in `docker-compose.yml`, in both `f2b-geo-export` and `mysql` services.

Update the `cronjob` file if you want another period (5 mins).

NOTE: Because of ip-api limitations, the script will wait for 1 minute every 45 requests. Hence, you should not set the period to a value too short.

Replace network `net_prometheus` with the network your grafana instance is running on, or simply connect your grafana instance to `net_f2b_geo_export`.

If necessary, adapt the path to fail2ban logs (default: `/var/log/fail2ban.log`).

Build and run the docker containers:

`docker compose up -d --build`

## Alternative install

It's also possible to manually create a MySQL database (use init.sql file), and run the python script `f2b-geo-parser.py` periodically with the system cron.

## Check install

Check that the database is beeing updated regularly (default: 5 mins):

`docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT * FROM banned_ips"`

`docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT COUNT(*) FROM banned_ips"`

The python script output will be located under `/var/log/cron.log`.

## Grafana

Add a new MySQL data connection to your grafana instance and import the `dashboard.json`

