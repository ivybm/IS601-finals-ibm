# IS601-finals-ibm
Final Project for IS601

# Contact the Author
Ivy B. Manalang
ibm@njit.edu

# What's here
This repo contains a REST API backend for a dosa restaurant. This uses a SQLite database and FastAPI to provide access to three objects: 
- customers
- items
- orders

The API supports CRUD (create, read, update, delete) for the three objects. The script named `init_db.py` will initialize an empty database using relational constraints (primary keys and foreign keys) from the `customers.json` and `items.json` file we used in the midterm project. The SQLite database is in a file named `db.sqlite`. The FastAPI backend reads and writes from `db.sqlite` and is called `main.py`.

The API supports the following endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/customers` | creates a customer in the DB given a JSON representation |
| GET | `/customers/{id}` | retrieves a JSON representation of a customer in the DB |
| DELETE | `/customers/{id}` | deletes a customer in the DB |
| PUT | `/customers/{id}` | updates a customer in the DB given a JSON representation |
| POST | `/items` | creates an item in the DB given a JSON representation |
| GET | `/items/{id}` | retrieves a JSON representation of an item in the DB |
| DELETE | `/items/{id}` | deletes an item in the DB |
| PUT | `/items/{id}` | updates an item in the DB given a JSON representation |
| POST | `/orders` | creates an order in the DB given a JSON representation |
| GET | `/orders/{id}` | retrieves a JSON representation of an order in the DB |
| DELETE | `/orders/{id}` | deletes an order in the DB |
| PUT | `/orders/{id}` | updates an order in the DB given a JSON representation| 


# How to use
1. Create a virtual environment.
    - Mac: `python3 -m venv venv`
    - Windows: `py -m venv venv`
2. Activate the virtual environment.
    - Mac: `source venv/bin/activate`
    - Windows: `venv\Scripts\activate`
3. Install required packages.
    `pip install -r requirements.txt`
4. Create and populate the SQLite database.
    - Mac: `python3 init_db.py`
    - Windows: `py init_db.py`
5. Run the FastAPI backend.
    `fastapi dev main.py`
