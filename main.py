from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, validator
from fastapi.responses import JSONResponse

import re
import sqlite3

MAXIMUM_NAME_LENGTH = 64
REQUIRED_PHONE_LENGTH = 10

connection = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = connection.cursor()


class Customer(BaseModel):
    id: int
    name: str
    phone: str


class CustomerCreate(BaseModel):
    name: str
    phone: str


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class Item(BaseModel):
    id: int
    name: str
    price: float

    @validator("price", pre=True, always=True)
    def format_price(cls, v):
        return round(v, 2)


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = 0.00


class ItemQuantity(BaseModel):
    name: str
    quantity: int


# Define the alias generator function
def to_camel_case(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class ItemQuantityTotalPrice(BaseModel):
    name: str
    item_price: float
    quantity: int
    item_price_total: float

    class Config:
        alias_generator = to_camel_case
        allow_population_by_field_name = True
        json_encoders = {float: lambda v: format(v, ".2f")}


class OrderCreate(BaseModel):
    name: str
    phone: str
    items: list[ItemQuantity]
    notes: Optional[str] = None


class OrderCreated(BaseModel):
    id: int
    timestamp: datetime
    items: list[ItemQuantityTotalPrice]
    total: float


class OrderReturned(BaseModel):
    id: int
    timestamp: datetime
    name: str
    phone: str
    notes: Optional[str] = None
    items: list[ItemQuantityTotalPrice]
    total: float

    class Config:
        json_encoders = {float: lambda v: format(v, ".2f")}


class OrderUpdate(BaseModel):
    items: Optional[list[ItemQuantity]] = None
    notes: Optional[str] = None


app = FastAPI()


def get_customer_service(id: str):
    """Retrieves a JSON representation of a customer in the DB"""
    # Retrieve the customer
    cursor.execute("SELECT name, phone FROM customers where id = ?", (id,))
    data = cursor.fetchone()
    if data is None:
        raise HTTPException(status_code=404, detail=f"Customer ID {id} not found.")
    else:
        return CustomerCreate(name=data[0], phone=data[1])


def get_item_service(id: str):
    """Retrieves a JSON representation of an item in the DB"""
    # Retrieve the customer
    cursor.execute("SELECT name, price FROM items where id = ?", (id,))
    data = cursor.fetchone()
    if data is None:
        raise HTTPException(status_code=404, detail=f"Item ID {id} not found.")
    else:
        return ItemCreate(name=data[0], price=data[1])


def get_item_given_name(item_name: str):
    """Given a name, retrieves an item from the DB"""
    # Retrieve the customer
    cursor.execute("SELECT id, price FROM items where name = ?", (item_name,))
    data = cursor.fetchone()
    if data is None:
        raise HTTPException(status_code=404, detail=f"Item {item_name} does not exist.")
    else:
        return Item(id=data[0], name=item_name, price=data[1])


def format_phone_number(phone_number):
    """Formats the input phone number string to a standard 'xxx-xxx-xxxx' format."""
    # Remove all non-numeric characters
    digits = re.sub(r"\D", "", phone_number)

    # Format to 'xxx-xxx-xxxx'
    formatted_number = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return formatted_number


def validate_customer_name_length(name):
    """Validates the length of the customer name"""
    if len(name) > MAXIMUM_NAME_LENGTH:
        return False
    return True


def validate_customer_phone_length(phone):
    """Validates the length of the customer phone number"""
    phone_length = len(phone)
    if phone_length < REQUIRED_PHONE_LENGTH or phone_length > REQUIRED_PHONE_LENGTH:
        return False
    return True


def format_price(price):
    """Formats the price by rounding it off to 2-decimal places"""
    return round(price, 2)


def create_customer_service(customer_create: CustomerCreate):
    """Creates a customer in the DB given a JSON representation"""
    name = customer_create.name
    phone = customer_create.phone

    if not validate_customer_name_length(name):
        raise HTTPException(
            status_code=400,
            detail=f"Customer Name is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.",
        )

    if not validate_customer_phone_length(phone):
        raise HTTPException(
            status_code=400,
            detail=f"Customer Phone is not of required length {REQUIRED_PHONE_LENGTH}.",
        )
    phone = format_phone_number(phone)

    # Insert a new row
    cursor.execute("INSERT INTO customers(name, phone) VALUES (?, ?);", (name, phone))

    # Commit the transaction
    connection.commit()

    last_id = cursor.lastrowid
    return Customer(id=last_id, name=name, phone=phone)


def get_order_items(id: int):
    """Retrieves items for an order"""
    cursor.execute("SELECT * from item_list where order_id = ?", (id,))
    item_list_data = cursor.fetchall()

    if item_list_data is None:
        raise HTTPException(
            status_code=404, detail=f"Order ID {id} not found in item_list table."
        )

    return item_list_data


def get_order_service(id: int):
    """Retrieves a JSON representation of an order in the DB"""
    # Get order by id
    cursor.execute("SELECT * from orders where id = ?", (id,))
    order_data = cursor.fetchone()

    if order_data is None:
        raise HTTPException(status_code=404, detail=f"Order ID {id} not found.")
    else:
        timestamp = order_data[1]
        customer_id = order_data[2]
        notes = order_data[3]

    # Get customer by id
    customer = get_customer_service(customer_id)

    items_map = {}
    total = 0

    # Get item list by order_id
    item_list_data = get_order_items(id)
    for row in item_list_data:
        item_id = row[1]

        # Get item by id
        item = get_item_service(item_id)
        if item_id in items_map:
            items_quantity_total_price = items_map[item_id]
            items_quantity_total_price.quantity += 1
            items_quantity_total_price.item_price_total = (
                item.price * items_quantity_total_price.quantity
            )
        else:
            items_map[item_id] = ItemQuantityTotalPrice(
                name=item.name,
                itemPrice=item.price,
                quantity=1,
                itemPriceTotal=item.price,
            )
    if len(items_map) > 0:
        total = sum(item.item_price_total for item in items_map.values())

    return OrderReturned(
        id=id,
        timestamp=timestamp,
        name=customer.name,
        phone=customer.phone,
        notes=notes,
        items=list(items_map.values()),
        total=total,
    )


def create_order_items(order_id, items: list[ItemQuantity]):
    """Creates items for an order in the DB"""
    items_list = []
    total = 0

    for item_ordered in items:
        item_name = item_ordered.name
        item = get_item_given_name(item_name)
        item_price = item.price
        item_quantity = item_ordered.quantity
        if item_quantity == 0:
            raise HTTPException(
                status_code=400, detail=f"Item quantity for {item_name} is 0."
            )
        item_price_total = item_price * item_quantity
        total += item_price_total

        # Insert new row/s into item_list table based on the quantity ordered
        for _ in range(item_quantity):
            cursor.execute(
                "INSERT INTO item_list(order_id, item_id) VALUES (?, ?);",
                (
                    order_id,
                    item.id,
                ),
            )
            # Commit the transaction
            connection.commit()

        # Construct ItemQuantityTotalPrice object
        items_list.append(
            ItemQuantityTotalPrice(
                name=item_name,
                itemPrice=item_price,
                quantity=item_quantity,
                itemPriceTotal=item_price_total,
            )
        )
    return items_list, total


def delete_order_items(id: int):
    """Deletes items from an order in the DB"""
    cursor.execute("DELETE FROM item_list WHERE order_id = ?", (id,))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Order id {id} from item_list table.",
        )


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/customers")
async def create_customer(customer_create: CustomerCreate):
    """Creates a customer in the DB given a JSON representation"""
    return create_customer_service(customer_create)


