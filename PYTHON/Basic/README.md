# PI Vision API

## Overview

The VisionApi class provides methods to interact with the PI Vision API, specifically for retrieving and updating PI Vision display data. This class uses Kerberos authentication to securely access the PI Vision API.

## Prerequisites

* Python 3.x
* Required Python libraries: requests, urllib3, requests_kerberos, json, logging
* Kerberos authentication configured on the client machine

## Installation

 To install the required Python libraries, you can use pip:

```bash
pip install requests urllib3 requests_kerberos
```

## Usage

### Initialization

Create an instance of the VisionApi class by providing the base URL of the PI Vision API endpoint.

```python
from vision_api import VisionApi

url_endpoint = "https://servername/PIVision/Utility/api/v1"
api = VisionApi(url_endpoint)
```

### Retrieving PI Vision Data

To retrieve data from the PI Vision API, use the get_PiVisionApi method with the specific API endpoint.

```python
custom_url = "displays/{displayId}/export"
response_get = api.get_PiVisionApi(custom_url)
```

### Updating PI Vision Data

To update data on the PI Vision API, use the update_PiVisionApi method with the specific API endpoint and the data to be updated.

```python
response_get["Display"]["Owner"] = "user_owner"
response_get["DuplicateDisplayWriteBehavior"] = "Overwrite"
custom_url = "displays"
response_update = api.update_PiVisionApi(custom_url, response_get)
```

### Methods

**get_PiVisionApi(custom_url)**

Retrieves data from the PI Vision API.

* Parameters:

    * custom_url (str): The specific API endpoint to retrieve data from.
Returns:

    * dict: The JSON response from the API or an empty dictionary if an error occurs.
update_PiVisionApi(custom_url, body)
Updates data on the PI Vision API.

* Parameters:

    * custom_url (str): The specific API endpoint to update data on.
body (dict): The data to be updated in JSON format.

* Returns:

  * dict: The JSON response from the API or an empty dictionary if an error occurs.

### Error Handling

The VisionApi class handles various HTTP status codes and logs appropriate error messages:

* 200: Success
* 204: Success but no content
* 400: Invalid request
* 401: Unauthorized
* 404: Resource not found
* 503: Service unavailable

In case of connection errors, the error message is logged, and an empty dictionary is returned.

Logging
Logging is used to capture warnings and errors. Ensure that logging is appropriately configured in your environment to capture these messages.

Example

```python
if __name__ == "__main__":
    url_endpoint = "https://servername/PIVision/Utility/api/v1"
    api = VisionApi(url_endpoint)

    # Get one display
    display_id = "0000"
    custom_url = f"displays/{display_id}/export"
    response_get = api.get_PiVisionApi(custom_url)
    
    response_get["Display"]["Owner"] = "user_owner"
    response_get["DuplicateDisplayWriteBehavior"] = "Overwrite"
    custom_url = "displays"
    response_update = api.update_PiVisionApi(custom_url, response_get)
    print(response_update)
```

## Notes

The code disables SSL warnings using urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning). This is generally not recommended for production environments.

Ensure that the Kerberos authentication is correctly set up on the client machine to avoid authentication issues.