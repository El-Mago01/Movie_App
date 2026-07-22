from flask_sqlalchemy import SQLAlchemy
# from app import app

db = SQLAlchemy()

class User(db.Model):
    """
    User model, with name and user_id, using the Flask-ORM for database management

    """
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    user_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"{self.user_id}: {self.user_name},\n"

    def __str__(self):
        return f"{self.user_id}: {self.user_name},\n"

class Movie(db.Model):
    """
    Movie model, with name and movie_id, using the Flask-ORM for database management

    """
    # Define all the Movie properties
    __tablename__ = 'movies'
    # Link Movie to User
    movie_id = db.Column(db.Integer, primary_key=True , nullable=False, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    director = db.Column(db.String(100), nullable=False)
    IMDB_id = db.Column(db.String, nullable=False)
    year = db.Column(db.String)
    poster_url = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    def __repr__(self):
        return f"{self.movie_id}: {self.title},\n {self.director},\n {self.IMDB_id},\n {self.year},\n {self.poster_url}"

    def __str__(self):
        return f"{self.movie_id}: {self.title},\n {self.director},\n {self.IMDB_id},\n {self.year},\n {self.poster_url}"

"""
The intermediate table between users and movies to enable a many to many relation. 
Only stores the movies_ids and user_ids to show what movies are connected to what user_ids. 
So it can be derived what movies are related to a specific user. But also, what users are 
related to specific movies.

"""
movie_user= db.Table("movie_user",
                     db.Column('movie_id', db.Integer, db.ForeignKey('movies.movie_id'), primary_key=True),
                     db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
                     )

