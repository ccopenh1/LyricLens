from flask import Flask, jsonify, render_template, url_for, redirect, request, session, make_response
import requests
import trans
import redis
import os
from apis import run_apis
import boto3
import unicodedata
import re
from urllib.parse import urlparse
import uuid
import json

redis_url = urlparse(os.getenv("REDIS_URL"))

redis_client = redis.Redis(host=redis_url.hostname, port=redis_url.port, password=redis_url.password, ssl=(redis_url.scheme == "rediss"), ssl_cert_reqs=None)

# Configure AWS S3
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
S3_BUCKET = os.getenv('S3_BUCKET')

# Create S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

db = []
app = Flask(__name__)
app.secret_key = os.getenv('sec_key')

@app.before_request
def set_user_identifier():
    user_id = request.cookies.get('user_id')  # Check if 'user_id' exists in cookies
    if not user_id:  # If no 'user_id', generate one
        user_id = str(uuid.uuid4())
        resp = make_response(render_template(request.endpoint))  # Render the endpoint's template
        resp.set_cookie('user_id', user_id)
        print(f"New user ID generated: {user_id}")
        return resp
    else:
        print(f"Existing user ID: {user_id}")

# @app.before_request
# def set_user_identifier():
#     user_id = request.cookies.get('user_id')  # Check if 'user_id' exists in cookies
#     if not user_id:  # If no 'user_id', generate one
#         user_id = str(uuid.uuid4())
#         resp = make_response(render_template(request.endpoint))  # Render the endpoint's template
#         resp.set_cookie('user_id', user_id)
#         print(f"New user ID generated: {user_id}")
#         return resp
#     else:
#         print(f"Existing user ID: {user_id}")

def add_to_history(user_id, song_data, song_key):
    key = f"user:{user_id}"  # Key for Redis
    existing_history = redis_client.get(key)  # Get existing history
    
    # Parse existing history or initialize an empty list if not found
    history = json.loads(existing_history) if existing_history else [] 
    
    # Include the song_key along with the song_data
    song_data_with_key = song_data.copy()  # Create a copy of song_data
    song_data_with_key['song_key'] = song_key  # Add the song_key to the data
    
    # Append the song data (now with the song_key) to the history
    history.append(song_data_with_key)
    
    # Save updated history back to Redis
    redis_client.set(key, json.dumps(history))
    
    print(f"History updated for user {user_id}: {history}")

@app.route('/history')
def history():
    user_id = request.cookies.get('user_id')
    history = redis_client.get(f"user:{user_id}")
    song_history = json.loads(history) if history else []
    return render_template('history.html', song_history=song_history)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    user_id = request.cookies.get('user_id')
    redis_client.delete(f"user:{user_id}")
    return redirect(url_for('history'))

@app.get('/redistest')
def redis_test():
    message = redis_client.get('my_message')
    message = message.decode('utf-8') if message else "No message found."
    return render_template('redistest.html', message=message)

@app.get('/index')
def index():
    try:
        redis_client.ping()
        print("Redis connection is healthy!")
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
    
    return render_template('index.html')

@app.get('/about')
def about():
    return render_template('about.html')

