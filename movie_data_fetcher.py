"""
This module contains the fetching of movie data which is then used by the data_manager to handle the
service requests from the app-module.
The movie_data_fetcher uses the omdbapi to fetch relevant movie data required to fulfill the service
requests of the app-module..
"""
import os
import requests
from data_manager import logging

# from dotenv import load_dotenv
# load_dotenv()
api_key = os.getenv("apikey")
BASE_URL = "https://www.omdbapi.com/"

MIN_LENGTH_TITLE = 5


def fetch_movie_data(imdbID: str = "", title: str = "") -> dict:
    """
    gets the detailed movie data from the imdb-API for a specific imdbID or title. At least
    one of these parameters must be provided with a valid value (i.e. not "").
    :param imdbID: the imdbID to fetch
    :param title: the title to fetch
    :return:
    """

    logging.info(
        f"Request received to fetch movie information with imdbID={imdbID}, title={title}"
    )

    def specify_search_term(imdbID: str = "", title: str = "") -> str:
        try:
            if imdbID != "":  # the imdbID is the main search key
                search_term = f"?apikey={api_key}&i={imdbID}"
                url = BASE_URL + search_term
                print(url)

            elif title != "":  # the title is the main search key
                if len(title) < MIN_LENGTH_TITLE:
                    return ""
                title_words = title.strip().split(" ")
                title_search_term = "+".join(title_words)
                search_term = f"?apikey={api_key}&s={title_search_term}"
                url = BASE_URL + search_term
                print(url)
            else:
                # Should not occur. Either, imdbID or title must be provided
                return ""
            return url
        # pylint: disable=broad-exception-caught
        # Any type of connection failure is caught
        except Exception as e:
            print("Unexpected path taken. Either imdbID or title must be provided")
            print(f"Error: {e}")
            search_term = f"?apikey={api_key}"
            return search_term

    if not isinstance(imdbID, str):
        return {}
    if not isinstance(title, str):
        return {}

    imdb_url = specify_search_term(imdbID, title)
    if imdb_url == "":
        return {}
    try:
        response = requests.get(imdb_url, timeout=15)
        movie_details = response.json()
        # pylint: disable=broad-exception-caught
        # Any type of connection failure is caught
    except Exception as e:
        logging.info(f"Could not access API: GET Request failed:\n{e}")
        return {}
    if response.status_code != 200:  # the json contains an invalid response
        logging.info(
            f"Unable to search for movie in omdb db. Error: {response.content}"
        )
    logging.info("successfully fetched movie details")
    return movie_details


def fetch_movie_general_data(title: str) -> list:
    """
    Get all the movies from the API that are alike the provided title
    :param title: the title to fetch
    :return: a list of movies
    """
    if not isinstance(title, str):
        return []
    if len(title) < MIN_LENGTH_TITLE:
        return []
    movie_data = fetch_movie_data("", title)
    if movie_data.get("Response") == "True" and "Search" in movie_data:
        return movie_data["Search"]
    return []  # in case movie_data is empty
