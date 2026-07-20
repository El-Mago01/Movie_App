from typing import Literal
from sqlalchemy import select
from models import db, Movie, User, movie_user
import logging
from movie_data_fetcher import fetch_movie_general_data

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
        if self.exists(user_id):
            stmt= db.select(User).where(User.user_id == user_id)
            user = db.session.execute(stmt).scalars().all()
            if len(user) == 1:
                print(user, type(user))
                self.active_user = user[0]
                return user[0]
            else:
                return None
        return None


    def exists(self, received_user)->bool:
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
        # potential_movies=fetch_movie_general_data(movie_title)
        potential_movies = []
        return potential_movies

    def store_movie(self, movie):
        pass

    def get_all_movies_of_active_user(self)->list[Movie|None]:
        """
        returns a list of all movies for the active user
        :return:
        """
        stmt = db.select(Movie).join(
            movie_user, Movie.movie_id == movie_user.c.movie_id,).join(
            User, User.user_id == movie_user.c.user_id).order_by(Movie.title.asc())
        movies=db.session.execute(stmt).scalars().all()
        # movies = []
        return movies