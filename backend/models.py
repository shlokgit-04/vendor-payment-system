from sqlalchemy import Column, Date, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    amount_due = Column(Float, nullable=True)
    due_date = Column(Date, nullable=True)
    payout_status = Column(String, nullable=True)
