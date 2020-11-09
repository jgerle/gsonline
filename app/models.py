import base64
from datetime import datetime, timedelta
from hashlib import md5
import json
import os
from time import time
from flask import current_app, url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import redis
import rq
from wtforms.fields.core import BooleanField
from app import db, login
from app.search import add_to_index, remove_from_index, query_index
import enum

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(UserMixin, PaginatedAPIMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()

    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() + 'Z',
            'about_me': self.about_me,
            'post_count': self.posts.count(),
            'follower_count': self.followers.count(),
            'followed_count': self.followed.count(),
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'followers': url_for('api.get_followers', id=self.id),
                'followed': url_for('api.get_followed', id=self.id),
                'avatar': self.avatar(128)
            }
        }
        if include_email:
            data['email'] = self.email
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(SearchableMixin, db.Model):
    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

##
## OpenGS data
##
class ProcessType(enum.Enum):
    CORE = "Kerngeschäft"
    SUPPORTING = "Unterstützend"

class NetworkCriticality(enum.Enum):
    K1 = "Außenverbindung"
    K2 = "hohe Vertraulichkeit"
    K3 = "hohe Integrität"
    K4 = "hohe Verfügbarkeit"
    K5 = "keine Übertragung"

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Infodomain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    organization = db.relationship('Organization', backref='infodomains')

class Coreprocess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text(256))
    type = db.Column(db.Enum(ProcessType))
    user = db.Column(db.Integer, db.ForeignKey('person.id'))

    # Foreign Relations
    responsible = db.Column(db.Integer, db.ForeignKey('person.id'))
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='coreprocesses')
    applications = db.relationship("AssociationProcApp", back_populates="coreprocess")

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))

    # Foreign Relations
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='applications')
    coreprocesses = db.relationship("AssociationProcApp", back_populates="application")
    systems = db.relationship("AssociationAppSys", back_populates="application")

class AssociationProcApp(db.Model):
    __tablename__ = 'association_proc_app'
    coreprocess_id = db.Column(db.Integer, db.ForeignKey('coreprocess.id'), primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), primary_key=True)
    relation_type = db.Column(db.String(50))

    # Foreign Relations
    application = db.relationship("Application", back_populates="coreprocesses")
    coreprocess = db.relationship("Coreprocess", back_populates="applications")

class System(db.Model):
    # TODO: Seite 93, 88 im 200.2er
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    number = db.Column(db.Integer())

    # Foreign Relations
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='systems')
    applications = db.relationship("AssociationAppSys", back_populates="system")
    networks = db.relationship("AssociationSysNet", back_populates="system")
    rooms = db.relationship("AssociationSysRoom", back_populates="system")

class AssociationAppSys(db.Model):
    __tablename__ = 'association_app_sys'
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('system.id'), primary_key=True)
    relation_type = db.Column(db.String(50))
    system = db.relationship("System", back_populates="applications")
    application = db.relationship("Application", back_populates="systems")

class Network(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    is_external = db.Column(db.Boolean, unique=False, default=False)
    # Foreign Relations
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='networks')
    systems = db.relationship("AssociationSysNet", back_populates="network")

class AssociationSysNet(db.Model):
    __tablename__ = 'association_sys_net'
    system_id = db.Column(db.Integer, db.ForeignKey('system.id'), primary_key=True)
    network_id = db.Column(db.Integer, db.ForeignKey('network.id'), primary_key=True)
    relation_type = db.Column(db.String(50))
    system = db.relationship("System", back_populates="networks")
    network = db.relationship("Network", back_populates="systems")

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='rooms')
    systems = db.relationship("AssociationSysRoom", back_populates="room")

class AssociationSysRoom(db.Model):
    __tablename__ = 'association_sys_room'
    system_id = db.Column(db.Integer, db.ForeignKey('system.id'), primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), primary_key=True)
    relation_type = db.Column(db.String(50))
    system = db.relationship("System", back_populates="rooms")
    room = db.relationship("Room", back_populates="systems")

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='persons')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    dom_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    dom = db.relationship('Infodomain', backref='documents')

##
## OpenGS BSI Components ^= Grundschutzkompendium
##
class ProtectionLevel(enum.Enum):
    BASE = "Basis"
    STANDARD = "Standard"
    HIGH = "Hoch"

class ImplementationPriority(enum.Enum):
    """ Empfohlene Bearbeitungsreihenfolge der Bausteine """
    R1 = "Prio 1"
    R2 = "Prio 2"
    R3 = "Prio 3"

class Catalogue(db.Model):
    """ Rahmenwerk / Katalog, z.B. BSI Grundschutz Kompendium, Edition 2020 """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)

class Threat(db.Model):
    """ Elementare Gefährdungen, z.B. G 0.<id=1> Feuer """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)

class BuildingBlockGroup(db.Model):
    """ ISMS, ORG, CON, SYS, ... """
    __tablename__ = 'buildingblockgroup'
    id = db.Column(db.Integer, primary_key=True)
    shorthand = db.Column(db.String(4), index=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text())

    # ForeignKeys
    catalogue_id = db.Column(db.Integer, db.ForeignKey('catalogue.id'))
    catalogue = db.relationship('Catalogue', backref='buildingblockgroups')

