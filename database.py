import os
import datetime

from sqlalchemy import create_engine, or_
from sqlalchemy.sql import func
from sqlalchemy import Column, ForeignKey, Integer, Boolean, Enum, String, DateTime, select, Text
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
        Base.session.add(self)
        Base.session.commit()

    def save(self):
        Base.session.commit()

    def delete(self):
        Base.session.delete(self)
        Base.session.commit()


class Page(SQLBase, Base):
    __tablename__ = "page"

    fb_id = Column(String(128), primary_key=True)
    name = Column(String(255))
    token = Column(String(255))
    admin_messenger_id = Column(String(128))
    confessions = relationship("Confession", back_populates="page")

    @staticmethod
    def findById(fb_id):
        page = Page.session.query(Page).filter_by(fb_id=fb_id).one_or_none()
        return page

    def getFirstFreshConfession(self):
        return Confession.getFirstFresh(self.fb_id)

    def hasPendingConfession(self):
        query = Confession.session.query(func.count(Confession.fb_id))
        query.filter_by(page_id=self.fb_id)
        amount = query.scalar()
        return amount > 0

    def addConfession(self, text):
        c = Confession()
        c.page = self
        c.text = text
        return c


""" 
Enum for status of confession. Values are:
 - fresh:       Received from form, but not handled yet. (default) 
 - pending:     Sent to admin for processing, but no answer yet.
 - posted:      Posted on the Facebook page.
 - rejected:    Discarded by admin.
"""
class Confession(SQLBase, Base):
    __tablename__ = "confession"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    page_id = Column(String(128), ForeignKey(Page.fb_id))
    page = relationship("Page", back_populates="confessions")
    status = Column(Enum("fresh", "pending", "posted", "rejected", name="confessionStatusEnum"), default="fresh")
    text = Column(Text)
    time_updated = Column(DateTime, onupdate=datetime.datetime.now)
    fb_id = Column(String(128))

    @staticmethod
    def findById(id):
        confession = Confession.session.query(Confession).filter_by(id=id).one_or_none()
        return confession

    @staticmethod
    def getFirstFresh(page_id):
        query = Confession.session.query(Confession)
        query.filter_by(page_id=page_id, status="fresh")
        query.order_by(Confession.timestamp.asc())
        confession = query.first()
        return confession

    def setPosted(self, fb_id):
        self.status = "posted"
        self.fb_id = fb_id

    def setPending(self):
        self.status = "pending"

    def setRejected(self):
        self.status = "rejected"


if not engine.dialect.has_table(engine, "page"):
    Page.__table__.create(bind=engine)

if not engine.dialect.has_table(engine, "confession"):
    Confession.__table__.create(bind=engine)
