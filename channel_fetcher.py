# -*- coding: utf-8 -*-
# Sample Python code for youtube.channels.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python
#!/usr/bin/python3.7
import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
client_secrets_file = "secret.json"
api_service_name = "youtube"
api_version = "v3"

def get_requests(youtube, pageToken):
    channels = []
    request = youtube.subscriptions().list(
        part="snippet",
        channelId="UCZwR8eFEDhcKPUD6noy0cKw",
        order="alphabetical",
        pageToken=pageToken,
        maxResults=20
    )
    response = request.execute()
    if "nextPageToken" in response:
        channels = get_requests(youtube, response["nextPageToken"])
    channels.extend([[page["snippet"]["title"], page["snippet"]["resourceId"]["channelId"]] for page in response["items"]][::-1])
    return channels

def write_csv(channels, file):
    out = open(file, "w")
    for title, id in channels:
        out.write(f"{title};{id}\n")

def main():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    youtube = get_authenticated_service()
    channels = get_requests(youtube, "")
    write_csv(channels, "channels.csv")
    return "channels.csv"

def get_authenticated_service():
    if os.path.exists("CREDENTIALS_PICKLE_FILE"):
        with open("creds.pk", 'rb') as f:
            credentials = pickle.load(f)
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_console()
        with open("creds.pk", 'wb') as f:
            pickle.dump(credentials, f)
    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)
if __name__ == "__main__":
    main()