@app.get("/customers/{id}")
async def get_customer(id: int):
    """Retrieves a JSON representation of a customer in the DB"""
    return get_customer_service(id)


@app.delete("/customers/{id}")
async def delete_customer(id: int):
    """Deletes a customer in the DB"""
    customer = get_customer_service(id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer ID {id} not found")

    cursor.execute("DELETE FROM customers WHERE id = ?", (id,))
    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete Customer ID {id}."
        )
    return f"Successfully deleted Customer ID {id} with name {customer.name} and phone {customer.phone}."


@app.put("/customers/{id}")
async def update_customer(id: int, customer_update: CustomerUpdate):
    """Updates a customer in the DB given a JSON representation"""
    customer = get_customer_service(id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer id {id} not found")

    old_name = customer.name
    old_phone = customer.phone

    new_name = customer_update.name
    if new_name is not None:
        if not validate_customer_name_length(new_name):
            raise HTTPException(
                status_code=400,
                detail=f"Customer new name {new_name} is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.",
            )

    new_phone = customer_update.phone
    if new_phone is not None:
        if not validate_customer_phone_length(new_phone):
            raise HTTPException(
                status_code=400,
                detail=f"Customer Phone {new_phone} is not of required length {REQUIRED_PHONE_LENGTH}.",
            )
        new_phone = format_phone_number(new_phone)

    if new_name is not None and new_name != "" and new_phone is None:
        cursor.execute("UPDATE customers SET name = ? WHERE id = ?", (new_name, id))
        result_detail = f"Successfully updated customer id {id} with old name {old_name} to new name {new_name}."
    elif new_phone is not None and new_phone != "" and new_name is None:
        cursor.execute("UPDATE customers SET phone = ? WHERE id = ?", (new_phone, id))
        result_detail = f"Successfully updated customer id {id} with old phone {old_phone} to new phone {new_phone}."
    else:
        cursor.execute(
            "UPDATE customers SET name = ?, phone = ? WHERE id = ?",
            (new_name, new_phone, id),
        )
        result_detail = f"Successfully updated customer id {id} with old name {old_name} and phone {old_phone} to new name {new_name} and phone {new_phone}."

    connection.commit()
    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(
            status_code=500, detail=f"Failed to update Customer ID {id}."
        )
    return result_detail


@app.post("/items")
async def create_item(item_create: ItemCreate):
    """Creates an item in the DB given a JSON representation"""
    name = item_create.name
    price = format_price(item_create.price)

    if not validate_customer_name_length(name):
        raise HTTPException(
            status_code=400,
            detail=f"Item name {name} is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.",
        )

    # Insert a new row
    cursor.execute("INSERT INTO items(name, price) VALUES (?, ?);", (name, price))

    # Commit the transaction
    connection.commit()

    last_id = cursor.lastrowid
    return Item(id=last_id, name=name, price=price)


@app.get("/items/{id}")
async def get_item(id: int):
    """Retrieves a JSON representation of an item in the DB"""
    return get_item_service(id)


@app.delete("/items/{id}")
async def delete_item(id: int):
    """Deletes an item in the DB"""
    item = get_item_service(id)

    cursor.execute("DELETE FROM items WHERE id = ?", (id,))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=500, detail=f"Failed to delete Item ID {id}.")
    return f"Successfully deleted Item ID {id} with name {item.name} and price {item.price}."


