# /usr/local/bin/python3.9
# Pulls MY Strava Data for posts including "Half Dome" and logs to a google sheeet
# todo: Pull from everyone in the club
    #  Average club distance for the day 
    #  Exclude anything with "EC"
    #  Better fuzzy matching of "Half Dome"
import os
import json
import logging
# import time
import re
from datetime import datetime, date
from distutils.log import debug

import gspread

from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

import pandas as pd
import requests

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d in function %(funcName)s] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

#Activity Name 
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
logger.debug(response)

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
    logger.debug(r)
    # print(r)
    with open('athlete_activities.json', 'a') as outfile:
        logger.debug(json.dump(r, outfile))
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

# Data Cleanup/Manuplation
# Convert 'start_date_local' to datetime format
activities['start_date_local'] = pd.to_datetime(activities['start_date_local'])

# Create 'simple_date' column with date in MM/DD/YYYY format
activities['simple_date'] = activities['start_date_local'].dt.strftime('%m/%d/%Y')

# Create 'Asterisk' column based on me flagging a run as having an "EC" or Starting before Start time
activities['asterisk'] = ((activities['name'].str.contains(r'\sEC$', regex=True, case=False)) | 
                          (activities['start_date_local'].dt.time < pd.to_datetime('05:20:00').time()))

# Convert 'asterisk' column to boolean type
activities['asterisk'] = activities['asterisk'].astype(bool)

# Extract substring between "dome:" and " Q" to create 'QiC' column
activities['QiC'] = activities['name'].str.extract(':(.*?) Q', flags=re.IGNORECASE)
activities['QiC'] = activities['QiC'].str.strip()
activities.loc[activities['QiC'] == 'YHC', 'QiC'] = 'Ramsay'

# -- ----------------------------------------------------------------------------------------
# Get Club Activities

# /clubs/{id}/activities
#Loop through all activities
page = 1
url = "https://www.strava.com/api/v3/clubs"

access_token = strava_tokens['access_token']
# 'id': 326452, 'resource_state': 2, 'name': 'F3 Carpex' fetched from above "Get Athlete Club"
Clubid = '326452'

# Create the dataframe ready for the API call to store your activity data
club_activities = pd.DataFrame(
    columns = [
            # "id",
            "athlete",
            "name",
            "distance",
            "moving_time",
            "elapsed_time",
            "total_elevation_gain"
    ]
)


while page <= 12 :
    # https://www.strava.com/api/v3/clubs/{id}/activities?page=&per_page=" "Authorization: Bearer [[token]]"
    logger.debug(f"{Clubid} + '/activities'  + '&per_page=200' + '&{page}=' + str({page})")
    # r = requests.get(url + '/' + Clubid + '/activities'  + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))
    r = requests.get(f"{url}/{Clubid}/activities?access_token={access_token}&per_page=200&page={str(page)}")
    if r.status_code == 400:
        logger.error(r.content)

    r = r.json()
    with open('club_activities.json', 'a') as outfile:
        logger.debug(json.dump(r, outfile))

    if (not r):
        break
    
    # otherwise add new data to dataframe
    logger.debug('line:',x)
    for x in range(len(r)):
        logger.debug(f"Debugging Club activities: {r[x]['athlete']['firstname']} {r[x]['athlete']['lastname']} activity: {r[x]['name']}")
        try:
            if pattern.search(r[x]['name']):
                # club_activities.loc[x + (page-1)*200,'id'] = str(page) + str(r[x])
                club_activities.loc[x + (page-1)*200,'athlete'] = r[x]['athlete']['firstname'] + ' ' + r[x]['athlete']['lastname']
                club_activities.loc[x + (page-1)*200,'name'] = r[x]['name']
                club_activities.loc[x + (page-1)*200,'distance'] = r[x]['distance']*0.000621371 # convert Meters to miles
                club_activities.loc[x + (page-1)*200,'moving_time'] = r[x]['moving_time']
                club_activities.loc[x + (page-1)*200,'elapsed_time'] = r[x]['elapsed_time']
                club_activities.loc[x + (page-1)*200,'total_elevation_gain'] = r[x]['total_elevation_gain']*3.28084 # convert Meters to feet
        except KeyError as e:
            logger.error(f"KeyError: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

    page += 1
logger.info("{substring} Activities")

# Create 'simple_date' column with date in MM/DD/YYYY format
club_activities['date'] = date.today()

# club_activities[['athlete','name','distance','moving_time','elapsed_time','total_elevation_gain']].sort_values(by='distance',ascending=False).to_csv('PAX_HD_Excercises.csv', mode='a', header=False)
# -- ----------------------------------------------------------------------------------------

# Load credentials from environment variable (GitHub secret)
credentials_json = os.environ['GOOGLE_SHEETS_CREDENTIALS']
credentials_json = credentials_json.replace('\n', ' ')
credentials_json_dict = json.loads(credentials_json)

try:
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json_dict, scope)
    client = gspread.authorize(credentials)
