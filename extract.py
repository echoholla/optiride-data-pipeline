import json   # STORING THE DATA IN THE RAW STAGING AREA
import os     # CREATING DIR AND PATHS

import requests   # MAKING A CONNECTION TO API
import yaml       # CONFIGURATION FILE DATA

from logger import get_logger

logger = get_logger("Extract")

logger.info("Collecting URL for target APIs...")

# API endpoints
BIKE_API = "https://api.citybik.es/v2/networks/citi-bike-nyc"
WEATHER_API = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=40.71348&longitude=-74.006&"
    "hourly=temperature_2m,precipitation,wind_speed_10m,cloudcover,relativehumidity_2m"
)

def extract():
    # load config file
    with open("./config.yaml", "r") as f:
        config = yaml.safe_load(f)

    raw_dir = config["storage"]["raw"]
    
    # Make sure the raw folder exists
    os.makedirs(raw_dir, exist_ok=True)

    logger.info("Extracting bike and weather data for New York...")

    # Fetch data from APIs
    bike_data = requests.get(BIKE_API).json()
    weather_data = requests.get(WEATHER_API).json()

    # Save raw data to files
    with open(os.path.join(raw_dir, "bike_raw.json"), "w") as f:
        json.dump(bike_data, f, indent=4)

    with open(os.path.join(raw_dir, "weather_raw.json"), "w") as f:
        json.dump(weather_data, f, indent=4)

    logger.info("Stage 1 Extract complete. Data stored in landing zone.")

if __name__ == "__main__":
    extract()
