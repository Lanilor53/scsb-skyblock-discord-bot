from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///bazaar_data.db', echo=False)

BAZAAR_PRODUCTS_TABLE_NAME = 'bazaar_products'

if not engine.dialect.has_table(engine, BAZAAR_PRODUCTS_TABLE_NAME):  # If table don't exist, Create.
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
class TimestampedBazaarProduct(Base):
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
    products = bazaar_data["products"]
    timestamp = bazaar_data["lastUpdated"]
    session = Session()
    for product_name in products.keys():
        product = products[product_name]
        quick_status = product["quick_status"]
        bazaar_product = TimestampedBazaarProduct(product_id=product["product_id"],
                                                  timestamp=timestamp,
                                                  sell_price=quick_status["sellPrice"],
                                                  sell_volume=quick_status["sellVolume"],
                                                  sell_moving_week=quick_status["sellMovingWeek"],
                                                  sell_orders=quick_status["sellOrders"],
                                                  buy_price=quick_status["buyPrice"],
                                                  buy_volume=quick_status["buyVolume"],
                                                  buy_moving_week=quick_status["buyMovingWeek"],
                                                  buy_orders=quick_status["buyOrders"],
                                                  )
        session.add(bazaar_product)
    session.commit()


# TODO: add "byTimestamp"
def get_all_products_batches():
    session = Session()
    session.query(TimestampedBazaarProduct).all()
    session.commit()


def get_last_products_batch():
    session = Session()
    last_timestamp = (
        session.query(TimestampedBazaarProduct.timestamp, func.max(TimestampedBazaarProduct.timestamp))
        .limit(1)
        .one_or_none()
    )[0]
    if last_timestamp is None:
        print("[!!!!!!] " + str(last_timestamp))
        raise
    last_batch = (
        session.query(TimestampedBazaarProduct)
        .filter(TimestampedBazaarProduct.timestamp == last_timestamp)
        .all()
    )
    session.commit()
    return last_batch