except json.JSONDecodeError as e:
    logger.error(f"JSON Decode Error: {e}")
    exit(1)  # This will exit the script if an error occurs
except Exception as e:
    logger.error(f"An error occurred: {e}")
    exit(1)  # This will exit the script if an error occurs

# Open the Google Sheets document
spreadsheet_key = os.environ['GOOGLE_SHEETS_SPREADSHEET_KEY']
if not spreadsheet_key:
    logger.error("Spreadsheet key not found in environment variables")
    exit(1)

spreadsheet = client.open_by_key(spreadsheet_key)

# Get references to the existing sheets by title
try:
    elevation_sheet = spreadsheet.worksheet("Ramsays Records")
    club_sheet = spreadsheet.worksheet("Club Activities")
except gspread.exceptions.WorksheetNotFound as e:
    logger.error(f"Worksheet not found: {e}")
    # elevation_sheet = spreadsheet.add_worksheet(title="Elevation", rows="100", cols="6")
    # distance_sheet = spreadsheet.add_worksheet(title="Distance", rows="100", cols="6")
    exit(1)

# Read existing data into dataframes
try:
    sheet_records = elevation_sheet.get_all_records()
    if sheet_records:
        existing_elevation_data = pd.DataFrame(sheet_records)
    else:
        existing_elevation_data = pd.DataFrame()  # or set up a DataFrame with appropriate columns but no data
except IndexError as e:
    logger.error(f"Error reading data from the sheet: {e}")
    # Handle the error (e.g., skip processing this sheet or initialize an empty DataFrame)

# Read existing data into dataframes
try:
    sheet_records = club_sheet.get_all_records()
    if sheet_records:
        existing_club_data = pd.DataFrame(sheet_records)
    else:
        existing_club_data = pd.DataFrame()  # or set up a DataFrame with appropriate columns but no data
except IndexError as e:
    logger.error(f"Error reading data from the sheet: {e}")
    # Handle the error (e.g., skip processing this sheet or initialize an empty DataFrame)
    

# existing_elevation_data = pd.DataFrame(elevation_sheet.get_all_records())
# existing_club_data = pd.DataFrame(club_sheet.get_all_records())

# # Create separate dataframes for Club and Ramsay data
elevation_leaderboard_df = activities[['name','start_date_local','distance','total_elevation_gain','simple_date','asterisk','QiC']].sort_values(by='total_elevation_gain',ascending=False)
club_leaderboard_df = club_activities[['date','athlete','name','distance','moving_time','elapsed_time','total_elevation_gain']].sort_values(by='distance',ascending=False)

# Concatenate new data to existing data
updated_elevation_data = pd.concat([existing_elevation_data, elevation_leaderboard_df], ignore_index=True)
updated_club_data = pd.concat([existing_club_data, club_leaderboard_df], ignore_index=True)

# fix rounding issue on distance
elevation_leaderboard_df['distance'] = elevation_leaderboard_df['distance'].apply(lambda x: round(x, 7) if pd.notnull(x) else x)
club_leaderboard_df['distance'] = club_leaderboard_df['distance'].apply(lambda x: round(x, 7) if pd.notnull(x) else x)

# elevation_leaderboard_df['distance'] = elevation_leaderboard_df['distance'].round(7)
# club_leaderboard_df['distance'] = club_leaderboard_df['distance'].round(7)

# De-duplicate keeping latest
updated_elevation_data = updated_elevation_data.drop_duplicates(subset=['name','simple_date'],keep='last')
updated_club_data = updated_club_data.drop_duplicates(subset=['athlete','name','distance','moving_time','elapsed_time','total_elevation_gain'],keep='last')

logger.info(updated_elevation_data[updated_elevation_data.duplicated(subset=['name', 'simple_date','distance','total_elevation_gain'], keep=False)])
logger.info(updated_club_data[updated_club_data.duplicated(subset=['athlete', 'name','distance','total_elevation_gain'], keep=False)])

# Clear the sheets before uploading the updated data
elevation_sheet.clear()
club_sheet.clear()

# Upload the updated dataframes back to the sheets
set_with_dataframe(elevation_sheet, updated_elevation_data, include_index=False, include_column_header=True, resize=True)
set_with_dataframe(club_sheet, updated_club_data, include_index=False, include_column_header=True, resize=True)

logger.info('GetStrava.py has run')