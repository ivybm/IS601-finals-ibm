import sqlite3
import json

connection = sqlite3.connect("db.sqlite")
cursor = connection.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
    id INTEGER PRIMARY KEY,
    name CHAR(64) NOT NULL,
    phone CHAR(10) NOT NULL
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY,
    name CHAR(64) NOT NULL,
    price REAL NOT NULL
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cust_id INT NOT NULL,
    notes TEXT
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS item_list(
    order_id NOT NULL,
    item_id NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(item_id) REFERENCES items(id)
);
""")

with open('customers.json') as f:
    customers = json.load(f)
    # print(customers)
for phone, name in customers.items():
    cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?);", (name, phone))

result_customers = cursor.execute("SELECT * FROM customers;")
for customer in result_customers.fetchall():
    print(customer)

with open('items.json') as f:
    items = json.load(f)
    # print(item)
for name, stats in items.items():
    price = stats["price"]
    number_of_orders = stats["orders"] # not used
    cursor.execute("INSERT INTO items (name, price) VALUES (?, ?);", (name, price))

result_items = cursor.execute("SELECT * FROM items;")
for item in result_items.fetchall():
    print(item)

connection.commit()