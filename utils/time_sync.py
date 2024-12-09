import ntplib
import time
import logging
from datetime import datetime

def get_ntp_time(timeout=1):
    """Get time from NTP server with timeout"""
    client = ntplib.NTPClient()
    try:
        response = client.request('pool.ntp.org', version=3, timeout=timeout)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        logging.error(f"Failed to fetch NTP time: {e}")
        return None

def sync_system_time(timeout=1):
    """Sync system time with NTP server"""
    try:
        ntp_time = get_ntp_time(timeout=timeout)
        if ntp_time:
            # Set system time if we have root access
            import os
            if os.geteuid() == 0:
                os.system(f'date -s "{ntp_time.strftime("%Y-%m-%d %H:%M:%S")}"')
                logging.info("System time synchronized successfully")
            else:
                logging.warning("Root access required to set system time")
        else:
            logging.warning("Failed to get NTP time, using system time")
    except Exception as e:
        logging.error(f"Error syncing system time: {e}") 