from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import pytz
from config import DATABASE_URL

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String)
    discount = Column(String)
    price = Column(String)
    image = Column(String)
    rating = Column(String)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone("Asia/Kolkata"))
    )


class ProductRepo:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_table(self):
        Base.metadata.create_all(bind=self.engine)

    def add_product(
        self,
        product_id: str,
        product_name: str = None,
        price: str = None,
        image: str = None,
        rating: str = None,
        discount: str = None,
    ):
        session = self.SessionLocal()
        session.add(
            Product(
                id=product_id,
                product_name=product_name,
                discount=discount,
                price=price,
                image=image,
                rating=rating,
            )
        )
        session.commit()

    def get_all_products(self):
        session = self.SessionLocal()
        products = session.query(Product).all()
        session.close()
        return products
