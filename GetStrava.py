# /usr/local/bin/python3.9
# Pulls MY Strava Data for posts including "Half Dome" and creates a CSV sorted of the most height climed and distance gained
# todo: Pull from everyone in the club
    #  Average club distance for the day 
    #  Exclude anything with "EC"
    #  Better fuzzy matching of "Half Dome"
import os
import json
import logging
# import time
import re
from datetime import datetime
from distutils.log import debug

import gspread

from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

import pandas as pd
import requests

# Define logfile
LOG_FILENAME = datetime.now().strftime('./logs/GetStravaData_%a.log')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
# logging.basicConfig( level=logging.DEBUG,format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')


#Activity Name 
# substring = 'Half Dome'
pattern = re.compile(r'half\s*dome', re.IGNORECASE)


# Get credentials from environment variables
client_id = os.environ.get('STRAVA_CLIENT_ID')
client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')

response = requests.post(
    url='https://www.strava.com/oauth/token',
    data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
)
logging.info(response)

#Save response as json in new variable
new_strava_tokens = response.json()
strava_tokens = new_strava_tokens

#Loop through all activities
page = 1
url = "https://www.strava.com/api/v3/activities"
access_token = strava_tokens['access_token']
## Create the dataframe ready for the API call to store your activity data
activities = pd.DataFrame(
    columns = [
            "id",
            "name",
            "start_date_local",
            "type",
            "distance",
            "moving_time",
            "elapsed_time",
            "total_elevation_gain",
            "end_latlng",
            "external_id"
    ]
)
while True:
    
    # get page of activities from Strava
    r = requests.get(f"{url}?access_token={access_token}&per_page=200&page={page}")
    r = r.json()
    logging.info(r)
    # print(r)
    with open('athlete_activities.json', 'a') as outfile:
        json.dump(r, outfile)
# if no results then exit loop
    if (not r):
        break
    
    # otherwise add new data to dataframe
    for x in range(len(r)):
        if pattern.search(r[x]['name']):
            activities.loc[x + (page-1)*200,'id'] = r[x]['id']
            activities.loc[x + (page-1)*200,'name'] = r[x]['name']
            activities.loc[x + (page-1)*200,'start_date_local'] = r[x]['start_date_local']
            activities.loc[x + (page-1)*200,'type'] = r[x]['type']
            activities.loc[x + (page-1)*200,'distance'] = r[x]['distance']*0.000621371 # convert Meters to miles
            activities.loc[x + (page-1)*200,'moving_time'] = r[x]['moving_time']
            activities.loc[x + (page-1)*200,'elapsed_time'] = r[x]['elapsed_time']
            activities.loc[x + (page-1)*200,'total_elevation_gain'] = r[x]['total_elevation_gain']*3.28084 # convert Meters to feet
            activities.loc[x + (page-1)*200,'end_latlng'] = r[x]['end_latlng']
            activities.loc[x + (page-1)*200,'external_id'] = r[x]['external_id']
# increment page
    page += 1

# Load credentials from environment variable (GitHub secret)
credentials_json = os.environ['GOOGLE_SHEETS_CREDENTIALS']
credentials_json = credentials_json.replace('\n', ' ')
credentials_json_dict = json.loads(credentials_json)

try:
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json_dict, scope)
    client = gspread.authorize(credentials)
except json.JSONDecodeError as e:
    logging.error(f"JSON Decode Error: {e}")
    exit(1)  # This will exit the script if an error occurs
except Exception as e:
    logging.error(f"An error occurred: {e}")
    exit(1)  # This will exit the script if an error occurs

# Open the Google Sheets document
spreadsheet_key = os.environ['GOOGLE_SHEETS_SPREADSHEET_KEY']
if not spreadsheet_key:
    print("Spreadsheet key not found in environment variables")
    exit(1)

spreadsheet = client.open_by_key(spreadsheet_key)

# Get references to the existing sheets by title
try:
    elevation_sheet = spreadsheet.worksheet("Elevation")
    distance_sheet = spreadsheet.worksheet("Distance")
except gspread.exceptions.WorksheetNotFound as e:
    print(f"Worksheet not found: {e}")
    # elevation_sheet = spreadsheet.add_worksheet(title="Elevation", rows="100", cols="6")
    # distance_sheet = spreadsheet.add_worksheet(title="Distance", rows="100", cols="6")
    exit(1)

# Read existing data into dataframes
existing_elevation_data = pd.DataFrame(elevation_sheet.get_all_records())
existing_distance_data = pd.DataFrame(distance_sheet.get_all_records())

# # Create separate dataframes for elevation and distance leaderboard
elevation_leaderboard_df = activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='total_elevation_gain',ascending=False)
distance_leaderboard_df = activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False)

# Concatenate new data to existing data
updated_elevation_data = pd.concat([existing_elevation_data, elevation_leaderboard_df], ignore_index=True)
updated_distance_data = pd.concat([existing_distance_data, distance_leaderboard_df], ignore_index=True)

# Clear the sheets before uploading the updated data
elevation_sheet.clear()
distance_sheet.clear()

# Upload the updated dataframes back to the sheets
set_with_dataframe(elevation_sheet, updated_elevation_data, include_index=False, include_column_header=True, resize=True)
set_with_dataframe(distance_sheet, updated_distance_data, include_index=False, include_column_header=True, resize=True)

logging.info('GetStrava.py has run')