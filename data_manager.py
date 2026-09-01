"""
This module contains the handling of movie and user data which is modeled in the models-module.
It creates an abstraction layer for the app-module by providing an interface tailored for
the storage of the data or fetching of movie related data externally by movie_data_fetcher-module
The service requests will come from the app-module. The data_manager takes of the fulfillment
of these requests by using the partners models and movie_data_fetcher.
"""

import logging

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, OperationalError

import re
from models import db, Movie, User
from movie_data_fetcher import fetch_movie_general_data, fetch_movie_data


def normalize_year(year_val) -> int | None:
    if year_val is None:
        return None
    if isinstance(year_val, int):
        return year_val
    match = re.search(r"\d{4}", str(year_val))
    if match:
        return int(match.group())
    return None

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


class DataManager:
    """
    Data manager class.
    Data manager controls all the db services and the fetching of the required data
    and storing them in the right format

    Knows HOW to retrieve movies/user information
    Knows HOW to store movies/user data
    Knows HOW to update movies/user data
    Knows HOW to delete movies/user data
    """

    def __init__(self):
        self.active_user = None

    # =========================================================================
    # All class definitions related to user management
    # =========================================================================
    def get_all_users(self) -> list[User]:
        """
        derive all users from the db.
        :return: a list of users
        """
        stmt = db.select(User).order_by(User.user_name.asc())
        users = db.session.execute(stmt).scalars().all()
        return list(users)

    def get_active_user(self) -> User|None:
        """
        returns the active user (class User)
        :return:
        """
        return self.active_user

    def set_active_user(self, user_id: int):
        """
        Activates the User related to the received user_id
        :param user_id:
        :return:
        """
        if not isinstance(user_id, int):
            return None
        if self.user_exists(user_id):
            stmt = db.select(User).where(User.user_id == user_id)
            user = db.session.execute(stmt).scalars().all()
            if len(user) == 1:
                print(user, type(user))
                self.active_user = user[0]
                return user[0]
            return None
        return None

    def unset_active_user(self):
        self.active_user = None

    def user_exists(self, received_user) -> bool:
        """
        Checks if the received user exists in the user table
        :param received_user can be:
        - a string to compare on user_name
        - an int to compare on user_id
        - a User object to compare the object

        comparassion with the existing User objects in the DB
        :return:
        """
        all_users = self.get_all_users()
        if isinstance(received_user, int):
            for user in all_users:
                if user.user_id == received_user:
                    return True
        if isinstance(received_user, str):
            for user in all_users:
                if user.user_name == received_user:
                    return True
        if isinstance(received_user, User):
            for user in all_users:
                if user.user_id == received_user.user_id:
                    return True
        return False

    def add_user(self, user_name: str) -> tuple:
        """
        Upon request to add a new user to the db, first it is checked if perhaps the
        user_name already exists in the db. if so, return that user with result code -1

        if it is a new user, the user will be stored in the db and the new_user object
        will be returned
        :param user_name:
        :return:
        """
        if not isinstance(user_name, str):
            return None, "Received user name is not a string"
        new_user = User(user_name=user_name)
        stmt = db.select(User).where(User.user_name == user_name)
        existing_users = db.session.execute(stmt).scalars().all()
        for user in existing_users:
            if user_name == user.user_name:
                print("Name already exist in userDB: ", user.user_name)
                return user, -1
        # store the new user_name
        db.session.add(new_user)
        db.session.commit()
        print("added User, type():", new_user)
        return new_user, 0

    def delete_user(self, user_data: int | str) -> tuple:
        """
        Deletes the provided user from the db. Associated movies will be automatically
        deleted due to cascade mapping on User.movies relationship.
        """
        if isinstance(user_data, int):
            user_id_to_delete = user_data
        elif isinstance(user_data, str):
            active_user = self.get_active_user()
            if active_user is not None:
                if active_user.user_name == user_data:
                    user_id_to_delete = active_user.user_id
                else:
                    return None, "Active user name and received name do not match"
            else:
                return (
                    None,
                    "Active user is not set. Please select an active user first.",
                )
        else:
            return (
                None,
                f"Programming error, received {user_data} should be an integer or a string."
            )

        try:
            stmt = db.select(User).where(User.user_id == user_id_to_delete)
            user_to_delete = db.session.execute(stmt).scalars().one_or_none()
            if user_to_delete is None:
                return None, f"No user found with the provided user ID: {user_id_to_delete}"
            
            db.session.delete(user_to_delete)
            db.session.commit()
            
            if self.active_user is not None:
                if self.active_user.user_id == user_to_delete.user_id:
                    self.unset_active_user()
            return user_to_delete, f"User {user_to_delete.user_name} deleted successfully!"

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error while deleting user: {e}")
            return None, "Error while deleting user and associated movies. Rollback executed"


    def update_user(self, user_id: int, new_user_name: str) -> User | None:
        """
        Update the user_name of the User object that has the provided user_id
        :param user_id:
        :param new_user_name:
        :return:
        """
        if not isinstance(user_id, int):
            return None
        if not isinstance(new_user_name, str):
            return None
        stmt = db.select(User).where(User.user_id == user_id)
        user_to_update = db.session.execute(stmt).scalars().all()
        if len(user_to_update) != 1:
            return None
        active_user = self.get_active_user()
        if active_user is not None:
            if active_user.user_id == user_id:
                active_user.user_name = new_user_name
        user_to_update[0].user_name = new_user_name
        db.session.commit()
        return user_to_update[0]

    # =========================================================================
    # All class definitions related to movie management
    # =========================================================================

    def fetch_matching_movies(self, movie_title) -> list[Movie]:
        """
        Interface function for searching for movies with a specific title within the imdb web-site.
        The search is actually performed by the movie_data_fetcher module.
        :param movie_title:
        :return:
        """
        if not isinstance(movie_title, str):
            return []
        if movie_title == "":
            return []
        potential_movies = fetch_movie_general_data(movie_title)
        return potential_movies

    def create_movie(self, imdbID: str) -> tuple:
        """
        Creates a new movie object without the movie_id as this is established the moment the
        movie is stored in the DB.
        Fetch relevant details for the received imdbID which will be used to create the movie.
        if movie details are received, create a movie object and return it.

        :param imdbID:
        :return: If no movie details are received return None. Otherwise return the movie object
        with a result string.
        """
        if not isinstance(imdbID, str):
            return None, "received imdbID is not a string"
        movie_details = fetch_movie_data(imdbID)
        user = self.get_active_user()
        if user is None:
            return None, "Error: active user is not set. Please select an active user first"
        user_id = user.user_id
        if len(movie_details) != 0:
            new_movie = Movie(
                title=movie_details.get("Title", ""),
                director=movie_details.get("Director", ""),
                IMDB_id=imdbID,
                year=normalize_year(movie_details.get("Year", "")),
                poster_url=movie_details.get("Poster", ""),
                user_id=user_id
            )
            return (
                new_movie, f"Movie {
                    new_movie.title} by {
                    new_movie.director} created successfully!", )
        return None, "Error: Movie details could not be fetched. Please try again later"

    def movie_exists(self, a_movie_id:int|str) -> bool:
        """
        Checks if the received movie_id or imdbID exists in the database
        :param a_movie_id: as int -> movie_id
                           as str -> imdb_id

        :return: boolean -> True if movie exists, False otherwise
        """

        act_usr = self.get_active_user()
        if act_usr is None:
            return False
        if isinstance(a_movie_id, int):
            stmt = db.select(Movie).where(Movie.movie_id == a_movie_id)
        elif isinstance(a_movie_id, str):
            stmt = db.select(Movie).where(
                Movie.IMDB_id == a_movie_id,
                Movie.user_id == act_usr.user_id
            )
        else:
            return False
        existing_movies = db.session.execute(stmt).scalars().all()


        if len(existing_movies) != 0:
            return True
        return False

    def title_exists(self, title: str, active_user_id: int) -> bool:
        """
        Checks if the received title exists in the database. Only used for manually added movies
        :param title
        :param active_user_id: Is needed to check if the title exists in the db for THIS specific user
        :return: boolean -> True if movie with this title exists, False otherwise
        """
        if not isinstance(active_user_id, int) or active_user_id < 0:
            return False
        if not isinstance(title, str) or len(title) == 0:
            return False
        stmt = (
            db.select(Movie)
            .where(
                Movie.user_id == active_user_id,
                Movie.title == title,
            )
        )
        existing_movies = db.session.execute(stmt).scalars().all()
        if len(existing_movies) != 0:
            return True
        return False

    def store_movie(self, movie: Movie):
        """
        Store the received movie into the database.
        :param movie of type Movie
        :return:
        """
        imdb_id = movie.IMDB_id
        if not isinstance(imdb_id, str) or len(imdb_id) == 0:
            return None, "received imdb_id is not a string"
        if self.movie_exists(movie.IMDB_id):
            return None, f"Movie {movie.title} already exists in the database"
        db.session.add(movie)
        db.session.commit()
        print("added movie:", movie)
        return (
            movie,
            f"Movie successfully stored in the DB: {movie.title}, {movie.director}")

    def store_manually_added_movie(self, movie: dict) -> tuple:
        """
        Store the manually added movie into the database.
        :param movie:
        :return:
        """
        if len(movie.get("title", "")) == 0:
            return None, "Movie can not be stored: Movie title can not be empty"
        if self.title_exists(movie.get("title", ""), self.active_user.user_id):
            return None, "Movie can not be stored: Movie title already exists"
        user = self.get_active_user()
        if user is None:
            return None, "Error: active user is not set. Please select an active user first"
        new_movie = Movie(
            title=movie.get("title", ""),
            director=movie.get("director", ""),
            IMDB_id=movie.get("IMDB_id", ""),
            year=normalize_year(movie.get("year", "")),
            poster_url=movie.get("poster_url", ""),
            user_id=user.user_id,
        )
        try:
            db.session.add(new_movie)
            db.session.commit()
        except IntegrityError as e:
            logging.info("Movie can not be stored due to error: %s", e)
            return new_movie, f"Movie can not be stored due to error: {e}"
        print("added movie:", new_movie)
        return None, "Manually added movie stored successfully"

    def get_all_movies_of_user(
        self, user_id:int, sorting_command: dict
    ) -> list[Movie | None]:
        """
        returns a list of all movies for the active user
        :return:
        """
        if not isinstance(user_id, int):
            return []
        if not self.user_exists(user_id):
            return []
        sort_by = sorting_command.get("sort_by", "movies")
        direction = sorting_command.get("direction", "asc")
        
        stmt = db.select(Movie).where(Movie.user_id == user_id)
        if sort_by == "movies":
            if direction == "asc":
                stmt = stmt.order_by(Movie.title.asc())
            else:
                stmt = stmt.order_by(Movie.title.desc())
        else:
            if direction == "asc":
                stmt = stmt.order_by(Movie.director.asc())
            else:
                stmt = stmt.order_by(Movie.director.desc())
                
        movies = db.session.execute(stmt).scalars().all()
        return list(movies)

    def get_movie(self, movie_id: int) -> Movie | None:
        """
        returns a movie object with the provided movie_id or none if the movie_id is not found.
        :param movie_id:
        :return:
        """
        if isinstance(movie_id, int):
            if self.movie_exists(movie_id):
                stmt = db.select(Movie).where(
                    Movie.movie_id == movie_id)
            else:
                return None
        else:
            return None
        movie = db.session.execute(stmt).scalars().one()
        return movie

    def search_for_titles_and_directors(
        self, query: str, sorting_command: dict
    ) -> list[Movie | None]:
        """
        Enables the search in the database using "%like%" SQL search, case-insensitive.
        The outcome is sorted based upon user demands
        :param query: the searchstring
        :param sorting_command: user demands for sorting the output
        :return: a list of Movie objects that matches the query and sorting command
        """
        act_usr = self.get_active_user()
        user_id = act_usr.user_id if act_usr else -1
        query = "%" + query.strip().lower() + "%"
        sort_by = sorting_command.get("sort_by", "movies")
        direction = sorting_command.get("direction", "asc")
        
        stmt = db.select(Movie).where(
            Movie.user_id == user_id,
            or_(
                func.lower(Movie.title).like(query),
                func.lower(Movie.director).like(query)
            )
        )
        if sort_by == "title":
            if direction == "asc":
                stmt = stmt.order_by(Movie.title.asc())
            else:
                stmt = stmt.order_by(Movie.title.desc())
        else:
            if direction == "asc":
                stmt = stmt.order_by(Movie.director.asc())
            else:
                stmt = stmt.order_by(Movie.director.desc())
                
        search_result = db.session.execute(stmt).scalars().all()
        return list(search_result)

    def delete_movie(self, movie_id:int, commit:bool=True) -> Movie | None:
        """
        Deletes the movie from the movies table

        :param movie_id: movie identifier
        :param commit: An indicator if the commit should be given or if the commit will be
                       done outside of this function

        :return: The Movie object fitting the movie_id or None if the movie does not exist in the DB
        """
        if not isinstance(movie_id, int):
            return None
        stmt = db.select(Movie).where(Movie.movie_id == movie_id)
        movie_to_delete = db.session.execute(stmt).scalars().one_or_none()
        if movie_to_delete is None:
            return None
        try:
            db.session.delete(movie_to_delete)
            if commit:
                db.session.commit()
        except OperationalError:
            logging.error(
                f"Fatal error while deleting movie {movie_id} from database")
            db.session.rollback()
            return None

        return movie_to_delete
