#!/bin/bash
printenv | grep -v "no_proxy" >> /etc/environment

# Create cron job file
touch /etc/cron.d/cronjob
# Create cron log file
touch /var/log/cron.log
# Add cron jobs
echo "*/${EXPORT_INTERVAL} * * * * root /usr/local/bin/python /app/f2b-geo-parser.py >> /var/log/cron.log 2>&1" >> /etc/cron.d/cronjob
echo "0 1 * * * root echo "" > /var/log/cron.log" >> /etc/cron.d/cronjob
chmod 0644 /etc/cron.d/cronjob
crontab /etc/cron.d/cronjob

# Start cron and then run the Python script
cron && tail -f /var/log/cron.log
