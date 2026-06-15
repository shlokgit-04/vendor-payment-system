from fastapi import FastAPI
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Base, Vendor

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "Vendor Payment System"}


# CREATE
@app.post("/vendors")
def create_vendor(vendor: dict):
    db = SessionLocal()

    new_vendor = Vendor(
        name=vendor["name"],
        email=vendor["email"],
        phone=vendor["phone"]
    )

    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)

    db.close()

    return {
        "id": new_vendor.id,
        "name": new_vendor.name,
        "email": new_vendor.email,
        "phone": new_vendor.phone
    }


# READ
@app.get("/vendors")
def get_vendors():
    db = SessionLocal()

    vendors = db.query(Vendor).all()

    result = []

    for vendor in vendors:
        result.append({
            "id": vendor.id,
            "name": vendor.name,
            "email": vendor.email,
            "phone": vendor.phone
        })

    db.close()

    return result


# UPDATE
@app.put("/vendors/{vendor_id}")
def update_vendor(vendor_id: int, vendor: dict):
    db = SessionLocal()

    existing_vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id
    ).first()

    if not existing_vendor:
        db.close()
        return {"error": "Vendor not found"}

    existing_vendor.name = vendor["name"]
    existing_vendor.email = vendor["email"]
    existing_vendor.phone = vendor["phone"]

    db.commit()

    db.close()

    return {"message": "Vendor updated successfully"}


# DELETE
@app.delete("/vendors/{vendor_id}")
def delete_vendor(vendor_id: int):
    db = SessionLocal()

    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id
    ).first()

    if not vendor:
        db.close()
        return {"error": "Vendor not found"}

    db.delete(vendor)
    db.commit()

    db.close()

    return {"message": "Vendor deleted successfully"}
