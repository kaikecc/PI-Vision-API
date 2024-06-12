<!-- Watermark CSS -->
<style>
.watermark {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-45deg);
  font-size: 5em;
  color: rgba(128, 0, 128, 0.2);
  opacity: 0.5;
  z-index: 1;
  pointer-events: none;
}
</style>

# How to Search Tags in PI Vision using Python

<div class="watermark">kaikecastro</div>
This script demonstrates how to interact with the PI Vision API using Python. It specifically focuses on retrieving PI tags associated with a specific display.

## Features:

* **Import Libraries:** Imports necessary Python libraries like requests, json, and urllib3 for API communication, as well as requests_ntlm for NTLM authentication.
  
* **VisionApi Class:** Defines a VisionApi class that handles API requests and provides methods for GET, POST, PUT, and DELETE operations.
  
* **NTLM Authentication:** Uses HttpNtlmAuth for NTLM authentication against the PI Vision server.
  
* **Retrieving Display Data:** Fetches display data (including PI tags) based on a provided display ID using the get_pi_vision_api method.

* **Extracting PI Tags:** Extracts PI tags from the display data and prints them to the console.

## Usage:

1. Replace Placeholders: Modify the following placeholders in the code:
   
   * ``https://server/PIVision/Utility/api/v1``: Replace with the PI Vision API endpoint URL.
   * ``username``: Replace with your PI Vision username.
   * ``password``: Replace with your PI Vision password.
   * ``0000``: Replace with the desired display ID.
  
2. Execute Script: Run the Python script.   
3. Output: The script will print the extracted PI tags from the specified display to the console.


## Notes:

   * This script relies on NTLM authentication, which is common in PI Vision environments.
   * The script disables SSL certificate verification for simplicity. This is not recommended in production environments.
   * You can adapt the get_pi_vision_api method to retrieve different API data based on your needs.
   * Consider using a library like requests_cache to cache API responses for performance optimization.
  
## Future Enhancements:

* Error Handling: Improve error handling and provide more specific error messages.
* API Data Retrieval: Extend the script to retrieve other PI Vision data, such as historical data or asset information.
* GUI Interface: Create a GUI interface for easier user interaction.
  
This script serves as a basic starting point for interacting with the PI Vision API. You can modify and extend it to create more complex and tailored solutions.