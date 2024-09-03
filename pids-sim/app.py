import os
import time
import random
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplePIDSSimulator:
    def __init__(self, alert_endpoint, locations, min_interval=5, max_interval=20):
        
        self.alert_endpoint = alert_endpoint
        self.locations = locations
        self.min_interval = min_interval
        self.max_interval = max_interval

    def simulate_breach(self):

        location = random.choice(self.locations)
        breach_detected = True  # Assume a breach is always detected for simulation purposes

        if breach_detected:
            
            logger.info(f"PIDS Tripped at location: {location}")

            # Send alert to backend
            alert_data = {
                "location": location,
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "alert_type": "PIDS_BREACH"
            }
            
            try:
                response = requests.post(self.alert_endpoint, json=alert_data)
                if response.status_code == 200:
                    logger.info(f"Alert sent successfully: {alert_data}")
                else:
                    logger.error(f"Failed to send alert. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error sending alert: {e}")

    def run(self):
        
        while True:
            self.simulate_breach()
            sleep_time = random.randint(self.min_interval, self.max_interval)
            logger.info(f"Next breach simulation in {sleep_time} seconds.")
            time.sleep(sleep_time)

if __name__ == "__main__":
    alert_endpoint = os.environ.get('ALERT_ENDPOINT', 'http://localhost:5000/pids_alert')
    locations = ["Sector A", "Sector B", "Sector C"]  # Example locations

    pids_simulator = SimplePIDSSimulator(
        alert_endpoint=alert_endpoint,
        locations=locations
    )
    pids_simulator.run()
