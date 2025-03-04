#!/usr/local/bin/python3.9

import os
import json
import logging
import re
from requests.exceptions import JSONDecodeError
from datetime import date
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d in function %(funcName)s] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING
)

logger = logging.getLogger(__name__)

class StravaDataFetcher:
    def __init__(self):
        self.client_id = os.environ.get('STRAVA_CLIENT_ID')
        self.client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
        self.refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
        self.access_token = self.authenticate()
    
    def authenticate(self):
        """Authenticate with Strava API and obtain access token."""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.error("Missing Strava credentials in environment variables")
            raise ValueError("Missing required Strava credentials")
        
        response = requests.post(
            url='https://www.strava.com/oauth/token',
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Strava authentication failed with status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            raise Exception("Failed to authenticate with Strava")
        
        try:
            strava_tokens = response.json()
            access_token = strava_tokens['access_token']
            logger.debug(f"Successfully obtained access token: {access_token[:10]}...")
            return access_token
        except (JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Strava response: {e}")
            logger.error(f"Response content: {response.text}")
            raise
        
    def fetch_activities(self):
        """Fetch Strava activities based on name pattern."""
        pattern = re.compile(r'half\s*dome', re.IGNORECASE)
        activities_list = []

        page = 1
        url = "https://www.strava.com/api/v3/activities"

        while True:
            try:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                r = requests.get(f"{url}?per_page=200&page={page}", headers=headers)
                r.raise_for_status()
                activities_json = r.json()
                logger.debug(f"API Response (Page {page}): {activities_json}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch activities: {e}")
                break
            except JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {e}")
                break
                
            if not isinstance(activities_json, list):
                logger.error("API response is not a list of activities.")
                break
            
            for activity in activities_json:
                if isinstance(activity, dict) and pattern.search(activity.get('name', '')):
                    activities_list.append(self.process_activity(activity))
            page += 1
            
        activities = pd.DataFrame(activities_list)
        activities['start_date_local'] = pd.to_datetime(activities['start_date_local'])
        return activities
    
    @staticmethod
    def activity_columns():
        """Define activity DataFrame columns."""
        return [
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
    
    @staticmethod
    def process_activity(activity):
        """Process individual activity data."""
        return {
            "id": activity['id'],
            "name": activity['name'],
            "start_date_local": activity['start_date_local'],
            "type": activity['type'],
            "distance": activity['distance'] * 0.000621371,  # Convert Meters to miles
            "moving_time": activity['moving_time'],
            "elapsed_time": activity['elapsed_time'],
            "total_elevation_gain": activity['total_elevation_gain'] * 3.28084,  # Convert Meters to feet
            "end_latlng": activity['end_latlng'],
            "external_id": activity['external_id']
        }

class GoogleSheetsHandler:
    def __init__(self):
        self.credentials_json = os.environ['GOOGLE_SHEETS_CREDENTIALS']
        self.spreadsheet_key = os.environ['GOOGLE_SHEETS_SPREADSHEET_KEY']
        self.client = self.authorize_google_sheets()

    def authorize_google_sheets(self):
        """Authorize Google Sheets API."""
        credentials_json_dict = json.loads(self.credentials_json.replace('\n', ' '))
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json_dict, scope)
        return gspread.authorize(credentials)

    def upload_data(self, data, sheet_name):
        """Upload data to the specified Google Sheets worksheet."""
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_key)
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()  # Clear existing data
            set_with_dataframe(worksheet, data, include_index=False, include_column_header=True, resize=True)
        except gspread.exceptions.WorksheetNotFound as e:
            logger.error(f"Worksheet not found: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")

def main():
    strava_fetcher = StravaDataFetcher()
    activities = strava_fetcher.fetch_activities()

    google_sheets_handler = GoogleSheetsHandler()
    google_sheets_handler.upload_data(activities, "Ramsay's Records")

if __name__ == "__main__":
    main()