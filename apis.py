import requests
import base64
import json
from bs4 import BeautifulSoup
from app import key
import os
akey = os.getenv('alt_key')
coverart = ""
full_title = ""

def read_audio_file(file_path):
    with open(file_path, 'rb') as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')
        
def run_apis_1(full_title):
    genius_id = 0
    url = "https://shazam.p.rapidapi.com/songs/v2/detect"
    querystring = {"timezone": "America/Chicago", "locale": "en-US"}
    payload = read_audio_file(full_title)
    
    headers = {
        "x-rapidapi-key": akey,
        "x-rapidapi-host": "shazam.p.rapidapi.com",
        "Content-Type": "text/plain"
    }

    response = requests.post(url, data=payload, headers=headers, params=querystring)
    ax = json.loads(response.text)

    if response.status_code == 200 and "track" in ax:
        print("IN____________________ SONG FOUND")
        song_name = ax['track']['title']
        song_artist = ax['track']['subtitle']
        
        print(f'Title Name: {song_name}')
        print(f'Artist: {song_artist}')
        full_title = song_name + " " + song_artist
        print(full_title)
        
        if 'images' in ax['track']:
            coverart = ax['track']['images']['coverart']
        
        ax = return_lyrics(song_name, song_artist)
        
        if response.status_code == 200 and "hits" in ax:
            print("IN____________________ ID FOUND")
            genius_id = ax['hits'][0]['result']['id']
            print(f'Genius ID: {genius_id}')
            
            if ax['hits'][0]['result']['instrumental']:
                print("This song is a confirmed instrumental")
                return 2, song_name, song_artist, "", "", coverart

            url = "https://genius-song-lyrics1.p.rapidapi.com/song/lyrics/"
            querystring = {"id": str(genius_id), "text_format": "html"}
            headers = {
                "x-rapidapi-key": str(key),
                "x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
            }
            response = requests.get(url, headers=headers, params=querystring)
            ax = json.loads(response.text)

            if response.status_code == 200 and "lyrics" in ax:
                print("IN____________________ LYRICS FOUND")
                lyric_check = ax['lyrics']['lyrics']['body']['html']
                if lyric_check:
                    if not isinstance(lyric_check, str):
                        lyric_check = str(lyric_check)
                    ret_val = lyric_check
                    soup = BeautifulSoup(lyric_check, features="html.parser")
                    ret_val = soup.get_text()
                    from trans import detect, translate
                    co, la = detect(ret_val[:130])
                    if co == "MUL":
                        return 4, song_name, song_artist, la, ret_val, coverart
                    return 3, song_name, song_artist, la, ret_val, coverart
            elif response.status_code == 200:
                print('Error: cant find track___________________lyrics')
             
        elif response.status_code == 200:
            print('Error: cant find track___________________Id')
            print("Songs lyrics have not been located on the API/not recorded or song is likely an instrumental")
            return 1, song_name, song_artist, "", "", coverart
    
    elif response.status_code == 200:
        print('Error: cant find track___________________at all')
        return 0, "", "", "", "", ""

