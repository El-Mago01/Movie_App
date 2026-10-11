# Movie App

A Flask learning project for managing users and their personal movie collections. Movies can be searched through the [OMDb API](https://www.omdbapi.com/) or entered manually, then viewed, updated, or deleted. The application stores its data in SQLite.

## Getting started

Use Python 3.12 or newer. From the repository directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
```

Request an API key from [OMDb](https://www.omdbapi.com/apikey.aspx). Create a local `.env` file in the project directory:

```dotenv
SECRET_KEY=replace-with-your-own-random-secret
apikey=replace-with-your-omdb-api-key
```

The application reads the OMDb key from the environment variable `apikey` (lowercase). Generate a Flask secret with `python -c "import secrets; print(secrets.token_hex(32))"`. Keep your actual `.env` file private; it is already excluded by `.gitignore`.

Start the application:

```bash
python app.py
```

Open http://127.0.0.1:5000/. The SQLite tables are created on startup in `data/movie_app.sqlite`, which is ignored by Git. The tracked `data/movie_app.sqlite_bu` is preserved as an existing backup.

## Learning notes and concepts explored

The following notes are preserved from the original README. They describe topics explored during the assignment; not all are necessarily implemented in the final models.

TechStack from Movie App assignment:
- Flask SQLAlchemy
- Flask ORM
- Bootstrap with modals using: 
  - javascript sending both GET and POST request for the modal
- Toast (Bootstrap, little window to change user)
- logging
- OOP - Object oriented Programming
- ORM Statements with joins
- ORM Tables enabling many to many (many-to-many) data connections using a middle table
- flushing for SQL staging area to enable correct storage of data
- flash for forwarding a message with a redirect. Similar to session
- Composite primary key