@app.route('/detected')
def detected():
    user_id = request.cookies.get('user_id')  # Retrieve user_id from cookies
    if not user_id:
        return "User ID not found!", 400  # Handle missing user ID
    
    song_key = request.args.get('key')
    print(f"Received song key: {song_key}")
  
    if not song_key:
        return jsonify({"error": "Missing or invalid key"}), 400

    try:
        song_data_json = redis_client.get(song_key)
        print(f"Song data retrieved: {song_data_json}")

        if not song_data_json:
            return jsonify({"error": "No data found for the provided key"}), 404

        song_data = json.loads(song_data_json)

        add_to_history(user_id=user_id, song_data=song_data, song_key=song_key)


        # Pass the song data and song_key to the template
        return render_template(
            'detected.html',
            code=song_data['code'],
            songName=song_data['songName'],
            artistName=song_data['artistName'],
            songLang=song_data['songLang'],
            songLyric=song_data['songLyric'],
            albumCover=song_data['albumCover'],
            song_key=song_key  # Pass the song_key to the template
        )
    except Exception as e:
        print(f"Error retrieving or rendering song data: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@app.get('/translations')
def translations():
    song_key = request.args.get('key')
    print(f"Received song key: {song_key}")
    
    if not song_key:
        return jsonify({"error": "Missing or invalid key"}), 400


    try:
        # Retrieve song data from Redis
        song_data_json = redis_client.get(song_key)
        print(f"Song data retrieved: {song_data_json}")

        if not song_data_json:
            return jsonify({"error": "No data found for the provided key"}), 404
        song_data = json.loads(song_data_json)
        print(f"Song data: {song_data}")

        # Pass the retrieved data to the template
        return render_template(
            'translation.html',
            name=song_data['songName'],
            art=song_data['artistName'],
            lang=song_data['songLang'],
            lyric=song_data['songLyric'],
            ca=song_data['albumCover'],
            ldict=trans.languages_dict 
        )
    except Exception as e:
        print(f"Error retrieving or rendering song data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.post('/translate')
def translate():
    data = request.get_json()
    text = data.get('text')
    lang = data.get('lang')

    translated_text = trans.translate(text=text, lang=lang) 

    return jsonify({'translatedText': translated_text})

@app.post('/upload-audio')
def upload_audio():

    if 'audio' not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files['audio']
    file_name = audio_file.filename
    s3_path = f"audio/{file_name}"

    try:
        # Upload the audio file to S3
        s3_client.upload_fileobj(audio_file, S3_BUCKET, s3_path)
        print(f"Audio file uploaded to S3: {s3_path}")
        # Process the audio file and retrieve song metadata
        result = run_apis(S3_BUCKET, s3_path)
        print(f"run_apis returned: {result}")

        if result is None:
            return jsonify({"error": "run_apis returned None"}), 500


        code, song_name, song_artist, la, ret_val, coverart = result


        if code == 0:
            return jsonify({"message": "Unable to process audio file"}), 400

        # Prepare song data for Redis
        song_data = {
            'code': code,
            'songName': song_name,
            'artistName': song_artist,
            'songLang': la,
            'songLyric': ret_val,
            'albumCover': coverart
        } 

        # Generate a unique key for storing the song data in Redis
        song_key = f"song:{uuid.uuid4().hex}"  # Unique identifier for the song

        # Store the song data in Redis
        redis_client.set(song_key, json.dumps(song_data))

        # Respond with the song key and endLoop flag
        return jsonify({
            "endLoop": True,  # This will signal the front-end to stop the loop
            "key": song_key   # Return the song key so the client can use it in the redirect
        })

    except Exception as e:
        print(f"Error uploading or processing file: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/lyrics')
def lyrics():
    song_key = request.args.get('song_key')  # Retrieve the song_key from the URL
    user_id = request.cookies.get('user_id')  # Get the user_id from cookies
    
    # Get the user's song history from Redis
    history = redis_client.get(f"user:{user_id}")
    song_history = json.loads(history) if history else []
    
    # Find the song data based on the song_key
    song_data = next((song for song in song_history if song['song_key'] == song_key), None)
    
    if song_data:
        # Extract the song data
        songName = song_data['songName']
        artistName = song_data['artistName']
        songLang = song_data['songLang']
        songLyric = song_data['songLyric']
        albumCover = song_data['albumCover']
        
        # Render the template with the unpacked song data
        return render_template('lyrics.html', songName=songName, artistName=artistName, 
                               songLang=songLang, songLyric=songLyric, albumCover=albumCover)
    else:
        # If no song is found with the given song_key, you can handle it accordingly
        return "Song not found", 404







