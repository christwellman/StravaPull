import os
import requests

def main():
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    access_token = os.getenv("ACCESS_TOKEN")

    # Your code to interact with Strava API using above credentials

if __name__ == "__main__":
    main()
