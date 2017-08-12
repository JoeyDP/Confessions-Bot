import os
import datetime

from sqlalchemy import create_engine, or_
from sqlalchemy.sql import func
from sqlalchemy import Column, ForeignKey, Integer, Boolean, Enum, String, DateTime, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import sessionmaker, relationship

import app


from util import *

SQLBase = declarative_base()

url = os.environ["DATABASE_URL"]
engine = create_engine(url)
SQLBase.metadata.bind = engine
Session = sessionmaker(bind=engine)


class Base:
    session = Session()

    def add(self):
        app.updateLocale(self.locale)
        Base.session.add(self)
        Base.session.commit()

    def save(self):
        Base.session.commit()

    def delete(self):
        Base.session.delete(self)
        Base.session.commit()


class Page(SQLBase, Base):
    __tablename__ = "page"

    fbID = Column(String(128), primary_key=True)


class Confession(SQLBase, Base):
    __tablename__ = "confession"

    ID = Column(String(128), primary_key=True)


if not engine.dialect.has_table(engine, "page"):
    Page.__table__.create(bind=engine)

if not engine.dialect.has_table(engine, "confession"):
    Confession.__table__.create(bind=engine)