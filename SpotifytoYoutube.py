# this program creates the playlist
import json, os, google_auth_oauthlib.flow, googleapiclient.errors, requests, youtube_dl, googleapiclient.discovery
from exceptions import ResponseException
from secrets import spotify_token, spotify_userinfo

# Create a class to keep it more organized and allow for quick method specific fixes.

class SearchAndCreate:
    def __init__(self):
        self.ytClient=self.getYT_Client()
        # use dictionary for quick lookups
        self.songData={}
    def getYT_Client(self):
        '''Login to YouTube, https://github.com/googleapis/google-api-python-client'''
        # This is for testing as it prevents security errors from crashing program. Learned from stack overflow
        # Delete upon download
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        # client secrets file is your youtube login credentials
        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

        # from the Youtube DATA API
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client
    def FetchLiked(self):
        """Collects liked vids, collects song information such as song name artist name vid title."""
        request = self.ytClient_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # collect vid get its info
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(
                item["id"])

            # youtube dl gets song name and artist name
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            songTitle = video["track"]
            artist = video["artist"]

            if songTitle is not None and artist is not None:
                # save all important info and skip any missing song and artist
                self.all_song_info[video_title] = {
                    "youtube_url": youtube_url,
                    "songTitle": songTitle,
                    "artist": artist,

                    # add the uri, easy to get song to put into playlist
                    "spotify_uri": self.FetchSpotifyURL(songTitle, artist)

                }
    def FetchSpotifyURL(self, songTitle, artist):
        """Search For the Song"""
        # optimize search in spotify because this isnt used there
        songTitle = songTitle.replace('album', '')
        songTitle = songTitle.replace('offical', '')
        songTitle = songTitle.replace('video', '')
        songTitle = songTitle.replace('lyrics', '')
        songTitle = songTitle.replace('version', '')
        songTitle = songTitle.replace('audio', '')
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            songTitle,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # only use the first song
        uri = songs[0]["uri"]

        return uri

    def createPlaylist(self):
        """create playlist object next method will append to it"""
        request_body = json.dumps({
            "name": "YT to Spotify",
            "description": "github.com/Matthew-Mullen",
            "public": False
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            spotify_userinfo)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()

        # playlist id
        return response_json["id"]

    def add_song_to_playlist(self):
        """Add all liked songs into a new Spotify playlist"""
        # populate dictionary with our liked songs
        self.get_liked_videos()

        # collect all of uri
        uris = [info["spotify_uri"]
                for song, info in self.all_song_info.items()]

        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        # check for valid response status
        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response_json



