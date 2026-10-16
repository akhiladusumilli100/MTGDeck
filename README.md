# MTGDeck

A Django project for building and working with Magic: The Gathering card data.

## Databases

The project uses two SQLite databases:

- `db.sqlite3` is Django's default database.
- `cards_db.sqlite3` stores the card catalog, tags, taggings, roles, and archetypes.

From the project root, apply migrations to both databases:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py migrate --database=cards_db
```

## Rebuild Card Data

With the project's virtual environment active and `requests` installed, run:

```powershell
.\.venv\Scripts\python.exe manage.py build_card_db
```

The command downloads Scryfall's oracle card and tag bulk data, then rebuilds the card-related tables in `cards_db.sqlite3`. It replaces the existing card data in that database and requires an internet connection.