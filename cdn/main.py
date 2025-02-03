import requests
import json
import os

# https://github.com/dr5hn/countries-states-cities-database/tags
COUNTRY_REGION_JSON_VERSION = 'v2.5' # Should match the version stated in the settings.py file of AdventureLog

def downloadCountriesStateCities():
    res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/json/countries%2Bstates%2Bcities.json')

def downloadGeojson(iso_code=None, region_name=None):
    """
    Download geojson data for a specific region using the Overpass API.
    :param iso_code: ISO 3166-2 code for the region (e.g. "US-CT")
    :param region_name: Name of the region (e.g. "Connecticut")
    :return: Geojson data for the region
    """
    base_url = "https://overpass-api.de/api/interpreter"
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(__file__)

    # Ensure the ./data directory exists
    data_dir = os.path.join(script_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Set the path for the geojson file
    geojson_path = os.path.join(data_dir, "geojson.json")

    if iso_code:
        query = f'[out:json];relation["boundary"="administrative"]["admin_level"="4"]["ISO3166-2"="{iso_code}"];out body;way(r);(._;>;);out geom;'
        response = requests.post(base_url, data=query)
        if response.ok and response.json().get("elements"):
            data = response.json()
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return data
    
    if region_name:
        query = f'[out:json];relation["boundary"="administrative"]["admin_level"="4"]["name"="{region_name}"];out body;way(r);(._;>;);out geom;'
        response = requests.post(base_url, data=query)
        if response.ok and response.json().get("elements"):
            data = response.json()
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return data

    return None  # No results found

# Example usage
data = downloadGeojson(iso_code="US-CT", region_name="Connecticut")

if data:
    print(f"Region data found and saved to {os.path.join(os.path.dirname(__file__), 'data', 'geojson.json')}!")
else:
    print("No region data found.")
