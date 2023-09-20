# /usr/local/bin/python3.9
# Pulls MY Strava Data for posts including "Half Dome" and creates a CSV sorted of the most height climed and distance gained
# todo: Pull from everyone in the club
    #  Average club distance for the day 
    #  Exclude anything with "EC"
    #  Better fuzzy matching of "Half Dome"
import os
import json
import logging
import time
from datetime import datetime
from distutils.log import debug

import gspread

from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

import pandas as pd
import requests

if not os.path.exists('./data'):
    os.makedirs('./data')

# Define logfile
LOG_FILENAME = datetime.now().strftime('./logs/GetStravaData_%a.log')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
# logging.basicConfig( level=logging.DEBUG,format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

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
logging.info(print(response))

#Save response as json in new variable
new_strava_tokens = response.json()

strava_tokens = new_strava_tokens

#Activity Name 
substring = 'Half Dome'

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
    r = requests.get(url + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))
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
        if r[x]['name'].find(substring) != -1:
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
logging.info('Elevation Leaderboard')
logging.info(activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='total_elevation_gain',ascending=False))
# print("Creating HD_Elevation_Leaderboard.csv...")
activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='total_elevation_gain',ascending=False).to_csv('./data/HD_Elevation_Leaderboard.csv', header=False)

logging.info('Distance Leaderboard')
logging.info(activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False))
# print("Creating HD_Distance_Leaderboard.csv...")
activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False).to_csv('./data/HD_Distance_Leaderboard.csv', header=False)
# # -- ------------------------------------------------------------------------------------------------------
# # Load credentials from environment variable (GitHub secret)
# credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
credentials_json = os.environ['GOOGLE_SHEETS_CREDENTIALS']
credentials_json = credentials_json.replace('\n', ' ')
credentials_json = credentials_json.replace('\n', ' ')
print(credentials_json)

credentials_json_dict = json.loads(credentials_json)

try:
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json_dict, scope)
    client = gspread.authorize(credentials)
except json.JSONDecodeError as e:
    print(f"JSON Decode Error: {e}")
    exit(1)  # This will exit the script if an error occurs
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)  # This will exit the script if an error occurs

# Open the Google Sheets document
spreadsheet_key = '1416YvyZiCqt3AF2LaAhguj4jLxnkXQIBdFbHsRcX32Y'  # From the URL of your Google Sheets document

# Creating a new worksheets
spreadsheet = client.open_by_key(spreadsheet_key)
elevation_sheet = spreadsheet.add_worksheet(title="Elevation", rows="100", cols="26")
distance_sheet = spreadsheet.add_worksheet(title="Distance", rows="100", cols="26")

# Create separate dataframes for elevation and distance leaderboard
elevation_leaderboard_df = activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='total_elevation_gain',ascending=False)
distance_leaderboard_df = activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False)

# Upload new data to Google Sheets (replace `sheet` with the appropriate worksheet object)
set_with_dataframe(elevation_sheet, elevation_leaderboard_df, row=1, col=1, include_index=False, include_column_header=True, resize=False)
set_with_dataframe(distance_sheet, distance_leaderboard_df, row=1, col=1, include_index=False, include_column_header=True, resize=False)

logging.info('GetStravaData.py has run')