from typing import Literal
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError

from models import db, Movie, User, movie_user
import logging
from movie_data_fetcher import fetch_movie_general_data, fetch_movie_data

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


class DataManager:
    """
    Data manager class.
    Data manager controls all the db services and the fetching of the

    Knows HOW to retrieve movies/user
    Knows HOW to store movies/user
    Knows HOW to update movies/user
    Knows HOW to delete movies/user
    """

    def __init__(self):
        self.active_user = None

    # =========================================================================
    # All class definitions related to user management
    # =========================================================================
    def get_all_users(self)->list[User]:
        """
        derive all users from the db.
        :return: a list of users
        """
        stmt = db.select(User).order_by(User.user_name.asc())
        users = db.session.execute(stmt).scalars().all()
        return users


    def get_active_user(self)->User:
        """
        returns the active user (class User)
        :return:
        """
        return self.active_user


    def set_active_user(self, user_id):
        if self.user_exists(user_id):
            stmt= db.select(User).where(User.user_id == user_id)
            user = db.session.execute(stmt).scalars().all()
            if len(user) == 1:
                print(user, type(user))
                self.active_user = user[0]
                return user[0]
            else:
                return None
        return None


    def user_exists(self, received_user)->bool:
        all_users = self.get_all_users()
        if isinstance(received_user, int):
            for user in all_users:
                if user.user_id == received_user:
                    return True
            return False
        elif isinstance(received_user, str):
            for user in all_users:
                if user.user_name == received_user:
                    return True
        elif isinstance(received_user, User):
            for user in all_users:
                if user.user_id == received_user.user_id:
                    return True
        return False


    def add_user(self, user_name:str)-> tuple:
        """
        Upon request to add a new user to the db, first it is checked if perhaps the
        user_name already exists in the db. if so, return that user with result code -1

        if it is a new user, the user will be stored in the db and the new_user object
        will be returned
        :param user_name:
        :return:
        """
        new_user = User(user_name=user_name)
        stmt=db.select(User).where(User.user_name == user_name)
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

    def delete_user(self, user_data:int|str)->tuple:
        """

        :param user_id:
        :return:
        """
        if isinstance(user_data, int):
            stmt=db.select(User).where(User.user_id == user_data)
        elif isinstance(user_data, str):
            if self.get_active_user() is not None:
                if self.active_user.user_name != user_data:
                    return None, "Active user name and received name do not match"
                else:
                    stmt=db.select(User).where(User.user_name == self.active_user.user_name)
            else:
                return None, "Active user is not set. Please select an active user first."
        else:
            return None, f"Programming error, received {user_data} should be an integer or a string."


        user_to_delete = db.session.execute(stmt).scalars().all()
        if len(user_to_delete) != 1:
            return None, f"No user found with the provided user data: {user_data}"
        if user_to_delete[0].user_id == self.active_user.user_id:
            self.active_user = None
        db.session.delete(user_to_delete[0])
        db.session.commit()
        return user_to_delete[0], f"User {user_to_delete[0]} deleted successfully!"

    def update_user(self, user_id:int, new_user_name:str)->User|None:
        stmt=db.select(User).where(User.user_id == user_id)
        user_to_update = db.session.execute(stmt).scalars().all()
        if len(user_to_update) != 1:
            return None
        user_to_update[0].user_name = new_user_name
        db.session.commit()
        return user_to_update[0]

    # =========================================================================
    # All class definitions related to movie management
    # =========================================================================

    def fetch_matching_movies(self, movie_title:str="")->list[Movie]:
        potential_movies=fetch_movie_general_data(movie_title)
        return potential_movies

    def create_movie(self, imdbID:str)->Movie|None:
        """
        Fetch relevant details for the received imdbID which will be used to create the movie.
        if movie details are received, create a movie object and store it in the database.

        :param imdbID:
        :return: If no movie details are received return None. Otherwise return the movie object
        """

        movie_details = fetch_movie_data(imdbID)
        if len(movie_details) != 0:
            new_movie = Movie(
            title = movie_details.get('Title',""),
            director = movie_details.get('Director', ""),
            IMDB_id = imdbID,
            year = movie_details.get('Year', ""),
            poster_url = movie_details.get('Poster', ""),
            user_id = self.get_active_user().user_id
            )
            return new_movie, f"Movie {new_movie.title} by {new_movie.director }created successfully!"
        return None, "Error: Movie details could not be fetched. Please try again later"

    def movie_exists(self, imdbID:str)->bool:
        stmt = db.select(Movie).where(Movie.IMDB_id == imdbID)
        existing_movies = db.session.execute(stmt).scalars().all()
        if len(existing_movies) != 0:
            return True
        return False

    def store_movie(self, movie):
        if self.movie_exists(movie.IMDB_id):
            return None, f"Movie {movie.title} already exists in the database"
        db.session.add(movie)

        # db.session.flush sends the INSERT to the database so movie.movie_id is generated,
        # but the transaction is not permanently committed yet. Commitment follows at
        # db.session.commit
        db.session.flush()
        logging.info(f"Connecting movie {movie.movie_id} to user {self.active_user.user_id}")
        insert_link = movie_user.insert().values(
            movie_id = movie.movie_id,
            user_id=self.active_user.user_id
        )
        db.session.execute(insert_link)
        logging.info(f"Connection successfully stored in the movie_user table3: {movie.title} - {movie.director}")
        db.session.commit()
        print("added movie:", movie)
        return movie, f"Movie successfully stored in the DB: {movie.title} - {movie.director}"


    def store_manually_added_movie(self, movie:dict)->tuple:
        if self.get_active_user():
            new_movie = Movie(
                title=movie.get('title',""),
                director=movie.get('director', ""),
                IMDB_id=movie.get('IMDB_id', ""),
                year=movie.get('year', ""),
                poster_url=movie.get('poster_url',""),
                user_id=self.get_active_user().user_id
            )
            try:
                db.session.add(new_movie)
                db.session.flush()
                logging.info(f"Connecting movie {new_movie.movie_id} to user {self.active_user.user_id}")
                insert_link = movie_user.insert().values(
                    movie_id=new_movie.movie_id,
                    user_id=self.active_user.user_id
                )
                db.session.execute(insert_link)
                logging.info(f"Connection successfully stored in the movie_user table3: {new_movie.title} - {new_movie.director}")
                db.session.commit()
            except IntegrityError as e:
                logging.info(f"An error occurred while storing the movie: {e}")
                return new_movie, "An error occurred while storing the movie"
            print("added movie:", new_movie)
        return None, "An error occurred while storing the movie"


    def get_all_movies_of_active_user(self, sorting_command:dict)->list[Movie|None]:
        """
        returns a list of all movies for the active user
        :return:
        """
        active_user_id = self.get_active_user().user_id
        if sorting_command['sort_by'] == 'movies':
            if sorting_command['direction'] == 'asc':
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id,).join(
                    User, User.user_id == movie_user.c.user_id).where(User.user_id == active_user_id).order_by(Movie.title.asc())
            else:
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id, ).join(
                    User, User.user_id == movie_user.c.user_id).where(User.user_id == active_user_id).order_by(Movie.title.desc())
        else:
            if sorting_command['direction'] == 'asc':
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id,).join(
                    User, User.user_id == movie_user.c.user_id).where(User.user_id == active_user_id).order_by(Movie.director.asc())
            else:
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id, ).join(
                    User, User.user_id == movie_user.c.user_id).where(User.user_id == active_user_id).order_by(Movie.director.desc())
        movies=db.session.execute(stmt).scalars().all()
        # movies = []
        return movies

    def get_movie(self, movie_id:int)->Movie|None:
        """

        :param movie_id:
        :return:
        """
        stmt = db.select(Movie).where(Movie.movie_id == movie_id)
        movie = db.session.execute(stmt).scalars().one()
        return movie

    def search_for_titles_and_directors(self, query: str, sorting_command:dict) -> list[Movie|None]:
        """
        Enables the search in the database using "%like%" SQL search, case-insensitive. The outcome is sored based
        upon user demands
        :param query: the searchstring
        :param sorting_command: user demands for sorting the output
        :return:
        """
        found_movies = []
        query = "%" + query.strip().lower() + "%"
        if sorting_command["sort_by"] == "title":
            if sorting_command["direction"] == "asc":
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id, ).join(
                        User, User.user_id == movie_user.c.user_id).where(
                            or_(
                                func.lower(Movie.title.like(query)),
                                func.lower(Movie.director.like(query)),
                            )
                        ).order_by(Movie.title.asc())
            else:
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id, ).join(
                        User, User.user_id == movie_user.c.user_id).where(
                            or_(
                                func.lower(Movie.title.like(query)),
                                func.lower(Movie.director.like(query)),
                            )
                        ).order_by(Movie.title.desc())
        else:
            if sorting_command["direction"] == "asc":
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id, ).join(
                        User, User.user_id == movie_user.c.user_id).where(
                            or_(
                                func.lower(Movie.title.like(query)),
                                func.lower(Movie.director.like(query)),
                            )
                        ).order_by(Movie.director.asc())
            else:
                stmt = db.select(Movie).join(
                    movie_user, Movie.movie_id == movie_user.c.movie_id, ).join(
                    User, User.user_id == movie_user.c.user_id).where(
                    or_(
                        func.lower(Movie.title.like(query)),
                        func.lower(Movie.director.like(query)),
                    )
                ).order_by(Movie.director.desc())
        search_result = db.session.execute(stmt).scalars().all()

        # print(search_result, type(search_result))
        return search_result