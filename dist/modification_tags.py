import requests
import json
import urllib3
import csv
import os
from requests_ntlm import HttpNtlmAuth
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Logger:
    def __init__(self, min_level=logging.DEBUG, log_base_filename="application_log", log_directory=None, max_bytes=1024*1024, backup_count=1):
        self._min_level = min_level
        self._log_base_filename = log_base_filename
        self._max_bytes = max_bytes
        self._backup_count = backup_count

        if log_directory is None:
            log_directory = os.path.dirname(os.path.abspath(__file__))
            log_directory = os.path.join(log_directory, "logs")

        log_filename = f"{log_base_filename}.log"

        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        self._log_file_path = os.path.join(log_directory, log_filename)

        # Create a rotating file handler
        handler = RotatingFileHandler(self._log_file_path, maxBytes=self._max_bytes, backupCount=self._backup_count)
        handler.setFormatter(logging.Formatter('[%(levelname)s]\t%(asctime)s - %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p'))
        handler.setLevel(self._min_level)

        self.logger = logging.getLogger()
        self.logger.setLevel(self._min_level)
        self.logger.addHandler(handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

class VisionApi:
    def __init__(self, url_endpoint, username, password, logger):
        self.url_endpoint = url_endpoint
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # Be cautious with this in a production environment
        self.logger = logger

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
            self.logger.debug(f"Making {method} request to {api_url}")
            if method.upper() == 'GET':
                response = self.session.get(api_url, auth=auth, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(api_url, auth=auth, headers=headers, data=json.dumps(body))
            else:
                raise ValueError("Unsupported HTTP method provided.")

            # Handle responses
            if response.status_code == 200:
                self.logger.info(f"Successful {method} request to {api_url}")
                return response.json()
            elif response.status_code == 204:
                self.logger.info(f"204 No Content: No content returned from the API: {api_url}")
                return None
            else:
                self.logger.error(f"{response.status_code} Error: {response.text} from the API: {api_url}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection Error while accessing the API: {api_url}: {e}")
            return None

    def get_pi_vision_api(self, custom_url):
        return self._request("GET", custom_url)
    
    def put_pi_vision_api(self, custom_url, body):
        return self._request("PUT", custom_url, body)

def read_display_ids(filename, logger):
    """Read display IDs from a file and return as a list."""
    try:
        with open(filename, 'r') as file:
            content = file.read().strip()
        logger.info(f"Read display IDs from {filename}")
        return content.split(',')
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return []

def save_tags_to_csv(display_id, tags, logger):
    """Save tags to a CSV file named after the display ID."""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    csv_filename = os.path.join(output_dir, f"{display_id}.csv")
    try:
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Tag'])  # Write header
            for tag in tags:
                writer.writerow([tag])
        logger.info(f"Tags saved to {csv_filename}")
    except Exception as e:
        logger.error(f"Error saving tags to CSV file {csv_filename}: {e}")

def save_data_to_json(display_id, data, logger):
    """Save data to a JSON file named after the display ID."""
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    json_filename = os.path.join(backup_dir, f"{display_id}.json")
    try:
        with open(json_filename, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=4)
        logger.info(f"Data saved to {json_filename}")
    except Exception as e:
        logger.error(f"Error saving data to JSON file {json_filename}: {e}")

def read_credentials(filename, logger):
    """Read username and password from a JSON file."""
    try:
        with open(filename, 'r') as file:
            credentials = json.load(file)
        logger.info(f"Read credentials from {filename}")
        return credentials['server'], credentials['username'], credentials['password']
    except FileNotFoundError:
        logger.error(f"Credentials file not found: {filename}")
        exit(1)
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from the credentials file: {filename}")
        exit(1)

def read_modification_values(filename, logger):
    """Read modification values from a CSV file."""
    try:
        modification_values = {}
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'name' in row and 'newname' in row and 'pointid' in row:
                    modification_values[row['name']] = (row['newname'], row['pointid'])
                else:
                    logger.warning(f"Row missing required columns: {row}")
        logger.info(f"Read modification values from {filename}")
        return modification_values
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        exit(1)
    except csv.Error as e:
        logger.error(f"Error reading CSV file {filename}: {e}")
        exit(1)

def modify_data_source(data_source, modifications, logger):
    """Modify the content of data_source as needed."""
    partes = data_source.split('?')
    if len(partes) > 2:
        subpartes = partes[1].split('\\')
        tag = subpartes[1].replace('"',"").strip()
        keys = list(modifications.keys())
        if tag in keys:
            newname, pointid = modifications[tag]
            subpartes[0] = newname
            subpartes[1] = pointid
            partes[3] = '?'.join(subpartes)
            novo_data_source = '\\'.join(partes)
            logger.debug(f"Modified data source: OLD: {data_source}, NEW: {novo_data_source}")
            return novo_data_source, tag
        else:
            logger.debug(f"Data source not found in modifications: {data_source}")
            return data_source, None
    return data_source, None

if __name__ == "__main__":
    logger = Logger()

    # Determine the path to the credentials and display IDs files
    input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)

    credentials_file = os.path.join(input_dir, "credentials.json")
    display_ids_file = os.path.join(input_dir, "display_ids.txt")
    modification_values_file = os.path.join(input_dir, "newtags.csv")

    # Read credentials from the file
    server, username, password = read_credentials(credentials_file, logger)

    # Set up the Vision API object
    api = VisionApi(f"https://{server}/PIVision/Utility/api/v1", username, password, logger)

    # Read display IDs from the file
    display_ids = read_display_ids(display_ids_file, logger)

    # Read modification values from the CSV file
    modifications = read_modification_values(modification_values_file, logger)

    for display_id in display_ids:
        data = api.get_pi_vision_api(f"displays/{display_id}/export")

        save_data_to_json(display_id, data, logger)
        tags = []  
        if data and 'Display' in data and 'Symbols' in data['Display']:
                     
            for symbol in data['Display']['Symbols']:
                if 'DataSources' in symbol:
                    for i, data_source in enumerate(symbol['DataSources']):
                        try:
                            novo_data_source, tag = modify_data_source(data_source, modifications, logger)
                            if tag:
                                tags.append(tag)
                            symbol['DataSources'][i] = novo_data_source
                        except IndexError:
                            logger.error(f"IndexError processing data source: {data_source}")
                            continue

            # Save tags to a CSV file named after the display ID
            save_tags_to_csv(display_id, tags, logger)
        
        else:
            logger.warning(f"Unexpected data structure returned for display ID {display_id}")

        if tags:
            # Update the display with the modified data  
            data["DuplicateDisplayWriteBehavior"] = "Overwrite" #"Append"         
            api.put_pi_vision_api(f"displays", data)
        else:
            logger.info(f"No modifications needed for display ID {display_id}")


    # Pause to keep the console window open
    input("Press Enter to exit...")
