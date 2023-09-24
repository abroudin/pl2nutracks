from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, session, redirect, request
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from flask_oauthlib.client import OAuth
import csv
from spotify.utils import extract_spotify_id, fetch_tracks_from_playlist, fetch_artist_genres
from datetime import datetime
from models import Artist, Genre, Track, Album, artist_genres
from database import db
from datetime import datetime
import requests
import os



app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'



db.init_app(app)
migrate = Migrate(app, db)

oauth = OAuth(app)

# Set up the Spotify OAuth client
spotify = oauth.remote_app(
    'spotify',
    consumer_key = os.environ.get('CONSUMER_KEY'),
    consumer_secret = os.environ.get('CONSUMER_SECRET'),
    request_token_params={
        'scope': 'user-library-read user-read-email streaming',
        'show_dialog': True
    },
    base_url='https://api.spotify.com/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
)

@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('access_token')


# Function to read URLs from CSV
def read_spotify_links_from_csv(file_path):
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        urls = [{"type": row["Type"], "url": row["URL"]} for row in reader]
    return urls

spotify_links = read_spotify_links_from_csv('static/data/spotifyLinks.csv')

def slugify(value):
    return "".join(c if c.isalnum() else "-" for c in value).lower()


def save_artist_and_genres_to_db(artist_data, access_token):
    artist = Artist.query.filter_by(id=artist_data['id']).first()
    
    if not artist:
        artist = Artist(id=artist_data['id'], name=artist_data['name'])
        db.session.add(artist)
    
    artist_genres = fetch_artist_genres(artist_data['id'], access_token)
    
    for genre_name in artist_genres:
        genre = Genre.query.filter_by(name=genre_name).first()
        if not genre:
            genre = Genre(name=genre_name)
            db.session.add(genre)
        
        if genre not in artist.genres:
            artist.genres.append(genre)
    
    db.session.commit()

@app.route('/')
def home():
    genre_dict = {}
    tracks = Track.query.all()
    for track in tracks:
        for genre in track.artist.genres:
            genre_dict.setdefault(genre.name, []).append(track)
    if not session.get('access_token'):
        return redirect(url_for('login'))
    return render_template('home.html', token=session.get('access_token'), genre_data=genre_dict)

@app.route('/login')
def login():
    return spotify.authorize(callback='https://polite-finch-clearly.ngrok-free.app/callback')

@app.route('/callback')
def callback():
    response = spotify.authorized_response()
    if response is None or response.get('access_token') is None:
        return 'Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    session['access_token'] = response['access_token']
    return redirect('/')  # Redirect to the homepage


def update_database_with_new_data(access_token):
    
    # Loop over the Spotify links
    for link in spotify_links:
        link_type, spotify_id = extract_spotify_id(link['url'])
        
        # If the link is a playlist, fetch tracks from it
        if link_type == "playlist":
            spotify_data = fetch_tracks_from_playlist(spotify_id, access_token)
        else:
            spotify_data = []  # Initialize to an empty list if not a playlist
            
        # Determine if spotify_data is a list or a dictionary
        tracks = spotify_data['items'] if isinstance(spotify_data, dict) and 'items' in spotify_data else spotify_data
        headers = {
            'Authorization': f"Bearer {access_token}"
        }

        # Fetching saved tracks
        response = requests.get('https://api.spotify.com/v1/me/tracks', headers=headers)
        tracks_data = response.json()
        for track in tracks:
            # Check if track already exists in database
            if not Track.query.get(track['track']['id']):
                # Convert the string representation of the date-time to a Python datetime object
                if 'added_at' in track['track']:
                    added_on_datetime = datetime.fromisoformat(track['track']['added_at'].replace("Z", "+00:00"))
                else:
                    # Default to the current datetime if 'added_at' is not present
                    added_on_datetime = datetime.utcnow()

                # Fetch or create the artist
                artist = track['track']['artists'][0]
                # Processing artist
                artist_id = track['track']['artists'][0]['id']
                artist_name = track['track']['artists'][0]['name']

                # Fetch or create the artist
                db_artist = Artist.query.get(artist_id)

                if not db_artist:
                    db_artist = Artist(id=artist_id, name=artist_name)
                    db.session.add(db_artist)
                    db.session.commit()

                # Fetch artist details for genres (assuming spotify is your OAuthRemoteApp instance)
                artist_data = spotify.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers).data

                # Assign genres to the artist
                for genre_name in artist_data['genres']:
                    genre = Genre.query.filter_by(name=genre_name).first()
                    if not genre:
                        genre = Genre(name=genre_name)
                        db.session.add(genre)
                        db.session.commit()
                    if genre not in db_artist.genres:
                        db_artist.genres.append(genre)

                # Fetch or create the album
                album = track['track']['album']
                db_album = Album.query.get(album['id'])
                if not db_album:
                    release_date = datetime.strptime(album['release_date'], '%Y-%m-%d').date()
                    new_album = Album(id=album['id'], name=album['name'], release_date=release_date)
                    db.session.add(new_album)
                    db_album = new_album

                # Create the new track
                new_track = Track(
                    id=track['track']['id'],
                    name=track['track']['name'],
                    added_on=added_on_datetime,
                    artist=db_artist,
                    album=db_album
                )
                db.session.add(new_track)

    db.session.commit()

    print("Data updated!")

@app.route('/update_data')
def update_data_route():
    update_database_with_new_data(session.get('access_token'))
    return "Data update initiated."

def scheduled_update():
    update_database_with_new_data(session.get('access_token'))

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_update, trigger="interval", hours=12)  # Update twice a day
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True)
