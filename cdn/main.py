import requests
import json
import os

# The version of the CDN, this should be updated when the CDN data is updated so the client can check if it has the latest version
ADVENTURELOG_CDN_VERSION = 'v0.0.1'

# https://github.com/dr5hn/countries-states-cities-database/tags
COUNTRY_REGION_JSON_VERSION = 'v2.5' # Test on past and latest versions to ensure that the data schema is consistent before updating

def makeDataDir():
    """
    Creates the data directory if it doesn't exist
    """
    path = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(path):
        os.makedirs(path)

def saveCdnVersion():
    """
    Saves the CDN version to a JSON file so the client can check if it has the latest version
    """
    path = os.path.join(os.path.dirname(__file__), 'data', 'version.json')
    with open(path, 'w') as f:
        json.dump({'version': ADVENTURELOG_CDN_VERSION}, f)
        print('CDN Version saved')

def downloadCountriesStateCities():
    """
    Downloads the countries, states and cities data from the countries-states-cities-database repository
    """
    res = requests.get(f'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{COUNTRY_REGION_JSON_VERSION}/json/countries%2Bstates%2Bcities.json')

    path = os.path.join(os.path.dirname(__file__), 'data', f'countries_states_cities.json')

    with open(path, 'w') as f:
        f.write(res.text)
        print('Countries, states and cities data downloaded successfully')

def saveCountryFlag(country_code, name):
    """
    Downloads the flag of a country and saves it in the data/flags directory
    """
    # For standards, use the lowercase country_code
    country_code = country_code.lower()
    # Save the flag in the data/flags directory
    flags_dir = os.path.join(os.path.dirname(__file__), 'data', 'flags')

    # Check if the flags directory exists, if not, create it
    if not os.path.exists(flags_dir):
        os.makedirs(flags_dir)

    # Check if the flag already exists in the media folder
    flag_path = os.path.join(flags_dir, f'{country_code}.png')
    if os.path.exists(flag_path):
        # remove the flag if it already exists
        os.remove(flag_path)
        print(f'Flag for {country_code} ({name}) removed')

    res = requests.get(f'https://flagcdn.com/h240/{country_code}.png'.lower())
    if res.status_code == 200:
        with open(flag_path, 'wb') as f:
            f.write(res.content)
        print(f'Flag for {country_code} downloaded')
    else:
        print(f'Error downloading flag for {country_code} ({name})')

def saveCountryFlags():
    """
    Downloads the flags of all countries and saves them in the data/flags directory
    """
    # Load the countries data
    with open(os.path.join(os.path.dirname(__file__), 'data', f'countries_states_cities.json')) as f:
        data = json.load(f)

    for country in data:
        country_code = country['iso2']
        name = country['name']
        saveCountryFlag(country_code, name)

# Run the functions
print('Starting CDN update')
makeDataDir()
saveCdnVersion()
downloadCountriesStateCities()
saveCountryFlags()
print('CDN update complete')