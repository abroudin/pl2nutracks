import requests

def extract_spotify_id(url):
    if "playlist" in url:
        return "playlist", url.split("playlist/")[-1].split("?")[0]
    elif "user" in url:
        return "user", url.split("user/")[-1].split("?")[0]
    return None, None

def fetch_tracks_from_playlist(playlist_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers)
    data = response.json()
    return data.get('items', [])

def fetch_artist_genres(artist_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers)
    data = response.json()
    return data.get('genres', [])
