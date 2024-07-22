from typing import Optional, Union
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import re
import sqlite3
import uvicorn

MAXIMUM_NAME_LENGTH = 64
REQUIRED_PHONE_LENGTH = 10

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080)

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

class ItemCreate(BaseModel):
    name: str
    price: float

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = 0.00

app = FastAPI()

def get_db():
    conn = sqlite3.connect('db.sqlite', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def get_customer_service(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Retrieves a JSON representation of a customer in the DB"""
    cursor = db.cursor()

    # Retrieve the customer
    cursor.execute("SELECT name, phone FROM customers where id = ?", (id,))
    data = cursor.fetchone()
    cursor.close()
    if data is None:
        return data
    else:
        customer = CustomerCreate(name=data[0], phone=data[1])
        return customer
    
def get_item_service(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Retrieves a JSON representation of a customer in the DB"""
    cursor = db.cursor()

    # Retrieve the customer
    cursor.execute("SELECT name, price FROM items where id = ?", (id,))
    data = cursor.fetchone()
    cursor.close()
    if data is None:
        return data
    else:
        item = ItemCreate(name=data[0], price=data[1])
        return item
    
def format_phone_number(phone_number):
        """Formats the input phone number string to a standard 'xxx-xxx-xxxx' format."""
        # Remove all non-numeric characters
        digits = re.sub(r"\D", "", phone_number)

        # Format to 'xxx-xxx-xxxx'
        formatted_number = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return formatted_number

def validate_customer_name_length(name):
    if (len(name) > MAXIMUM_NAME_LENGTH):
        return False
    return True

def validate_customer_phone_length(phone):
    phone_length = len(phone)
    if (phone_length < REQUIRED_PHONE_LENGTH or phone_length > REQUIRED_PHONE_LENGTH):
        return False
    return True

def format_price(price):
    return round(price, 2)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/customers")
async def create_customer(customerCreate: CustomerCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates a customer in the DB given a JSON representation"""
    name = customerCreate.name
    phone = customerCreate.phone

    if (not validate_customer_name_length(name)):
        raise HTTPException(status_code=400, detail=f"Customer Name is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.")
    
    if (not validate_customer_phone_length(phone)):
        raise HTTPException(status_code=400, detail=f"Customer Phone is not of required length {REQUIRED_PHONE_LENGTH}.")
    phone = format_phone_number(phone)

    cursor = db.cursor()

    # Insert a new row
    cursor.execute("INSERT INTO customers(name, phone) VALUES (?, ?);", (name, phone))
    
    # Commit the transaction
    db.commit()

    last_id = cursor.lastrowid
    customer = Customer(id=last_id, name=name, phone=phone)

    cursor.close()
    return customer

@app.get("/customers/{id}")
def get_customer(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Retrieves a JSON representation of a customer in the DB"""
    customer = get_customer_service(id, db)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    else:
        return customer
    
@app.delete("/customers/{id}")
def delete_customer(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Deletes a customer in the DB"""
    customer = get_customer_service(id, db)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    cursor = db.cursor()
    cursor.execute("DELETE FROM customers WHERE id = ?", (id,))
    db.commit()
    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(status_code=404, detail="Customer not found")
    cursor.close()
    return f"Successfully deleted customer id {id} with name {customer.name} and phone {customer.phone}."

@app.put("/customers/{id}")
def update_customer(id: str, customerUpdate: CustomerUpdate, db: sqlite3.Connection = Depends(get_db)):
    """Updates a customer in the DB given a JSON representation"""
    customer = get_customer_service(id, db)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    old_name = customer.name
    old_phone = customer.phone

    new_name = customerUpdate.name
    if (new_name is not None):
        if (not validate_customer_name_length(new_name)):
            raise HTTPException(status_code=400, detail=f"Customer new name is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.")
    
    new_phone = customerUpdate.phone
    if (new_phone is not None):
        if (not validate_customer_phone_length(new_phone)):
            raise HTTPException(status_code=400, detail=f"Customer Phone is not of required length {REQUIRED_PHONE_LENGTH}.")
        new_phone = format_phone_number(new_phone)

    cursor = db.cursor()
    if (new_name is not None and new_name != "" and new_phone is None):
        cursor.execute(
            "UPDATE customers SET name = ? WHERE id = ?",
            (new_name, id)
        )
        result_detail = f"Successfully updated customer id {id} with old name {old_name} to new name {new_name}." 
    elif (new_phone is not None and new_phone != "" and new_name is None):
        cursor.execute(
            "UPDATE customers SET phone = ? WHERE id = ?",
            (new_phone, id)
        )
        result_detail = f"Successfully updated customer id {id} with old phone {old_phone} to new phone {new_phone}." 
    else:
        cursor.execute(
            "UPDATE customers SET name = ?, phone = ? WHERE id = ?",
            (new_name, new_phone, id)
        )
        result_detail = f"Successfully updated customer id {id} with old name {old_name} and phone {old_phone} to new name {new_name} and phone {new_phone}." 

    db.commit()
    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(status_code=404, detail="Customer not found")
    cursor.close()

    return result_detail

@app.post("/items")
async def create_item(itemCreate: ItemCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates an item in the DB given a JSON representation"""
    name = itemCreate.name
    price = format_price(itemCreate.price)

    if (not validate_customer_name_length(name)):
        raise HTTPException(status_code=400, detail=f"Item name is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.")

    cursor = db.cursor()

    # Insert a new row
    cursor.execute("INSERT INTO items(name, price) VALUES (?, ?);", (name, price))
    
    # Commit the transaction
    db.commit()

    last_id = cursor.lastrowid
    item = Item(id=last_id, name=name, price=price)

    cursor.close()
    return item

@app.get("/items/{id}")
def get_item(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Retrieves a JSON representation of an item in the DB"""
    item = get_item_service(id, db)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    else:
        return item
    
@app.delete("/items/{id}")
def delete_item(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Deletes an item in the DB"""
    item = get_item_service(id, db)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    cursor = db.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (id,))
    db.commit()
    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.close()
    return f"Successfully deleted item id {id} with name {item.name} and price {item.price}."

@app.put("/items/{id}")
def update_item(id: str, itemUpdate: ItemUpdate, db: sqlite3.Connection = Depends(get_db)):
    """Updates an item in the DB given a JSON representation"""
    item = get_item_service(id, db)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    old_name = item.name
    old_price = item.price

    new_name = itemUpdate.name
    if (new_name is not None):
        if (not validate_customer_name_length(new_name)):
            raise HTTPException(status_code=400, detail=f"Item new name is beyond the maximum allowed length of {MAXIMUM_NAME_LENGTH}.")
    
    new_price = itemUpdate.price
    if (new_price is not None):
        new_price = format_price(new_price)

    cursor = db.cursor()
    if (new_name is not None and new_name != "" and new_price == 0.00):
        cursor.execute(
            "UPDATE items SET name = ? WHERE id = ?",
            (new_name, id)
        )
        result_detail = f"Successfully updated item id {id} with old name {old_name} to new name {new_name}." 
    elif (new_price != 0.00 and new_name is None):
        cursor.execute(
            "UPDATE items SET price = ? WHERE id = ?",
            (new_price, id)
        )
        result_detail = f"Successfully updated item id {id} with old price {old_price} to new price {new_price}." 
    else:
        cursor.execute(
            "UPDATE items SET name = ?, price = ? WHERE id = ?",
            (new_name, new_price, id)
        )
        result_detail = f"Successfully updated item id {id} with old name {old_name} and price {old_price} to new name {new_name} and price {new_price}." 

    db.commit()
    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.close()

    return result_detail