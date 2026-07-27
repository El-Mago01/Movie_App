"""
This module handles all user requests. It outsourced all the data handling to the data_manager,
which creates an abstraction layer for the app-module by providing an interface tailored for
the storage of the data or fetching of movie related data externally by movie_data_fetcher-module
The service requests will come from the app-module. The data_manager takes care of the fulfillment
of these requests by using the partners models and movie_data_fetcher.
"""
import os
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, abort, flash
from data_manager import DataManager, db, logging

dm = DataManager()
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(basedir, 'data/movie_app.sqlite')}"
)
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/db.sqlite3"
db.init_app(app)

load_dotenv()  # Load environment variables from .env file
app.secret_key = os.getenv("SECRET_KEY")

with app.app_context():
    db.create_all()

APP_NAME = "MAGO Movie Library"

"""
======================================================================================
HELPER FUNCTIONS
======================================================================================
"""


def analyze_user_input(user_id: str) -> int:
    """
    This function execute the standard checks to see if the received user_id is valid:
    - can be turned into an integer
    - is not empty
    - the specific user_id exists in the DB.

    :param user_id: The received user id by the route
    :return: a verified received_user_id
    """
    print("Received user id:", user_id)
    if not isinstance(user_id, str):
        return -1
    if user_id == "" or not user_id.isnumeric():
        return -1
    try:
        received_user_id = int(user_id)
        if dm.user_exists(received_user_id):
            return received_user_id
    except ValueError:
        return -1
    return -1



#======================================================================================
#ENDPOINTS
#======================================================================================


#------------------------------------------------------------------------------------------
#All Endpoints related to user management
#------------------------------------------------------------------------------------------

@app.route("/")
def index():
    """
    Upon reception of a GET request on this route, it is checked if there are already users in
    the user-db. If not, the user receives the user_admin.html to add a new user.

    If there are already users in the DB, but the user_id is not set, the user gets the
    user_admin.html page to select a user.

    if the user is already set, the user will receive all available films for this user
    displayed as cards.
    On top, it has the ability to change user, via the toast menu

    :return:
    """
    all_users = dm.get_all_users()
    active_user = dm.get_active_user()
    logging.info("index page requested")
    sorting_command = {
        "sort_by": request.args.get("sort_by", "movies"),
        "direction": request.args.get("direction", "asc"),
    }

    if len(all_users) == 0:
        logging.info(
            "index page requested, but active user is not yet set. Select one or create a new user"
        )
        outcome = {
            "result": 200,
            "message": "active user is not set. Select one or create a new user",
        }
        return render_template(
            "user_admin.html",
            app_name=APP_NAME,
            all_users=all_users,
            outcome=outcome,
            current_function="User administration window",
            active_user=active_user,
        )
    if active_user is not None:
        # active user is set. Show the user's movies
        all_movies = dm.get_all_movies_of_user(active_user.user_id, sorting_command)
        if len(all_movies) == 0:
            logging.info(
                "index page requested, but there are no movies in the user database yet.")
            outcome = {
                "result": 200,
                "message": "No movies available in the movie database",
            }
        else:
            logging.info(
                "index page requested, the movies in the DB for "
                "the active user will be displayed")
            outcome = {
                "result": 200,
                "message": "No movies available in the movie database",
            }
        return render_template(
            "index.html",
            app_name=APP_NAME,
            all_users=all_users,
            all_movies=all_movies,
            current_function="Display user's movies and menu",
            outcome=outcome,
            active_user=active_user
        )
    # active user not set, select a user
    print("No user set")
    logging.info(
        "index page requested, but active user not yet set. Users are available")
    outcome = {"result": 200, "message": "active user is not set"}
    return render_template(
        "index.html",
        app_name=APP_NAME,
        all_users=all_users,
        current_function="Display user's movies and menu",
        outcome=outcome,
        active_user=active_user
    )



@app.route("/add_user", methods=["POST"])
def add_user():
    """
    Upon reception of a POST request on this route, it is checked if the received new user_name
    is a valid one. I.e.
    - not empty
    :return:
    """

    new_user_name = request.form.get("added_user_name", "")
    logging.info(
        f"Received a request to add a new user name for: {new_user_name}")
    if new_user_name == "":
        logging.info("No user name provided")
        outcome = {"result": 200, "message": "No user name provided"}
        return render_template(
            "user_admin.html",
            current_function="Add a new user",
            outcome=outcome)

    new_user, result = dm.add_user(new_user_name)
    if result == -1:
        logging.info(
            f"New user {
                new_user.user_name} already exists in database")
        flash(
            f"Not able to store new user: New user {
                new_user.user_name} already exists in the database",
            "warning",
        )
        return redirect(url_for("user_admin"))

    logging.info(f"New user {new_user.user_name} stored in the database")
    flash(f"New user {new_user.user_name} stored in the database", "info")
    return redirect(url_for("index"))


