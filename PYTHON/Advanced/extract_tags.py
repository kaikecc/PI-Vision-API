import requests
import json
import urllib3
import csv
import os
from requests_ntlm import HttpNtlmAuth

#pyinstaller --onefile --name="Extract PI Tags" --icon="PYTHON\Advanced\extract.ico" "PYTHON\Advanced\extract_tags.py"

# https://server/PIVision/Utility/api/v1/displays

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class VisionApi:
    def __init__(self, url_endpoint, username, password):
        self.url_endpoint = url_endpoint
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # Be cautious with this in a production environment

    def _request(self, method, custom_url, body=None):
        """
        Generic request method to handle all types of HTTP requests.
        """
        # Set up authentication and headers
        auth = HttpNtlmAuth(self.username, self.password)
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }

        # Construct the full API URL
        api_url = f"{self.url_endpoint}/{custom_url}"

        # Try to make the HTTP request
        try:
            if method.upper() == 'GET':
                response = self.session.get(api_url, auth=auth, headers=headers)
            else:
                raise ValueError("Unsupported HTTP method provided.")

            # Handle responses
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                print(f"204 No Content: No content returned from the API: {api_url}")
                return None
            else:
                print(f"{response.status_code} Error: {response.text} from the API: {api_url}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Connection Error while accessing the API: {api_url}: {e}")
            return None

    def get_pi_vision_api(self, custom_url):
        return self._request("GET", custom_url)

def read_display_ids(filename):
    """Read display IDs from a file and return as a list."""
    with open(filename, 'r') as file:
        content = file.read().strip()
    return content.split(',')

def save_tags_to_csv(display_id, tags):
    """Save tags to a CSV file named after the display ID."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = f"C://Temp//{display_id}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Tag'])  # Write header
        for tag in tags:
            writer.writerow([tag])
    print(f"Tags saved to {csv_filename}")

def read_credentials(filename):
    """Read username and password from a JSON file."""
    with open(filename, 'r') as file:
        credentials = json.load(file)
    return credentials['server'], credentials['username'], credentials['password']

if __name__ == "__main__":

    # Determine the path to the credentials and display IDs files
    #script_dir = os.path.dirname(os.path.abspath(__file__))
    
    credentials_file =  "C://Temp//credentials.json"

    print(f"Reading credentials from {credentials_file}")

    # Read credentials from the file
    try:
        server, username, password = read_credentials(credentials_file)
    except FileNotFoundError:
        print(f"Credentials file not found: {credentials_file}")
        #exit(1)
        input("Press Enter to exit...")

    # Set up the Vision API object
    api = VisionApi(f"https://{server}/PIVision/Utility/api/v1", username, password)

    # Determine the path to the display_ids.txt file
    display_ids_file = "C://Temp//display_ids.txt"

    # Read display IDs from the file
    try:
        display_ids = read_display_ids(display_ids_file)
    except FileNotFoundError:
        print(f"File not found: {display_ids_file}")
        #exit(1)
        input("Press Enter to exit...")

    for display_id in display_ids:
        data = api.get_pi_vision_api(f"displays/{display_id}/export")

        if data and 'Display' in data and 'Symbols' in data['Display']:
            tags = []
            for symbol in data['Display']['Symbols']:
                if 'DataSources' in symbol:
                    for data_source in symbol['DataSources']:
                        try:
                            tag = data_source.split('\\')[3].split('?')[0]
                            tags.append(tag)
                        except IndexError:
                            continue

            # Save tags to a CSV file named after the display ID
            save_tags_to_csv(display_id, tags)
        else:
            print(f"Unexpected data structure returned for display ID {display_id}")

    # Pause to keep the console window open
    input("Press Enter to exit...")
