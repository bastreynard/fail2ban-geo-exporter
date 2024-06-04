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
def get_geo_info(ip: str) -> dict | None:
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
# Returns True is the request was sent to IP-API
def store_banned_ip(banned_ip: str) -> bool :
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    req_sent = False
    ip = banned_ip[0]
    timestamp = banned_ip[1]
    attempts = banned_ip[2]

    # Check if the IP address already exists in the database
    cursor.execute("SELECT COUNT(*) FROM banned_ips WHERE ip = %s", (ip,))
    count = cursor.fetchone()[0]

    if count == 0:
        # Fetch geo info 
        geo_info = get_geo_info(ip)
        req_sent = True
        if geo_info:
            insert_query = """
            INSERT INTO banned_ips (ip, bantime, country, city, isp, latitude, longitude, attempts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (ip, timestamp, geo_info['country'], 
                geo_info['city'], geo_info['isp'],
                geo_info['lat'], geo_info['lon'], attempts))
        else:
            insert_query_no_geo = """
            INSERT INTO banned_ips (ip, bantime, attempts)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query_no_geo, (ip, timestamp, attempts))
        conn.commit()
    else:
        print(f"IP {ip} already exists in the database. Skipping insertion.")

    cursor.close()
    conn.close()
    return req_sent

# Function to store the number of bans at a given time
def store_num_bans() -> None:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("SELECT COUNT(ip) FROM banned_ips")
    count = cursor.fetchone()[0]
    print(f"Currently banned : {count}")
    insert_query = """
            INSERT INTO num_bans (timestamp, num)
            VALUES (%s, %s)
            """
    cursor.execute(insert_query, (now, count))
    conn.commit()

    cursor.close()
    conn.close()

# Function to remove unbanned IP info from the database
def remove_banned_ip(ip: str) -> None:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    delete_query = "DELETE FROM banned_ips WHERE ip = %s"
    cursor.execute(delete_query, (ip,))
    conn.commit()

    cursor.close()
    conn.close()

def parse_log_file(log_file_path: str) -> tuple[list[str,str,int], list[str,str]]:
    ip_states = {}
    ban_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* NOTICE  \[sshd\] (Ban|Restore Ban) (\d+\.\d+\.\d+\.\d+)')
    unban_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* NOTICE  \[sshd\] Unban (\d+\.\d+\.\d+\.\d+)')
    attempt_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* INFO    \[sshd\] Found (\d+\.\d+\.\d+\.\d+) .*')

    with open(log_file_path, 'r') as file:
        # Search Bans/Unbans
        for line in file:
            ban_match = ban_pattern.search(line)
            if ban_match:
                timestamp = datetime.strptime(ban_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                ip = ban_match.group(3)
                if ip not in ip_states or ip_states[ip][1] == 'unban':
                    ip_states[ip] = [timestamp, 'ban', 0]
            
            unban_match = unban_pattern.search(line)
            if unban_match:
                timestamp = datetime.strptime(unban_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                ip = unban_match.group(2)
                if ip not in ip_states or ip_states[ip][0] < timestamp:
                    ip_states[ip] = [timestamp, 'unban']

    with open(log_file_path, 'r') as file:
        # Search attempts
        for line in file:
            attempt_match = attempt_pattern.search(line)
            if attempt_match:
                ip = attempt_match.group(2)
                if ip in ip_states and ip_states[ip][1] == 'ban':
                    ip_states[ip][2] += 1 # Increments attempts number

    # Separate IPs into banned and unbanned based on the latest state
    banned_ips = {(ip, state[0], state[2]) for ip, state in ip_states.items() if state[1] == 'ban'}
    unbanned_ips = {(ip, state[0]) for ip, state in ip_states.items() if state[1] == 'unban'}

    return banned_ips, unbanned_ips

# Main function
def main():
    log_file_path = '/var/log/fail2ban.log'  # Path to the log file
    num_req = 0
    banned_ips, unbanned_ips = parse_log_file(log_file_path)

    # Process banned IPs
    for ip in banned_ips:
        req_sent = store_banned_ip(ip)
        if req_sent:
            num_req = num_req + 1
        print(f"Banned IP {ip[0]} information stored successfully.")
        if num_req == 45:
            print("Rate limit reached. Waiting for 60 seconds before continuing.")
            num_req = 0
            time.sleep(60)

    # Process unbanned IPs
    for ip in unbanned_ips:
        remove_banned_ip(ip[0])
        print(f"Unbanned IP {ip[0]} removed successfully.")

    # Store number of bans
    store_num_bans()

if __name__ == "__main__":
    main()
