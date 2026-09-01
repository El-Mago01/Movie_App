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
    GET /: The home page of your application. Show a list of all registered users and a form for adding new users.
    """
    all_users = dm.get_all_users()
    active_user = dm.get_active_user()
    logging.info("index page requested - displaying user admin")
    return render_template(
        "user_admin.html",
        app_name=APP_NAME,
        all_users=all_users,
        current_function="User administration window",
        active_user=active_user,
        outcome=""
    )


@app.route("/users", methods=["POST"])
def add_user():
    """
    POST /users: When the user submits the “add user” form, a POST request is made.
    The server receives the new user info, adds it to the database, then redirects back to /.
    """
    new_user_name = request.form.get("added_user_name", "").strip()
    logging.info(f"Received a request to add a new user name for: {new_user_name}")
    if new_user_name == "":
        logging.info("No user name provided")
        flash("No user name provided", "warning")
        return redirect(url_for("index"))

    new_user, result = dm.add_user(new_user_name)
    if result == -1:
        logging.info(f"New user {new_user.user_name} already exists in database")
        flash(f"Not able to store new user: New user {new_user.user_name} already exists in the database", "warning")
        return redirect(url_for("index"))

    logging.info(f"New user {new_user.user_name} stored in the database")
    flash(f"New user {new_user.user_name} stored in the database", "success")
    return redirect(url_for("index"))


@app.route('/users/<int:user_id>/movies', methods=['GET'])
def user_movies(user_id):
    """
    GET /users/<int:user_id>/movies: Retrieve that user’s list of favorite movies and displays it.
    """
    user = dm.set_active_user(user_id)
    if not user:
        abort(404, description="User not found")
    all_users = dm.get_all_users()
    sorting_command = {
        "sort_by": request.args.get("sort_by", "movies"),
        "direction": request.args.get("direction", "asc"),
    }
    all_movies = dm.get_all_movies_of_user(user_id, sorting_command)
    logging.info(f"Displaying movies for user {user.user_name}")
    
    outcome = {
        "result": 200,
        "message": f"Successfully retrieved movies for {user.user_name}" if all_movies else "No movies available in the movie database"
    }
    return render_template(
        "index.html",
        app_name=APP_NAME,
        all_users=all_users,
        all_movies=all_movies,
        current_function=f"Display {user.user_name}'s movies",
        outcome=outcome,
        active_user=user
    )


@app.route('/users/<int:user_id>/movies', methods=['POST'])
def add_user_movie(user_id):
    """
    POST /users/<int:user_id>/movies: Add a new movie to a user’s list of favorite movies.
    Handles search & add, selected search movies, and manual add operations.
    """
    user = dm.set_active_user(user_id)
    if not user:
        abort(404, description="User not found")
    
    # 1. OMDb Search Action
    if "movie_title" in request.form and "director" not in request.form:
        requested_title = request.form.get("movie_title", "").strip()
        if not requested_title:
            abort(404, description="Title cannot be empty")
        found_movies = dm.fetch_matching_movies(requested_title)
        if not found_movies:
            flash(f"No movies found for title '{requested_title}'", "warning")
            return redirect(url_for('user_movies', user_id=user_id))
        outcome = {
            "result": 200,
            "message": f"Found matching movies for '{requested_title}'",
        }
        return render_template(
            "select_movie.html",
            app_name=APP_NAME,
            current_function="Select movie to be added to the DB",
            outcome=outcome,
            found_movies=found_movies,
            active_user=user,
        )
        
    # 2. Add Selected Search Movies Action
    elif "selected_movies" in request.form:
        selected_movies = request.form.getlist("selected_movies")
        for movie_imdbID in selected_movies:
            new_movie, message = dm.create_movie(movie_imdbID)
            if new_movie is not None:
                movie_stored, result = dm.store_movie(new_movie)
                if movie_stored is None:
                    logging.warning(result)
                    flash(result, "warning")
                else:
                    logging.info(result)
                    flash(result, "success")
            else:
                logging.warning(message)
                flash(message, "warning")
        return redirect(url_for('user_movies', user_id=user_id))
        
    # 3. Manual Add Action
    elif "director" in request.form:
        updated_title = request.form.get("movie_title", "").strip()
        updated_year = request.form.get("year", "").strip()
        updated_director = request.form.get("director", "").strip()
        updated_imdbID = request.form.get("IMDB_id", "").strip()
        updated_poster_url = request.form.get("poster_url", "").strip()
        new_movie_dict = {
            "title": updated_title,
            "year": updated_year,
            "director": updated_director,
            "IMDB_id": updated_imdbID,
            "poster_url": updated_poster_url,
        }
        result = dm.store_manually_added_movie(new_movie_dict)
        if result[0] is None:
            flash(f"Manually added movie: {updated_title}", "success")
        else:
            flash(f"Movie not added: {result[1]}", "warning")
        return redirect(url_for('user_movies', user_id=user_id))
        
    abort(400, description="Invalid form submission")


@app.route('/users/<int:user_id>/movies/add_manual', methods=['GET'])
def manually_add_movie_form(user_id):
    """
    GET /users/<int:user_id>/movies/add_manual: Renders manual add movie form.
    """
    user = dm.set_active_user(user_id)
    if not user:
        abort(404, description="User not found")
    return render_template(
        "manually_add_movie.html",
        current_function="Manually add a new movie",
        active_user=user,
        user_id=user_id
    )


@app.route('/users/<int:user_id>/movies/<int:movie_id>/update', methods=['GET', 'POST'])
def update_user_movie(user_id, movie_id):
    """
    POST /users/<int:user_id>/movies/<int:movie_id>/update: Modify the title/details of a specific movie.
    """
    user = dm.set_active_user(user_id)
    if not user:
        abort(404, description="User not found")
    movie_to_update = dm.get_movie(movie_id)
    if not movie_to_update:
        abort(404, description="Movie not found")
        
    if request.method == 'POST':
        updated_title = request.form.get("movie_title", "").strip()
        updated_year = request.form.get("year", "").strip()
        updated_director = request.form.get("director", "").strip()
        updated_imdbID = request.form.get("IMDB_id", "").strip()
        updated_poster_url = request.form.get("poster_url", "").strip()
        
        if updated_title:
            movie_to_update.title = updated_title
        if updated_year:
            from data_manager import normalize_year
            movie_to_update.year = normalize_year(updated_year)
        if updated_director:
            movie_to_update.director = updated_director
        if updated_imdbID:
            movie_to_update.IMDB_id = updated_imdbID
        if updated_poster_url:
            movie_to_update.poster_url = updated_poster_url
            
        db.session.commit()
        flash(f"Movie updated successfully", "success")
        return redirect(url_for('user_movies', user_id=user_id))
        
    # GET request
    return render_template(
        "update_movie.html",
        app_name=APP_NAME,
        current_function="Update of a selected movie",
        movie_to_update=movie_to_update,
        active_user=user,
        user_id=user_id
    )


@app.route('/users/<int:user_id>/movies/<int:movie_id>/delete', methods=['POST'])
def delete_user_movie(user_id, movie_id):
    """
    POST /users/<int:user_id>/movies/<int:movie_id>/delete: Remove a specific movie from a user's favorites.
    """
    user = dm.set_active_user(user_id)
    if not user:
        abort(404, description="User not found")
    deleted_movie = dm.delete_movie(movie_id)
    if deleted_movie is None:
        abort(500, description="Movie not deleted due to internal database error")
    flash(f"Deletion of movie '{deleted_movie.title}' successful", "success")
    return redirect(url_for('user_movies', user_id=user_id))


@app.route("/update_user", methods=["POST"])
def update_user():
    user_to_update = dm.get_active_user()
    if user_to_update is None:
        abort(404, description="Active user is not set. Please ensure active user is set!")
    user_id_to_update = user_to_update.user_id
    new_user_name = request.form.get("new_user_name", "").strip()
    if new_user_name == "":
        abort(404, description="Received new_user_name is empty")
    result = dm.update_user(user_id_to_update, new_user_name)
    if result is not None:
        flash(f"User name updated successfully to {result.user_name}", "success")
        return redirect(url_for("index"))
    abort(500, description="Unable to update username")


@app.route("/delete_user", methods=["POST"])
def delete_user():
    user_name_to_delete = request.form.get("user_name_to_delete", "").strip()
    result = dm.delete_user(user_name_to_delete)
    if result[0] is not None:
        flash(result[1], "success")
        return redirect(url_for("index"))
    abort(400, description=result[1])


@app.route("/select_user", methods=["POST"])
def select_user():
    received_user_id = request.form.get("user_id", "")
    if received_user_id.isnumeric():
        return redirect(url_for('user_movies', user_id=int(received_user_id)))
    return redirect(url_for('index'))


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
    app.run(host="0.0.0.0", port=5001, debug=True)