@app.route("/list_users", methods=["GET"])
def list_users():
    """
    List all available users in a separate html file
    :return:
    """
    all_users = dm.get_all_users()
    if len(all_users) > 0:
        return render_template(
            "list_users.html",
            app_name=APP_NAME,
            current_function="Listing of available users",
            all_users=all_users,
        )
    abort(
        400,
        description="There are no users yet in the DB. "
                    "Please add them via the user administration tool",
    )


@app.route("/select_user", methods=["POST"])
def select_user():
    received_user_id = request.form.get("user_id", "")
    logging.info(
        f"Received a request to change the active user to: {received_user_id}")
    received_user_id = analyze_user_input(received_user_id)
    if received_user_id == -1:
        abort(
            404,
            description=f"Received user_id {received_user_id} not correct")
    active_user = dm.set_active_user(received_user_id)
    if active_user is not None:
        return redirect(url_for("index"), 302)
    return render_template("set_user-message.html")


@app.route("/user_admin", methods=["GET"])
def user_admin():
    """
    Upon reception of this request the user will receive a link towards the user_admin.thml
    including all the existing users in the DB and the active_user
    """
    all_users = dm.get_all_users()
    active_user = dm.get_active_user()

    return render_template(
        "user_admin.html",
        app_name=APP_NAME,
        active_user=active_user,
        all_users=all_users,
        current_function="User administration window",
        outcome="",
    )


@app.route("/user_action", methods=["POST"])
def user_action():
    """
    This is a grouping of the following 3 functions:
    - select
    - delete
    - update
    Which action to take comes from the input parameter "action".

    :param user_id,
    :param action (either 'select', 'delete' or 'update')
    :return:

    """
    received_user_id = request.form.get("user_id", "")
    received_action = request.form.get("action", "")
    received_user_id = analyze_user_input(received_user_id)
    if received_user_id == -1:
        abort(404, description="Received user_id not correct")
    if received_action == "select":
        active_user = dm.set_active_user(received_user_id)
        if active_user is not None:
            flash(f"User {active_user.user_name} is now active", "info")
            return redirect(url_for("index"))
        abort(
            500,
            description=f"Unable to activate the provided user id {received_user_id}",
        )
    elif received_action == "delete":
        result = dm.delete_user(received_user_id)
        if result[0] is not None:
            flash(
                f"User {
                    result[0].user_name} is deleted successfully",
                "info")
            return redirect(url_for("index"))

        abort(500,
              description=f"Unable to delete the provided user id {received_user_id}"
        )
    elif received_action == "update":
        new_user_name = request.form.get("new_user_name", "")
        if new_user_name == "":
            logging.info("No user name provided")
            abort(404, description="No new user name provided")
        result = dm.update_user(received_user_id, new_user_name)
        if result is not None:
            message = f"User {result.user_name} is updated successfully"
            flash(message, "success")
            return redirect(url_for("index"), 302)
        abort(
            500,
            description=f"Unable to update the provided user id {received_user_id}. "
                        "\nUnexpected error while updating the user",
        )
    else:
        message = "Invalid action selected"
        abort(500, description=message)


@app.route("/delete_user", methods=["POST"])
def delete_user():
    """
    Upon reception of this request the current user's name is compared with the received
    user's name for validation. If it is the same, the user will be deleted.
    """
    user_name_to_delete = request.form.get("user_name_to_delete", "")
    logging.info(f"Request to delete user: {user_name_to_delete} ")
    result = dm.delete_user(user_name_to_delete)
    if result[0] is not None:
        message = result[1]
        logging.info(result[1])
        flash(message, "success")
        return redirect(
            "set_user-message.html", 302
        )  # Indicating that a redirect should occur to the
           # set_user-message.html as the active user is not set

    message = (
        "User could not be deleted. Please use the user administration to try again."
    )
    logging.info(result[1])
    flash(message, "error")
    abort(
        402,
        description="User could not be deleted. Please use the user administration to try again.",
    )


