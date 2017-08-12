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
import matcher

Base = declarative_base()

url = os.environ["DATABASE_URL"]
engine = create_engine(url)
Base.metadata.bind = engine
Session = sessionmaker(bind=engine)


class Matches(Base):
    __tablename__ = "matches"
    person1 = Column(String(128), ForeignKey("person.fbID", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    person2 = Column(String(128), ForeignKey("person.fbID", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)


class Person(Base):
    __tablename__ = "person"
    fbID = Column(String(128), primary_key=True)
    appID = Column(String(128))
    firstName = Column(String(255), default="")
    lastName = Column(String(255), default="")
    locale = Column(String(16), default="en_US")
    gender = Column(Enum("Male", "Female", name="genderEnum"))
    requestedGender = Column(Enum("Male", "Female", "Both", name="requestedGenderEnum"))
    useCondom = Column(Enum("Yes", "No", "Both", name="condomEnum"))
    complete = Column(Boolean, default=False)
    isLooking = Column(Boolean, default=False)
    startedLooking = Column(DateTime)

    matches = relationship("Person",
                           secondary="matches",
                           primaryjoin=Matches.person1 == fbID,
                           secondaryjoin=Matches.person2 == fbID)

    chatContact = Column(String(128), ForeignKey("person.fbID", onupdate="CASCADE", ondelete="SET NULL"))

    @property
    def chatContactPerson(self):
        if self.chatContact:
            return Person.findByFb(self.chatContact, forceNoLocaleUpdate=True)
        return None

    fillable = ["gender", "requestedGender", "useCondom"]
    session = Session()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app.updateLocale(self.locale)

    def isComplete(self):
        if not self.complete:
            self.complete = len(self.getMissingValues()) == 0
            self.save()
        return self.complete

    @property
    def fullName(self):
        return str(self.firstName) + " " + str(self.lastName)

    def getMissingValues(self):
        return list(filter(lambda attribute: not self.__getattribute__(attribute), Person.fillable))

    def setValue(self, attribute, value):
        self.__setattr__(attribute, value)
        self.save()

    def startLooking(self):
        self.isLooking = True
        self.startedLooking = datetime.datetime.now()

    def stopLooking(self):
        self.isLooking = False
        self.startedLooking = None

    def getCandidateMatches(self):
        query = Person.session.query(Person).filter(or_(Person.requestedGender == self.gender, Person.requestedGender == "Both"))
        query = query.filter(Person.fbID != self.fbID)
        query = query.filter(~Person.allMatches.any(Person.fbID == self.fbID))
        query = query.filter_by(isLooking=True, complete=True)
        if self.requestedGender != "Both":
            query = query.filter_by(gender=self.requestedGender)
        if self.useCondom != "Both":
            query = query.filter(or_(Person.useCondom == self.useCondom, Person.useCondom == "Both"))
        query = query.order_by(Person.startedLooking.asc())
        candidateMatches = query.all()
        return candidateMatches

    # deprecated
    def getNewMatch(self):
        candidateMatches = self.getCandidateMatches()
        return matcher.selectMatch(candidateMatches)

    def addMatch(self, match):
        self.matches.append(match)

    def getLastMatchTime(self):
        last = Person.session.query(func.max(Matches.timestamp)).filter(or_(Matches.person1 == self.fbID, Matches.person2 == self.fbID)).first()[0]
        log("last match: " + str(last))
        return last

    def canChatWith(self, contactID, maxMessages):
        myMessages = Person.session.query(ChatCount).filter_by(person=self.fbID, contact=contactID).one_or_none()
        myMessages = myMessages.count if myMessages else 0

        if myMessages >= maxMessages:
            return False
        return True

    def sentMessageTo(self, contactID):
        myMessages = Person.session.query(ChatCount).filter_by(person=self.fbID, contact=contactID).one_or_none()
        if not myMessages:
            myMessages = ChatCount(person=self.fbID, contact=contactID, count=0)
            Person.session.add(myMessages)
        myMessages.count += 1

        theirMessages = Person.session.query(ChatCount).filter_by(person=contactID, contact=self.fbID).one_or_none()
        if not theirMessages:
            theirMessages = ChatCount(person=contactID, contact=self.fbID, count=0)
            Person.session.add(theirMessages)
        theirMessages.count = 0

    @staticmethod
    def findByFb(fbID, forceNoLocaleUpdate=False):
        person = Person.session.query(Person).filter_by(fbID=fbID).one_or_none()
        if person and not forceNoLocaleUpdate:
            app.updateLocale(person.locale)
        return person

    @staticmethod
    def everyone():
        people = Person.session.query(Person).all()
        return people

    def add(self):
        app.updateLocale(self.locale)
        Person.session.add(self)
        Person.session.commit()

    def save(self):
        Person.session.commit()

    def delete(self):
        Person.session.delete(self)
        Person.session.commit()


# this relationship is viewonly and selects across the union of all matches
matchesUnion = select([
    Matches.person1,
    Matches.person2,
]).union(
    select([
        Matches.person2,
        Matches.person1,
    ])
).alias()

Person.allMatches = relationship('Person',
                                 secondary=matchesUnion,
                                 primaryjoin=Person.fbID == matchesUnion.c.person1,
                                 secondaryjoin=Person.fbID == matchesUnion.c.person2,
                                 viewonly=True)


class ChatCount(Base):
    __tablename__ = "chat_count"
    person = Column(String(128), ForeignKey("person.fbID", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    contact = Column(String(128), ForeignKey("person.fbID", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    count = Column(Integer, default=0)


if not engine.dialect.has_table(engine, "person"):
    Person.__table__.create(bind=engine)
#    Base.metadata.create_all(engine)

if not engine.dialect.has_table(engine, "matches"):
    Matches.__table__.create(bind=engine)

if not engine.dialect.has_table(engine, "chat_count"):
    ChatCount.__table__.create(bind=engine)
