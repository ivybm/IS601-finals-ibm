from typing import Optional, Union
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import re
import sqlite3


import uvicorn

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
    
def format_phone_number(phone_number):
        """Formats the input phone number string to a standard 'xxx-xxx-xxxx' format."""
        # Remove all non-numeric characters
        digits = re.sub(r"\D", "", phone_number)

        # Format to 'xxx-xxx-xxxx'
        formatted_number = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return formatted_number

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/customers")
async def create_customer(customerCreate: CustomerCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates a customer in the DB given a JSON representation"""
    name = customerCreate.name
    phone = format_phone_number(customerCreate.phone)
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
    new_phone = customerUpdate.phone
    if (new_phone is not None):
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