@app.route("/update_user", methods=["POST"])
def update_user():
    """
    The user clicked on the menu option to update the active user. Upon reception, the active user
    """
    user_to_update = dm.get_active_user()
    if user_to_update is None:
        logging.info(
            "Active user is not set. Please ensure active user is set!")
        abort(
            404,
            description="Active user is not set. Please ensure active user is set!")

    user_id_to_update = user_to_update.user_id
    new_user_name = request.form.get("new_user_name", "").strip()
    if new_user_name == "":
        abort(
            404,
            description="Received new_user_name is an empty string. Please provide a new user name",
        )
    result = dm.update_user(user_id_to_update, new_user_name)
    if result is not None:
        result_activation = dm.set_active_user(user_id_to_update)
        if result_activation is None:
            message = f"User {
                result.user_name} was updated successfully. Could not change active user name"
            flash(message, "warning")
            return redirect("set_user-message.html", 500)
        message = f"User {result.user_name} was updated successfully"
        flash(message, "success")
        return redirect(url_for("index"), 302)
    abort(
        500,
        description=f"Unable to update the name of provided user id {user_id_to_update}",
    )


#------------------------------------------------------------------------------------------
#All endpoints definitions related to movie management
#------------------------------------------------------------------------------------------

@app.route("/add_movie", methods=["POST"])
def add_movie():
    """
    The user clicked on the option to add a new movie to the DB using the IMDB database.
    In this case:
    1. The received title is analyzed on correctness
    2. A request is sent to the datamanager to fetch all movies in the IMDB database with
    the provided title
    3. The user receives all the movies in a nice listing so that he/she can select the
    movies she/he wants
    to add

    :return:
    """
    requested_title = request.form.get("movie_title", "")

    if not isinstance(requested_title, str):
        abort(
            404,
            description=f"Received title '{requested_title}' not correct")
    if requested_title == "":
        abort(
            404,
            description=f"Received title '{requested_title}' not correct")

    found_movies = dm.fetch_matching_movies(requested_title)
    if len(found_movies) == 0:
        abort(
            400,
            description=f"No movies found for title '{requested_title}'")
    outcome = {
        "result": 200,
        "message": "Found 1 or more movies with the provided title. "
                   "Please select the ones you want to add",
    }
    return render_template(
        "select_movie.html",
        app_name=APP_NAME,
        current_function="Select movie to be added to the DB",
        outcome=outcome,
        found_movies=found_movies,
    )


@app.route("/store_selected_movies", methods=["POST"])
def store_selected_movies():
    """
    The user selected the movies he/she wants to store in the DB.
    Upon reception, the applicable movies are connected with the active user_id
    and stored as such in the 2 tables 'movies and movies_users'
    :return:
    """
    selected_movies = request.form.getlist("selected_movies")
    if dm.get_active_user() is None:
        abort(404, description="Active user is not set")
    for movie_imdbID in selected_movies:
        new_movie, message = dm.create_movie(movie_imdbID)
        if new_movie is not None:
            movie_stored, result = dm.store_movie(new_movie)
            if movie_stored is None:
                logging.warning(result)
            else:
                logging.info(result)
        else:
            logging.warning(message)
        print(message)
    return redirect(url_for("index"), 302)


@app.route("/manually_add_movie", methods=["POST", "GET"])
def manually_add_movie():
    """
    Enables the manually adding of a new movie, e.g. when the movie
    is not stored in the imdb Data base.Here various field like title, director,
    year, poster_url etc are manually fulfilled and forwarded to this route.
    :return:
    """

    # ------------------------------------------------
    #   GET MESSAGE - SEND THE FORM TO FULFILL
    # ------------------------------------------------
    if request.method == "GET":
        return render_template(
            "manually_add_movie.html",
            current_function="Manually add a new movie")

    # ------------------------------------------------
    #   POST MESSAGE - AFTER FILLING THE FORM
    # ------------------------------------------------
    updated_title = request.form.get("movie_title", "")
    updated_year = request.form.get("year", "-1")
    updated_director = request.form.get("director", "")
    updated_imdbID = request.form.get("IMDB_id", "")
    updated_poster_url = request.form.get("poster_url", "")
    new_movie_dict = {
        "title": updated_title,
        "year": updated_year,
        "director": updated_director,
        "IMDB_id": updated_imdbID,
        "poster_url": updated_poster_url,
    }
    result = dm.store_manually_added_movie(new_movie_dict)
    if result[0] is None:
        logging.warning(f"Movie not added: {result[1]}")
        abort(404, description=f"Movie not added: {result[1]}")
    return redirect(url_for("index"), 302)


