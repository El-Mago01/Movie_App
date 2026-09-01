"""
This module contains the handling of movie and user models.
It helps the data_manager to create an abstraction layer for the app-module
by providing an interface tailored for the storage of the data or fetching
of movie related data externally by movie_data_fetcher-module.
The service requests will come from the app-module. The data_manager will
take care of the fulfillment of these requests by using the partners models and
movie_data_fetcher.
"""

from flask_sqlalchemy import SQLAlchemy

# from app import app

db = SQLAlchemy()

# ================================================================================
# User class (inheriting from db.Model class)
# ================================================================================
class User(db.Model):
    """
    User model, with name and user_id, using the Flask-ORM for database management

    """

    __tablename__ = "users"
    user_id = db.Column(
        db.Integer, primary_key=True, nullable=False, autoincrement=True
    )
    user_name = db.Column(db.String(100), nullable=False)
    movies = db.relationship("Movie", backref="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.user_id}: {self.user_name},\n"

    def __str__(self):
        return f"{self.user_id}: {self.user_name},\n"

# ================================================================================
# Movie class (inheriting from db.Model class)
# ================================================================================
class Movie(db.Model):
    """
    Movie model, with name and movie_id, using the Flask-ORM for database management

    """

    # Define all the Movie properties
    __tablename__ = "movies"
    # Link Movie to User
    movie_id = db.Column(
        db.Integer, primary_key=True, nullable=False, autoincrement=True
    )
    title = db.Column(db.String(100), nullable=False)
    director = db.Column(db.String(100), nullable=False)
    IMDB_id = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer)
    poster_url = db.Column(db.String(100))
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False)

    def __repr__(self):
        return f"{
            self.movie_id}: {
            self.title},\n {
            self.director},\n {
                self.IMDB_id},\n {
                    self.year},\n {
                        self.poster_url}"

    def __str__(self):
        return f"{
            self.movie_id}: {
            self.title},\n {
            self.director},\n {
                self.IMDB_id},\n {
                    self.year},\n {
                        self.poster_url}"