class BuildingBlock(db.Model):
    """ Beispiel: SYS.1.1 Allgemeiner Server """
    __tablename__ = 'buildingblock'
    id = db.Column(db.Integer, primary_key=True)
    prio = db.Column(db.Enum(ImplementationPriority))
    order = db.Column(db.String(10))
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text())
    is_active = db.Column(db.Boolean, unique=False, default=True)

    # ForeignKeys
    buildingblockgroup_id = db.Column(db.Integer, db.ForeignKey('buildingblockgroup.id'))
    buildingblockgroup = db.relationship('BuildingBlockGroup', backref='buildingblocks')

class Requirement(db.Model):
    """ Beispiel: SYS.1.1.A1 Geeignete Aufstellung """
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer())
    protection_level = db.Column(db.Enum(ProtectionLevel))
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text())
    is_active = db.Column(db.Boolean, unique=False, default=True)

    # ForeignKeys
    buildingblock_id = db.Column(db.Integer, db.ForeignKey('buildingblock.id'))
    buildingblock = db.relationship('BuildingBlock', backref='requirements')

class Action(db.Model):
    """ Beispiel: Server MÜSSEN an Orten betrieben werden, zu denen nur berechtigte Personen Zutritt haben. """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.Text())

    # ForeignKeys
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirement.id'))
    requirement = db.relationship('Requirement', backref='actions')

##
##  OpenGS Grundschutz Modellierung
##

class ImplementationDecision(enum.Enum):
    NA = "n/a"
    YES = "ja"
    PART = "teilw."
    NO = "nein"

class ImplementationStatus(enum.Enum):
    OPEN = "offen"
    WIP = "in Arbeit"
    DONE = "erledigt"

class GsModelBase(db.Model):
    """ Basisinformationen zur Abbildung der Modellierung pro Informationsverbund """

    __tablename__ = 'gsmodelbase'

    id = db.Column(db.Integer, primary_key=True)
    bb_id = db.Column(db.Integer, db.ForeignKey('buildingblock.id'), nullable=False)
    dom_id= db.Column(db.Integer, db.ForeignKey('infodomain.id'), nullable=False)
    buildingblock = db.relationship('BuildingBlock', backref='models')
    type = db.Column(db.String(50))

    __mapper_args__ = {
        'polymorphic_identity':'gsmodelbase',
        'polymorphic_on':type
    }

""" Verknüpfung Bausteine zu Zielobjekten """

class GsModelDom(GsModelBase, db.Model):
    __tablename__ = 'gsmodeldom'

    id = db.Column(db.Integer, db.ForeignKey('gsmodelbase.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity':'gsmodeldom',
    }

class GsModelApp(GsModelBase, db.Model):
    __tablename__ = 'gsmodelapp'

    id = db.Column(db.Integer, db.ForeignKey('gsmodelbase.id'), primary_key=True)
    application_id= db.Column(db.Integer, db.ForeignKey('application.id'))
    application = db.relationship('Application', backref='gsmodelapp')

    __mapper_args__ = {
        'polymorphic_identity':'gsmodelapp',
    }

class GsModelSys(GsModelBase, db.Model):
    __tablename__ = 'gsmodelsys'

    id = db.Column(db.Integer, db.ForeignKey('gsmodelbase.id'), primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('system.id'))
    system = db.relationship('System', backref='gsmodelsys')

    __mapper_args__ = {
        'polymorphic_identity':'gsmodelsys',
    }

class GsModelNet(GsModelBase, db.Model):
    __tablename__ = 'gsmodelnet'

    id = db.Column(db.Integer, db.ForeignKey('gsmodelbase.id'), primary_key=True)
    network_id= db.Column(db.Integer, db.ForeignKey('network.id'))
    network = db.relationship('Network', backref='gsmodelnet')

    __mapper_args__ = {
        'polymorphic_identity':'gsmodelnet',
    }

class GsModelRoom(GsModelBase, db.Model):
    __tablename__ = 'gsmodelroom'

    id = db.Column(db.Integer, db.ForeignKey('gsmodelbase.id'), primary_key=True)
    room_id= db.Column(db.Integer, db.ForeignKey('room.id'))
    room = db.relationship('Room', backref='gsmodelroom')

    __mapper_args__ = {
        'polymorphic_identity':'gsmodelroom',
    }

class Checklist(db.Model):
    __tablename__ = 'checklist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)

    infodomain_id = db.Column(db.Integer, db.ForeignKey('infodomain.id'))
    infodomain = db.relationship('Infodomain', backref='checklists')
    
    gsmodelbase_id = db.Column(db.Integer, db.ForeignKey('gsmodelbase.id'))
    gsmodelbase = db.relationship('GsModelBase', backref='checklists')
    
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # vllt besser https://sqlalchemy-utils.readthedocs.io/en/latest/aggregates.html ???
    #@property
    #def checklistitem_count(self):
    #   return db.object_session(self).query(ChecklistItem).with_parent(self).count()

class ChecklistItem(db.Model):
    __tablename__ = 'checklistitem'

    id = db.Column(db.Integer, primary_key=True)
    
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklist.id'))
    checklist = db.relationship('Checklist', backref='checklistitems')

    requirement_id = db.Column(db.Integer, db.ForeignKey('requirement.id'))
    requirement = db.relationship('Requirement', backref='checklistitems')

    implementation_decision = db.Column(db.Enum(ImplementationDecision))
    responsible = db.Column(db.Integer, db.ForeignKey('person.id'))
    comments = db.Column(db.Text())
    est_amount = db.Column(db.Float())
    target_date = db.Column(db.Date())
    implementation_status = db.Column(db.Enum(ImplementationStatus))