@app.route("/delete_movie", methods=["POST"])
def delete_movie():
    """
    Delete a movie from the DB based upon input parameter "movie_id"
    :param movie_id, identifying the movie to be deleted
    :return:
    """
    received_movie_id = request.form.get("movie_id", "")
    logging.info(f"Received request to delete movie with ID {received_movie_id}")
    try:
        movie_id = int(received_movie_id)
    except ValueError as e:
        abort(500, description=e)

    if movie_id == -1:
        abort(404, description="Incorrect movie_id received")

    deleted_movie = dm.delete_movie(movie_id=movie_id, del_associations=True)

    if deleted_movie is None:
        abort(500,
              description="Movie not deleted due to internal problem during delete procedure")
    logging.info(f"Deletion of movie with ID {movie_id} successful")
    return redirect(url_for("index"), 302)


@app.route("/update_movie", methods=["GET"])
def update_movie():
    """
    User requested to edit a movie for a specific movie_id.
    To facilitate this request, the user will receive a prefilled
    "update_movie.html".
    :return:
    """
    received_movie_id = request.args.get("movie_id", "-1")
    try:
        received_movie_id = int(received_movie_id)
    except ValueError:
        abort(400, description="Received movie id is not an integer")
    if received_movie_id != -1:
        if dm.get_active_user() is None:
            abort(404, description="No active user set. Please set active user")
        movie_to_update = dm.get_movie(received_movie_id)
        return render_template(
            "update_movie.html",
            app_name=APP_NAME,
            current_function="Update of a selected movie",
            movie_to_update=movie_to_update,
        )
    abort(404, description="No movie id provided")


@app.route("/updated_movie", methods=["POST"])
def updated_movie():
    """
    The user returned the form with the changes to the movie elements. This endpoint takes care
    that these changes are correctly stored in the database.
    :return:
    """
    received_movie_id = request.form.get("movie_id", "")
    try:
        movie_id = int(received_movie_id)

    except ValueError as e:
        abort(500, description=f"Update failed due to : {e}")
    updated_title = request.form.get("title", "")
    updated_year = request.form.get("year", "-1")
    updated_director = request.form.get("director", "")
    updated_imdbID = request.form.get("IMDB_id", "")
    updated_poster_url = request.form.get("poster_url", "")
    if dm.get_active_user() is None:
        abort(404, description="No active user set. Please set active user")
    movie_to_update = dm.get_movie(movie_id)
    if len(updated_title) != 0:
        movie_to_update.title = updated_title
    if len(updated_year) != 0:
        movie_to_update.year = updated_year
    if len(updated_director) != 0:
        movie_to_update.director = updated_director
    if len(updated_imdbID) != 0:
        movie_to_update.olid_book_id = updated_imdbID
    if len(updated_poster_url) != 0:
        movie_to_update.cover_img = updated_poster_url

    db.session.commit()

    return redirect(url_for("index"), 302)


@app.route("/search_movie", methods=["GET"])
def search_movie():
    """
    Searches the DB within both the movie titles and the director name for a match with the received
    query. The query is made lower-case. and uses the SQL "%like%" form.
    :return:
    """
    search_query = request.args.get("query", "")
    sort_command = {"sort_by": "title", "direction": "asc"}
    if search_query == "":
        abort(404, description="Provided search query is empty")

    sorted_movies = dm.search_for_titles_and_directors(
        search_query, sort_command)
    if len(sorted_movies) == 0:
        outcome = {
            "message": f'No matching books or authors found for: "{search_query}"',
            "result": 200,
        }
    else:
        outcome = {
            "message": f'Search successful: "{search_query}"',
            "result": 200}
    return render_template(
        "index.html",
        app_name=APP_NAME,
        active_user=dm.get_active_user(),
        all_movies=sorted_movies,
        current_function="Search movie titles or directors",
        outcome=outcome,
    )


# ------------------------------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------------------------------

@app.errorhandler(404)
def wrong_user_input(e):
    """
    error handler for wrong user input - 404
    :param e:
    :return:
    """
    return render_template("error.html", code=404, message=e.description), 404


@app.errorhandler(500)
def internal_error(e):
    """
    Abort when an internal error occurred during execution - 500

    :param e:
    :return:
    """
    return render_template("error.html", code=500, message=e.description), 500


@app.errorhandler(400)
def bad_request(e):
    """
    Abort when a bad request error occurred - 400
    :param e:
    :return:
    """
    return render_template("error.html", code=400, message=e.description), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
