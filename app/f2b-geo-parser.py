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

retention_days = os.environ.get('RETENTION_DAYS')

# Use the credentials in your database connection
db_config = {
    'host': mysql_host,
    'user': mysql_user,
    'password': mysql_password,
    'database': mysql_database
}

def get_geo_info(ip: str) -> dict | None:
    """Function to get geo info from IP-API

    Args:
        ip (str): The ip to search info for

    Returns:
        dict | None: dict with geo info, if found (see https://ip-api.com/docs/api:json)
    """    
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

def store_banned_ip(banned_ip_info: list[str,str,str,int]) -> bool :
    """Function to store banned IP info in the database

    Args:
        banned_ip_info (str): Banned ip info [ip, bantime, jail, num_attempts]

    Returns:
        bool: True if a request was sent to IP-API, False otherwise
    """    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    req_sent = False
    ip = banned_ip_info[0]
    timestamp = banned_ip_info[1]
    attempts = banned_ip_info[3]
    jail = banned_ip_info[2]

    # Check if the IP address already exists in the database
    cursor.execute("SELECT COUNT(*) FROM banned_ips WHERE ip = %s", (ip,))
    count = cursor.fetchone()[0]

    if count == 0:
        # Fetch geo info 
        geo_info = get_geo_info(ip)
        req_sent = True
        if geo_info:
            insert_query = """
            INSERT INTO banned_ips (ip, bantime, country, city, isp, latitude, longitude, attempts, jail)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (ip, timestamp, geo_info['country'], 
                geo_info['city'], geo_info['isp'],
                geo_info['lat'], geo_info['lon'], attempts, jail))
        else:
            insert_query_no_geo = """
            INSERT INTO banned_ips (ip, bantime, attempts, jail)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query_no_geo, (ip, timestamp, attempts, jail))
        conn.commit()
    else:
        print(f"IP {ip} already exists in the database. Skipping insertion.")

    cursor.close()
    conn.close()
    return req_sent

def store_num_bans(num_banned_ips: int, num_failed_attempts: int) -> None:
    """Function to store the number of bans and failed attempts at a given time

    Args:
        num_banned_ips (int): Total number of banned ips
        num_failed_attempts (int): Total number of failed attempts
    """    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    now = datetime.now()
    insert_query = """
            INSERT INTO total_metrics (timestamp, num_ips, num_failed_attempts)
            VALUES (%s, %s, %s)
            """
    cursor.execute(insert_query, (now, num_banned_ips, num_failed_attempts))

    # Cleanup older entries
    cursor.execute("DELETE FROM total_metrics WHERE timestamp < now() - interval %s DAY", (retention_days,))
    conn.commit()

    cursor.close()
    conn.close()

def store_jails(jails: list[str]) -> None:
    """Function for storing jails in DB

    Args:
        jails (list[str]): List of jails to store
    """    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    print(f"jails : {jails}")
    for jail in jails:
        cursor.execute("SELECT COUNT(*) FROM jails WHERE jail = %s", (jail,))
        count = cursor.fetchone()[0]
        if count == 0:
            insert_query = """
                    INSERT INTO jails (jail) 
                    VALUES (%s)
                    """
            cursor.execute(insert_query, (jail,))
    conn.commit()

    cursor.close()
    conn.close()

def remove_banned_ip(ip: str) -> None:
    """Function to remove unbanned IP info from the database

    Args:
        ip (str): the ip to remove from DB
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    delete_query = "DELETE FROM banned_ips WHERE ip = %s"
    cursor.execute(delete_query, (ip,))
    conn.commit()

    cursor.close()
    conn.close()

def parse_jails(log_file_path: str) -> list[str]:
    """Function to extract active jails from log file

    Args:
        log_file_path (str): Path to fail2ban log file for parsing

    Returns:
        list[str]: List of jails found in log file
    """
    jail_pattern = re.compile(r'^(.*?\[.*?\]: (INFO|NOTICE)\s*\[\s*([^\]]+)\s*\])')
    jails = []
    with open(log_file_path, 'r') as file:
        # Search jails
        for line in file:
            jail_match = jail_pattern.search(line)
            if jail_match:
                jail = jail_match.group(3)
                if jail not in jails:
                    jails.append(jail)
    return jails

def parse_log_file(log_file_path: str) -> tuple[list[str,str,str,int], list[str,str,str], int]:
    """Function to extract banned and unbanned IPs from log file

    Args:
        log_file_path (str): Path to fail2ban log file for parsing

    Returns:
        banned_ips: List of banned ips [ip, bantime, jail, num_attempts]
        unbanned_ips: List of unbanned ips [ip, bantime, jail]
        num_failed_attempts: Total number of failed attempts logged
    """
    ip_states = {}
    num_failed_attempts = 0
    ban_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* NOTICE  (\[\s*([^\]]+)\s*\]) (Ban|Restore Ban) (\d+\.\d+\.\d+\.\d+)')
    unban_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* NOTICE  (\[\s*([^\]]+)\s*\]) Unban (\d+\.\d+\.\d+\.\d+)')
    attempt_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .* INFO    (\[\s*([^\]]+)\s*\]) Found (\d+\.\d+\.\d+\.\d+) .*')

    with open(log_file_path, 'r') as file:
        # Search Bans/Unbans
        for line in file:
            ban_match = ban_pattern.search(line)
            if ban_match:
                timestamp = datetime.strptime(ban_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                jail = ban_match.group(3)
                ip = ban_match.group(5)
                if ip not in ip_states or ip_states[ip][1] == 'unban':
                    ip_states[ip] = [timestamp, 'ban', jail, 0]
            
            unban_match = unban_pattern.search(line)
            if unban_match:
                timestamp = datetime.strptime(unban_match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                jail = unban_match.group(3)
                ip = unban_match.group(4)
                if ip not in ip_states or ip_states[ip][0] < timestamp:
                    ip_states[ip] = [timestamp, 'unban', jail]

    with open(log_file_path, 'r') as file:
        # Search attempts
        for line in file:
            attempt_match = attempt_pattern.search(line)
            if attempt_match:
                num_failed_attempts += 1
                jail = attempt_match.group(3)
                ip = attempt_match.group(4)
                if ip in ip_states and ip_states[ip][1] == 'ban':
                    ip_states[ip][3] += 1 # Increments attempts number

    # Separate IPs into banned and unbanned based on the latest state
    banned_ips = [(ip, state[0], state[2], state[3]) for ip, state in ip_states.items() if state[1] == 'ban']
    unbanned_ips = [(ip, state[0], state[2]) for ip, state in ip_states.items() if state[1] == 'unban']

    return banned_ips, unbanned_ips, num_failed_attempts

def main():
    """Entry point
    """
    log_file_path = '/var/log/fail2ban.log'  # Path to the log file
    num_req = 0
    jails = parse_jails(log_file_path)
    store_jails(jails)
    banned_ips, unbanned_ips, num_failed = parse_log_file(log_file_path)

    # Process banned IPs
    for ip in banned_ips:
        req_sent = store_banned_ip(ip)
        if req_sent:
            num_req = num_req + 1
        print(f"Banned IP {ip[0]} information stored successfully.")
        if num_req == 45:
            print("Rate limit reached. Waiting for 60 seconds before continuing.")
            num_req = 0
            time.sleep(62)

    # Process unbanned IPs
    for ip in unbanned_ips:
        remove_banned_ip(ip[0])
        print(f"Unbanned IP {ip[0]} removed successfully.")

    # Store number of bans
    store_num_bans(len(banned_ips), num_failed)

if __name__ == "__main__":
    main()