def return_lyrics(s_name, s_artist):
	# Try s_name and one artist if possible only
    print("RUN 1")
    if "," in s_artist: 
        if "-" in s_name:
            url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
            querystring = {"q": str(s_name.split("-")[0].strip() + " " + s_artist.split(",")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
            headers = {
				"x-rapidapi-key": str(key),
				"x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
			}
            response = requests.get(url, headers=headers, params=querystring)
            print(response.json())
            # print(response.text)
            ax = json.loads(response.text)

            if response.status_code == 200 and ax["hits"] and \
                (ax['hits'][0]['result']['artist_names'] in s_artist.split(",")[0].strip() or 
                 s_artist.split(",")[0].strip() in ax['hits'][0]['result']['artist_names']):

                print("NO ,: " + s_name.split("(")[0].strip() + " " + s_artist.split(",")[0].strip())
                return ax
        if "(" in s_name:
            url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
            querystring = {"q": str(s_name.split("(")[0].strip() + " " + s_artist.split(",")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
            headers = {
				"x-rapidapi-key": str(key),
				"x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
			}
            response = requests.get(url, headers=headers, params=querystring)
            print(response.json())
            # print(response.text)
            ax = json.loads(response.text)

            if response.status_code == 200 and ax["hits"] and \
                (ax['hits'][0]['result']['artist_names'] in s_artist.split(",")[0].strip() or 
                 s_artist.split(",")[0].strip() in ax['hits'][0]['result']['artist_names']):

                print("NO ,: " + s_name.split("(")[0].strip() + " " + s_artist.split(",")[0].strip())
                return ax
        if "(" not in s_name and "-" not in s_name:
            url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
            querystring = {"q": str(s_name.split("(")[0].strip() + " " + s_artist.split(",")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
            headers = {
				"x-rapidapi-key": str(key),
				"x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
			}
            response = requests.get(url, headers=headers, params=querystring)
            print(response.json())
			# print(response.text)
            ax = json.loads(response.text)

            if response.status_code == 200 and ax["hits"] and \
                (ax['hits'][0]['result']['artist_names'] in s_artist.split(",")[0].strip() or 
                 s_artist.split(",")[0].strip() in ax['hits'][0]['result']['artist_names']):
                print("NO , and clean s_name: " + s_name + " " + s_artist.split(",")[0].strip())
                return ax
    if "&" in s_artist:
        if "-" in s_name:
            url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
            querystring = {"q": str(s_name.split("-")[0].strip() + " " + s_artist.split("&")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
            headers = {
				"x-rapidapi-key": str(key),
				"x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
			}
            response = requests.get(url, headers=headers, params=querystring)
            print(response.json())
            # print(response.text)
            ax = json.loads(response.text)

            if response.status_code == 200 and ax["hits"] and \
                (ax['hits'][0]['result']['artist_names'] in s_artist.split("&")[0].strip() or
                 s_artist.split("&")[0].strip() in ax['hits'][0]['result']['artist_names']):

                print("NO &: " + s_name.split("-")[0].strip() + " " + s_artist.split("&")[0].strip())
                return ax
        if "(" in s_name:
            url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
            querystring = {"q": str(s_name.split("(")[0].strip() + " " + s_artist.split("&")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
            headers = {
				"x-rapidapi-key": str(key),
				"x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
			}
            response = requests.get(url, headers=headers, params=querystring)
            print(response.json())
            # print(response.text)
            ax = json.loads(response.text)

            if response.status_code == 200 and ax["hits"] and \
            (ax['hits'][0]['result']['artist_names'] in s_artist.split("&")[0].strip() or 
             s_artist.split("&")[0].strip() in ax['hits'][0]['result']['artist_names']):
                
                print("NO &: " + s_name.split("(")[0].strip() + " " + s_artist.split("&")[0].strip())
                return ax
        if "(" not in s_name and "-" not in s_name:
            url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
            querystring = {"q": str(s_name + " " + s_artist.split("&")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
            headers = {
				"x-rapidapi-key": str(key),
				"x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
			}
            response = requests.get(url, headers=headers, params=querystring)
            print(response.json())
            # print(response.text)
            ax = json.loads(response.text)

            if response.status_code == 200 and ax["hits"] and \
                (ax['hits'][0]['result']['artist_names'] in s_artist.split("&")[0].strip() or 
                 s_artist.split("&")[0].strip() in ax['hits'][0]['result']['artist_names']):

                print("NO & and clean s_name: " + s_name + " " + s_artist.split("&")[0].strip())
                return ax





    print("RUN 2")
    # Try artist and song name together
    url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
    querystring = {"q": str(s_name + " " + s_artist), "per_page": "1", "page": "1", "text_format": "String"}
    headers = {
        "x-rapidapi-key": str(key),
        "x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    print(response.json())
    # print(response.text)
    ax = json.loads(response.text)
    if response.status_code == 200 and ax["hits"] and \
        (ax['hits'][0]['result']['artist_names'].casefold() in s_artist.casefold() or 
         s_artist.casefold() in ax['hits'][0]['result']['artist_names'].casefold()):
        print("STANDARD PROCEDURE")
        return ax




    print("RUN 3")
    # Try formatted s_name
    url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
    querystring = {"q": str(s_name.split("(")[0].strip() + " " + s_artist), "per_page": "1", "page": "1", "text_format": "String"}
    headers = {
        "x-rapidapi-key": str(key),
        "x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    print(response.json())
    # print(response.text)
    ax = json.loads(response.text)

    if response.status_code == 200 and ax["hits"] and \
        (ax['hits'][0]['result']['artist_names'].casefold() in s_artist.casefold() or 
         s_artist.casefold() in ax['hits'][0]['result']['artist_names'].casefold()):
        print("formatted S-Name: " + s_name.split("(")[0].strip() + " " + s_artist)
        return ax


    print("RUN 4")
	#LAST RESORT, STRIP SNAME ONLY
    url = "https://genius-song-lyrics1.p.rapidapi.com/search/"
    querystring = {"q": str(s_name.split("(")[0].strip()), "per_page": "1", "page": "1", "text_format": "String"}
    headers = {
        "x-rapidapi-key": str(key),
        "x-rapidapi-host": "genius-song-lyrics1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    print(response.json())
    # print(response.text)
    ax = json.loads(response.text)

    if response.status_code == 200 and ax["hits"] and \
        (ax['hits'][0]['result']['artist_names'].casefold() in s_artist.casefold() or 
         s_artist.casefold() in ax['hits'][0]['result']['artist_names'].casefold()):
        
        print("LAST RESORT: " + s_name.split("(")[0].strip() + " " + s_artist.split(",")[0].strip())
        return ax

    return []