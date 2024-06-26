# Fail2ban Geo Exporter

Collect informations about a running fail2ban instance, along with location data for every IPs logged, using http://ip-api.com.

The parsed log and additional geo data is stored in a mysql database for easy Grafana visualization.

![image](https://github.com/bastreynard/fail2ban-geo-exporter/assets/26840072/af33bff4-0e43-42c7-a3bb-7fab930b01da)

## Docker Install

There is a ready to use `docker-compose.yml` that will setup 2 containers:

- `mysql`: Container for storing fail2ban data
- `f2b-geo-exporter`: Container running the python parser/exporter periodically

### Prepare install

- Update the MYSQL_ROOT_PASSWORD and EXPORT_INTERVAL to your liking in `docker-compose.yml`.

    NOTE: Because of ip-api limitations, the script will wait for 1 minute every 45 requests. Hence, you should not set the period to a value too short.

- Replace network `net_prometheus` with the network your grafana instance is running on, or simply connect your grafana instance to `net_f2b_geo_export`.

- If necessary, adapt the path to fail2ban logs (default: `/var/log/fail2ban.log`).

### Run

Build and run the docker containers:

`docker compose up -d --build`

## Alternative install

It's also possible to manually create a MySQL database (use init.sql file), and run the python script `f2b-geo-parser.py` periodically with the system cron.

## Check install

Check that the database is being updated regularly (default: 5 mins):

`docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT * FROM banned_ips"`

`docker exec -it mysql-f2b-geo-export mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -Dbanned_ips_db -e "SELECT COUNT(*) FROM banned_ips"`

The python script output will be located under `/var/log/cron.log`, and cleared every day at 1am.

## Grafana

[Add a new MySQL data source to your Grafana](https://grafana.com/grafana/plugins/mysql/) instance with 
- Host URL: mysql-f2b-geo-export:3306
- Database name: banned_ips_db
- Username: root
- Password: MYSQL_ROOT_PASSWORD set in ```docker-compose.yml```

Then you can import `grafana/dashboard.json` or directly from [Grafana](https://grafana.com/grafana/dashboards/21210).
