import logging
import time

from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import items

log = logging.getLogger(__name__)

# Set up database

engine = create_engine('sqlite:///bazaar_data.db', echo=False)
BAZAAR_PRODUCTS_TABLE_NAME = 'bazaar_products'
if not engine.dialect.has_table(engine, BAZAAR_PRODUCTS_TABLE_NAME):  # if table don't exist, create it
    metadata = MetaData(engine)
    # Create a table with the appropriate Columns
    Table(BAZAAR_PRODUCTS_TABLE_NAME, metadata,
          Column('id', Integer, primary_key=True),
          Column('product_id', String),
          Column('timestamp', Integer),
          Column('sell_price', Float),
          Column('sell_volume', Integer),
          Column('sell_moving_week', Integer),
          Column('sell_orders', Integer),
          Column('buy_price', Float),
          Column('buy_volume', Integer),
          Column('buy_moving_week', Integer),
          Column('buy_orders', Integer),
          )
    # Implement the creation
    metadata.create_all()
Session = sessionmaker(bind=engine)
Base = declarative_base()


# TODO: implement sell_ and buy_ summaries
class BazaarProduct(Base):
    __tablename__ = BAZAAR_PRODUCTS_TABLE_NAME

    id = Column(Integer, primary_key=True)
    product_id = Column(String)
    timestamp = Column(Integer)
    # Quick summary
    sell_price = Column(Float)
    sell_volume = Column(Integer)
    sell_moving_week = Column(Integer)
    sell_orders = Column(Integer)
    buy_price = Column(Float)
    buy_volume = Column(Integer)
    buy_moving_week = Column(Integer)
    buy_orders = Column(Integer)


def add_products_batch(bazaar_data):
    products_data = bazaar_data["products"]
    session = Session()
    item_list = []
    timestamp = int(time.time() * 1000)
    for product_name in products_data.keys():
        product = products_data[product_name]
        quick_status = product["quick_status"]
        bazaar_product = BazaarProduct(product_id=product["product_id"],
                                       sell_price=quick_status["sellPrice"],
                                       sell_volume=quick_status["sellVolume"],
                                       sell_moving_week=quick_status["sellMovingWeek"],
                                       sell_orders=quick_status["sellOrders"],
                                       buy_price=quick_status["buyPrice"],
                                       buy_volume=quick_status["buyVolume"],
                                       buy_moving_week=quick_status["buyMovingWeek"],
                                       buy_orders=quick_status["buyOrders"],
                                       timestamp=timestamp
                                       )
        session.add(bazaar_product)
        try:
            item_list.append(items.Item(bazaar_product))
        except items.ItemNotFoundError:
            continue
    session.commit()
    return items.ItemBatch(item_list, timestamp)


def get_all_products_batches():
    session = Session()
    timestamps = items.timestamps
    batches = []
    for ts in timestamps:
        q = session.query(BazaarProduct).filter(BazaarProduct.timestamp == ts).all()
        items_list = []
        for i in q:
            try:
                items_list.append(items.Item(i))
            except items.ItemNotFoundError:
                continue
        ib = items.ItemBatch(items_list, ts)
        batches.append(ib)
    session.commit()
    return batches
