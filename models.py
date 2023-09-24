from datetime import datetime
from database import db

# Many-to-many association table between Artist and Genre
artist_genres = db.Table('artist_genres',
    db.Column('artist_id', db.Integer, db.ForeignKey('artist.id')),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'))
)

class Artist(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    tracks = db.relationship('Track', backref='artist', lazy=True)
    genres = db.relationship('Genre', secondary=artist_genres, backref=db.backref('artists', lazy=True))

class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Album(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    tracks = db.relationship('Track', backref='album', lazy=True)
    release_date = db.Column(db.String, nullable=True)


class Track(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    added_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    artist_id = db.Column(db.String, db.ForeignKey('artist.id'), nullable=False)
    album_id = db.Column(db.String, db.ForeignKey('album.id'), nullable=True)