@app.put("/items/{id}")
async def update_item(id: int, item_update: ItemUpdate):
    """Updates an item in the DB given a JSON representation"""
    item = get_item_service(id)
    old_name = item.name
    old_price = item.price

    new_name = item_update.name
    if new_name is not None:
        if not validate_customer_name_length(new_name):
            raise HTTPException(
                status_code=400,
                detail=f"Item new name {new_name} is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.",
            )

    new_price = item_update.price
    if new_price is not None:
        new_price = format_price(new_price)

    if new_name is not None and new_name != "" and new_price == 0.00:
        cursor.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, id))
        result_detail = f"Successfully updated Item ID {id} with old name {old_name} to new name {new_name}."
    elif new_price != 0.00 and new_name is None:
        cursor.execute("UPDATE items SET price = ? WHERE id = ?", (new_price, id))
        result_detail = f"Successfully updated Item ID {id} with old price {old_price} to new price {new_price}."
    else:
        cursor.execute(
            "UPDATE items SET name = ?, price = ? WHERE id = ?",
            (new_name, new_price, id),
        )
        result_detail = f"Successfully updated Item ID {id} with old name {old_name} and price {old_price} to new name {new_name} and price {new_price}."

    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=500, detail=f"Failed to update Item ID {id}.")

    return result_detail


@app.post("/orders")
async def create_order(order_create: OrderCreate):
    """Creates an order in the DB given a JSON representation"""
    customer_name = order_create.name
    customer_phone = order_create.phone

    cursor.execute(
        "SELECT id FROM customers WHERE name = ? AND phone = ?",
        (
            order_create.name,
            order_create.phone,
        ),
    )
    data = cursor.fetchone()

    if data is None:
        # Insert new customer
        new_customer = CustomerCreate(name=customer_name, phone=customer_phone)
        cust_id = create_customer_service(new_customer).id
    else:
        cust_id = data[0]

    # Insert a new row into orders table
    cursor.execute(
        "INSERT INTO orders(cust_id, notes) VALUES (?, ?);",
        (
            cust_id,
            order_create.notes,
        ),
    )
    # Commit the transaction
    connection.commit()
    order_id = cursor.lastrowid

    order = get_order_service(order_id)

    items_list, total = create_order_items(order_id, order_create.items)
    return OrderCreated(
        id=order_id, timestamp=order.timestamp, items=items_list, total=total
    )


@app.get("/orders/{id}")
async def get_order(id: int):
    """Retrieves a JSON representation of an order in the DB"""
    return get_order_service(id)


@app.delete("/orders/{id}")
async def delete_order(id: int):
    """Deletes an order in the DB"""
    delete_order_items(id)

    cursor.execute("DELETE FROM orders WHERE id = ?", (id,))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Order id {id} not found.")

    return f"Successfully deleted Order ID {id}."


@app.put("/orders/{id}")
async def update_order(id: int, order_update: OrderUpdate):
    """Updates an order in the DB given a JSON representation"""
    notes = order_update.notes
    items = order_update.items

    if (notes is None or not notes) and (items is None or len(items) == 0):
        return JSONResponse(
            status_code=200, detail=f"Nothing to update for Order ID {id}."
        )

    # Check if order exists
    get_order_service(id)

    current_timestamp = datetime.now()

    # Update notes in the order
    if notes is not None and notes:
        cursor.execute(
            "UPDATE orders SET timestamp = ?, notes = ? WHERE id = ?",
            (
                current_timestamp,
                notes,
                id,
            ),
        )
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=500, detail=f"Failed to update notes for Order ID {id}."
            )

    # Update items in the order
    if items is not None and len(items) > 0:
        # Check if items are valid
        for item in items:
            get_item_given_name(item.name)

        # Get item list by order_id
        cursor.execute("SELECT * from item_list where order_id = ?", (id,))
        item_list_data = cursor.fetchall()

        if item_list_data is not None and len(item_list_data) > 0:
            delete_order_items(id)

        create_order_items(id, items)
        cursor.execute(
            "UPDATE orders SET timestamp = ? WHERE id = ?",
            (
                current_timestamp,
                id,
            ),
        )
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=500, detail=f"Failed to update items in Order ID {id}."
            )

    return get_order_service(id)
