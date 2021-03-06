import os
import datetime
import re

from sqlalchemy import create_engine, or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy import Column, ForeignKey, Integer, Boolean, Enum, String, DateTime, select, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import sessionmaker, relationship

from util import *

SQLBase = declarative_base()

url = os.environ["DATABASE_URL"]
engine = create_engine(url)
SQLBase.metadata.bind = engine
Session = sessionmaker(bind=engine)


class Base:
    session = Session()

    def commit(self):
        try:
            Base.session.commit()
        except:
            Base.session.rollback()
            raise

    def add(self):
        Base.session.add(self)
        self.commit()

    def save(self):
        self.commit()

    def delete(self):
        Base.session.delete(self)
        self.commit()


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
        query = select([func.count(Confession.id)], and_(Confession.page_id==self.fb_id, Confession.status=="pending"))
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
    page_id = Column(String(128), ForeignKey(Page.fb_id, onupdate="CASCADE", ondelete="CASCADE"))
    page = relationship("Page", back_populates="confessions")
    status = Column(Enum("fresh", "pending", "posted", "rejected", name="confessionStatusEnum"), default="fresh")
    text = Column(Text, unique=True)
    time_updated = Column(DateTime, onupdate=datetime.datetime.now)
    fb_id = Column(String(128))
    index = Column(Integer)

    @staticmethod
    def findById(id):
        try:
            confession = Confession.session.query(Confession).filter_by(id=id).one_or_none()
            return confession
        except SQLAlchemyError:
            log("Failed to query for confession with id: " + str(id))
            return

    @staticmethod
    def findByStatus(status):
        return Confession.session.query(Confession).filter_by(status=status).all()

    @staticmethod
    def findByStatusAndPage(status, pageId):
        return Confession.session.query(Confession).filter_by(status=status, page_id=pageId).all()

    @staticmethod
    def getFirstFresh(page_id):
        query = Confession.session.query(Confession)
        query = query.filter_by(page_id=page_id, status="fresh")
        query = query.order_by(Confession.timestamp.asc())
        confession = query.first()
        return confession

    @staticmethod
    def getPending(admin):
        """ Returns all pending confessions of admin. """
        query = Confession.session.query(Confession)
        query = query.filter(Confession.page_id == Page.fb_id)
        query = query.filter(Confession.status == "pending")
        query = query.filter(Page.admin_messenger_id == admin)
        pending = query.all()
        return pending

    @staticmethod
    def getLastIndex(page_id):
        query = Confession.session.query(func.max(Confession.index))
        query = query.filter_by(page_id=page_id)
        result = query.scalar()
        return result if result is not None else 0

    def getReferencedConfession(self):
        result = re.search(r'^(?:\#|\@|\@\#)(\d+)\s', self.text)
        if result:
            index = result.group(1)
            if index:
                try:
                    return self.session.query(Confession).filter_by(page_id=self.page_id, index=index).one_or_none()
                except SQLAlchemyError:
                    log("Failed to query for confession with index: " + str(index))
                    return

    def setPosted(self, fb_id, index):
        self.status = "posted"
        self.fb_id = fb_id
        self.index = index

    def setPending(self):
        self.status = "pending"

    def setRejected(self):
        self.status = "rejected"


if not engine.dialect.has_table(engine, "page"):
    Page.__table__.create(bind=engine)

if not engine.dialect.has_table(engine, "confession"):
    Confession.__table__.create(bind=engine)
