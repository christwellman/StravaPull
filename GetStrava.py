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
# Save new tokens to file
    # with open('strava_tokens.json', 'w') as outfile:
    #     json.dump(new_strava_tokens, outfile)
#Use new Strava tokens from now
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

logging.info('Distnace Leaderboard')
logging.info(activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False))
# print("Creating HD_Distance_Leaderboard.csv...")
activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False).to_csv('./data/HD_Distance_Leaderboard.csv', header=False)
# # -- ------------------------------------------------------------------------------------------------------
# Load credentials from environment variable (GitHub secret)
import json

# ... other parts of your script

# Load credentials from environment variable (GitHub secret)
credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
print(credentials_json)

credentials_json = credentials_json.replace('\n', '\\n')

try:
    # Now try to convert the modified string to a dictionary
    credentials_json_dict = json.loads(credentials_json)
except json.JSONDecodeError as e:
    # If there's still an error, print it to get more information
    print(f"JSON Decode Error: {e}")
    
# Use credentials to authenticate with the Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json_dict, scope)
client = gspread.authorize(credentials)

# Open the Google Sheets document
spreadsheet_key = '1416YvyZiCqt3AF2LaAhguj4jLxnkXQIBdFbHsRcX32Y'  # From the URL of your Google Sheets document
sheet = client.open_by_key(spreadsheet_key).sheet1

# Convert your data frames to records (list of dictionaries) for easy uploading
elevation_leaderboard_records = activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='total_elevation_gain',ascending=False).to_dict('records')
distance_leaderboard_records = activities[['name','start_date_local','distance','total_elevation_gain']].sort_values(by='distance',ascending=False).to_dict('records')

# Clear existing data in the sheets ?
# sheet.clear()

# Upload new data to Google Sheets
sheet.insert_rows(elevation_leaderboard_records, 1)
# If you have multiple sheets, open them by index or title and insert the data similarly

# # -- ------------------------------------------------------------------------------------------------------
# #Get athlete club
# page = 1
# url = "https://www.strava.com/api/v3/athlete/clubs"history
#             "member_count",
#             "dimensions"
#     ]
# )


# r = requests.get(url + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))
# r = r.json()

# for x in range(len(r)):
#     clubs.loc[x + (page-1)*200,'id'] = r[x]['id']
#     clubs.loc[x + (page-1)*200,'resource_state'] = r[x]['resource_state']
#     clubs.loc[x + (page-1)*200,'name'] = r[x]['name']
#     clubs.loc[x + (page-1)*200,'member_count'] = r[x]['member_count']
#     clubs.loc[x + (page-1)*200,'dimensions'] = r[x]['dimensions']

# print(clubs)
# # -- ------------------------------------------------------------------------------------------------------
# Get Club Activities

# /clubs/{id}/activities
#Loop through all activities
page = 1
url = "https://www.strava.com/api/v3/clubs"

access_token = strava_tokens['access_token']
# 'id': 326452, 'resource_state': 2, 'name': 'F3 Carpex' fetched from above "Get Athlete Club"
Clubid = '326452'
substring = 'Half Dome'

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
    # logging.info( Clubid + '/activities'  + '&per_page=200' + '&page=' + str(page))
    r = requests.get(url + '/' + Clubid + '/activities'  + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))

    r = r.json()
    with open('club_activities.json', 'a') as outfile:
        json.dump(r, outfile)

    if (not r):
        break
    
    # otherwise add new data to dataframe
    # debug('line:',x)
    for x in range(len(r)):
        if r[x]['name'].find(substring) != -1:
            # club_activities.loc[x + (page-1)*200,'id'] = str(page) + str(r[x])
            club_activities.loc[x + (page-1)*200,'athlete'] = r[x]['athlete']['firstname'] + ' ' + r[x]['athlete']['lastname']
            club_activities.loc[x + (page-1)*200,'name'] = r[x]['name']
            club_activities.loc[x + (page-1)*200,'distance'] = r[x]['distance']*0.000621371 # convert Meters to miles
            club_activities.loc[x + (page-1)*200,'moving_time'] = r[x]['moving_time']
            club_activities.loc[x + (page-1)*200,'elapsed_time'] = r[x]['elapsed_time']
            club_activities.loc[x + (page-1)*200,'total_elevation_gain'] = r[x]['total_elevation_gain']*3.28084 # convert Meters to feet
    page += 1
logging.info('-- ------------------------------------------  --------------------------------------------')
logging.info("{substring} Activities")
logging.info(club_activities)
logging.info('-- ------------------------------------------  --------------------------------------------')
club_activities[['athlete','name','distance','moving_time','elapsed_time','total_elevation_gain']].sort_values(by='distance',ascending=False).to_csv('./data/PAX_HD_Excercises.csv', mode='a', header=False)

logging.info('GetStravaData.py has run')