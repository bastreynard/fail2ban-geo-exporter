import os
import mysql.connector
import requests
import time
import re
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError
from datetime import datetime

# Get database credentials from environment variables
mysql_host = os.environ.get('MYSQL_HOST')
mysql_user = os.environ.get('MYSQL_USER')
mysql_password = os.environ.get('MYSQL_PASSWORD')
mysql_database = os.environ.get('MYSQL_DATABASE')

# Use the credentials in your database connection
db_config = {
    'host': mysql_host,
    'user': mysql_user,
    'password': mysql_password,
    'database': mysql_database
}

# Function to get geo info from IP-API
def get_geo_info(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 404, 500)
        data = response.json()
        if data['status'] == 'success':
            return data
        else:
            print(f"Failed to retrieve geo information for IP {ip}: {data.get('message', 'Unknown error')}")
            return None
    except JSONDecodeError as e:
        print(f"Failed to decode JSON response for IP {ip}: {e}")
        return None
    except RequestException as e:
        print(f"An error occurred while requesting geo information for IP {ip}: {e}")
        return None

# Function to store banned IP info in the database
def store_banned_ip(ip, geo_info):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    bantime = datetime.now()

    # Check if the IP address already exists in the database
    cursor.execute("SELECT COUNT(*) FROM banned_ips WHERE ip = %s", (ip,))
    count = cursor.fetchone()[0]

    if count == 0:
        insert_query = """
        INSERT INTO banned_ips (ip, bantime, country, region, isp, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        insert_query_no_geo = """
        INSERT INTO banned_ips (ip, bantime)
        VALUES (%s, %s)
        """
        if geo_info:
            cursor.execute(insert_query, (ip, bantime, geo_info['country'], 
                geo_info['regionName'], geo_info['isp'],
                geo_info['lat'], geo_info['lon']))
        else:
            cursor.execute(insert_query_no_geo, (ip, bantime))
        conn.commit()
    else:
        print(f"IP {ip} already exists in the database. Skipping insertion.")

    cursor.close()
    conn.close()

# Function to remove unbanned IP info from the database
def remove_banned_ip(ip):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    delete_query = "DELETE FROM banned_ips WHERE ip = %s"
    cursor.execute(delete_query, (ip,))
    conn.commit()

    cursor.close()
    conn.close()

def parse_log_file(log_file_path):
    ip_states = {}
    ban_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* NOTICE  \[sshd\] (Ban|Restore Ban) (\d+\.\d+\.\d+\.\d+)')
    unban_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* NOTICE  \[sshd\] Unban (\d+\.\d+\.\d+\.\d+)')

    with open(log_file_path, 'r') as file:
        for line in file:
            ban_match = ban_pattern.search(line)
            if ban_match:
                print(line)
                timestamp = datetime.strptime(ban_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                ip = ban_match.group(3)
                if ip not in ip_states or ip_states[ip][1] == 'unban':
                    ip_states[ip] = (timestamp, 'ban')
            
            unban_match = unban_pattern.search(line)
            if unban_match:
                print(line)
                timestamp = datetime.strptime(unban_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                ip = unban_match.group(2)
                if ip not in ip_states or ip_states[ip][0] < timestamp:
                    ip_states[ip] = (timestamp, 'unban')

    # Separate IPs into banned and unbanned based on the latest state
    banned_ips = {ip for ip, state in ip_states.items() if state[1] == 'ban'}
    unbanned_ips = {ip for ip, state in ip_states.items() if state[1] == 'unban'}

    return banned_ips, unbanned_ips

# Main function
def main():
    log_file_path = '/var/log/fail2ban.log'  # Path to the log file
    banned_ips, unbanned_ips = parse_log_file(log_file_path)

    ip_list = list(banned_ips)
    for i in range(0, len(ip_list), 45):
        batch = ip_list[i:i + 45]
        for ip in batch:
            geo_info = get_geo_info(ip)
            if geo_info:
                store_banned_ip(ip, geo_info)
                print(f"Banned IP {ip} information stored successfully.")
            else:
                store_banned_ip(ip, None)
                print(f"Failed to retrieve geo information for IP {ip}.")
        if i + 45 < len(ip_list):
            print("Rate limit reached. Waiting for 60 seconds before continuing.")
            time.sleep(60)

    # Process unbanned IPs
    for ip in unbanned_ips:
        remove_banned_ip(ip)
        print(f"Unbanned IP {ip} removed successfully.")

if __name__ == "__main__":
    main()
