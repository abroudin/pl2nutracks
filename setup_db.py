
from app import app, db

# Ensure models are imported
from models import Artist, Genre, Album, Track

with app.app_context():
    db.drop_all()
    db.create_all()

print("Database tables created successfully!")
