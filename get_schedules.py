import appdaemon.plugins.hass.hassapi as hass
import requests
from datetime import datetime, timedelta
import urllib.parse
import time

MINUTE = 60 

class SofiaTrafficSensor(hass.Hass):
    def initialize(self):
        # Configuration: Stop ID
        self.stop_id = self.args.get("stop_id")
        self.sensor_name = self.args.get("sensor_name")

        # Initialize the stop name and headers
        self.stop_name = None
        self.headers = None
        self.headers_last_updated = 0  # Timestamp of last headers update
        self.fetch_stop_name()

        # Create the sensor in Home Assistant
        self.set_state(self.sensor_name, state="Initializing", attributes={"lines": {}, "friendly_name": "", "summary": ""})

        # Set a schedule to update the sensor every however you want minutes
        self.run_every(self.update_sensor, self.datetime(), 3 * MINUTE )

    def refresh_headers(self):
        """Fetch new headers if they are older than 50 minutes."""
        current_time = time.time()
        if not self.headers or (current_time - self.headers_last_updated > 50 * MINUTE):
            self.log("Refreshing headers...")
            url = "https://www.sofiatraffic.bg/bg/trip/getAllStops"
            try:
                response = requests.post(url)
                response.raise_for_status()

                cookies = response.cookies
                sofia_traffic_session = cookies.get("sofia_traffic_session")
                x_xsrf_token = cookies.get("XSRF-TOKEN")
                x_xsrf_token_decoded = urllib.parse.unquote(x_xsrf_token)

                self.headers = {
                    "cookie": f"sofia_traffic_session={sofia_traffic_session}",
                    "accept": "application/json",
                    "content-type": "application/json",
                    "x-xsrf-token": x_xsrf_token_decoded,
                }
                self.headers_last_updated = current_time
                self.log("Headers refreshed successfully.")
            except requests.exceptions.RequestException as e:
                self.log(f"Error refreshing headers: {e}")
                self.headers = None

    def fetch_stop_name(self):
        """Fetch the name of the stop."""
        self.refresh_headers()
        if not self.headers:
            self.log("Headers not available, skipping stop name fetch.")
            return
        if self.stop_name is not None:
            self.log(f"Already got a name { self.stop_name }")
            return

        url = "https://www.sofiatraffic.bg/bg/trip/getAllStops"
        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()

            stops = response.json()
            for stop in stops:
                if stop.get("code") == self.stop_id:
                    self.stop_name = stop.get("name")
                    self.log(f"Found stop name: {self.stop_name}")
                    return
        except requests.exceptions.RequestException as e:
            self.log(f"Error fetching stop names: {e}")

        self.stop_name = None  # Default if not found

    def get_virtual_table(self, stop_id):
        """Fetch bus arrival times for a stop."""
        self.refresh_headers()
        if not self.headers:
            self.log("Headers not available, skipping request.")
            return None

        url = "https://www.sofiatraffic.bg/bg/trip/getVirtualTable"
        data = {"stop": stop_id}
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log(f"Error fetching virtual table: {e}")
            return None

    def update_sensor(self, kwargs):
        """Update the Home Assistant sensor with the latest bus data."""
        stop_data = self.get_virtual_table(self.stop_id)

        summary_list = []       
        if stop_data:
            lines = {}
            now = datetime.now()
            for key, value in stop_data.items():
                line_name = value.get("name", "Unknown Line")
                bus_times = [detail["t"] for detail in value.get("details", [])]
                lines[line_name] = bus_times

                # Convert minutes left to actual arrival time
                time_strings = []
                for minutes in bus_times:
                    arrival_time = now + timedelta(minutes=minutes)
                    arrival_time_str = arrival_time.strftime("%H:%M")  # 24-hour format
                    time_strings.append(f"{minutes} min ({arrival_time_str})")

                # Format summary for this line
                if time_strings:
                    summary_list.append(f"{line_name}: {', '.join(time_strings)}")

            # Final summary
            summary = "Last Updated: {0}\n".format(now.strftime("%H:%M:%S")) + "\n".join(summary_list)

            # Update the sensor in Home Assistant
            self.set_state(
                self.sensor_name,
                state="Updated",
                attributes={
                    "lines": lines,
                    "friendly_name": self.stop_name or "Bus Stop Info",
                    "summary": summary,
                },
            )
            self.log(f"Sensor {self.sensor_name} updated: {summary}")
        else:
            self.log(f"Failed to fetch data for stop ID {self.stop_id}")
            self.set_state(
                self.sensor_name,
                state="Error",
                attributes={
                    "lines": {},
                    "friendly_name": self.stop_name or "Bus Stop Info",
                },
            )
