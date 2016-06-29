

from hashlib import md5
import re
from app import db
from sqlalchemy.orm import relationship
from flask_bcrypt import generate_password_hash
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import event
from sqlalchemy.schema import DDL
from sqlalchemy import Table

import sqlalchemy.exc
import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import ENUM
from citext import CIText

# Some of the metaclass hijinks make pylint confused,
# so disable the warnings for those aspects of things
# pylint: disable=E0213, R0903

region_enum  = ENUM('western', 'eastern', 'unknown', name='region_enum')
tl_type_enum = ENUM('oel', 'translated',             name='tl_type_enum')

class StoryBase(object):
	id          = db.Column(db.Integer, primary_key=True)
	title       = db.Column(CIText())
	description = db.Column(db.Text())
	orig_lang   = db.Column(db.Text())

	chapter     = db.Column(db.Float(), default=-1)
	pub_date    = db.Column(db.DateTime)

	fspath      = db.Column(db.Text)
	hash        = db.Column(db.Text, nullable=False)

class TagsBase(object):
	id          = db.Column(db.Integer, primary_key=True)
	@declared_attr
	def story(cls):
		return db.Column(db.Integer, db.ForeignKey('story.id'))
	weight      = db.Column(db.Float, default=1)
	tag         = db.Column(CIText(), nullable=False, index=True)

class GenresBase(object):
	id          = db.Column(db.Integer, primary_key=True)
	@declared_attr
	def story(cls):
		return db.Column(db.Integer, db.ForeignKey('story.id'))
	genre       = db.Column(CIText(), nullable=False, index=True)


class AuthorBase(object):
	id          = db.Column(db.Integer, primary_key=True)
	@declared_attr
	def story(cls):
		return db.Column(db.Integer, db.ForeignKey('story.id'))
	name       = db.Column(CIText(), nullable=False, index=True)



class LanguageBase(object):
	id              = db.Column(db.Integer, primary_key=True)
	language   = db.Column(CIText(), nullable=False, index=True)

class CoversBase(object):
	id          = db.Column(db.Integer, primary_key=True)
	srcfname    = db.Column(db.Text)
	@declared_attr
	def story(cls):
		return db.Column(db.Integer, db.ForeignKey('story.id'))
	volume      = db.Column(db.Float())
	chapter     = db.Column(db.Float())
	fragment    = db.Column(db.Float())
	description = db.Column(db.Text)


class ChangeLogMixin(object):
	operation      = db.Column(db.Text())


class ModificationInfoMixin(object):

	@declared_attr
	def changetime(cls):
		return db.Column(db.DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)

	@declared_attr
	def changeuser(cls):
		return db.Column(db.Integer, db.ForeignKey('users.id'), index=True)





# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class Story(db.Model, StoryBase, ModificationInfoMixin):
	__tablename__ = 'story'

	__table_args__ = (
		db.UniqueConstraint('title'),
		)
	tags           = relationship("Tags",           backref='Story', order_by="Tags.tag")
	genres         = relationship("Genres",         backref='Story')
	author         = relationship("Author",         backref='Story')



class Tags(db.Model, TagsBase, ModificationInfoMixin):
	__tablename__ = 'tags'
	__searchable__ = ['tag']

	__table_args__ = (
		db.UniqueConstraint('story', 'tag'),
		)
	series_row     = relationship("Story",         backref='Tags')

class Genres(db.Model, GenresBase, ModificationInfoMixin):
	__tablename__ = 'genres'
	__searchable__ = ['genre']

	__table_args__ = (
		db.UniqueConstraint('story', 'genre'),
		)
	series_row     = relationship("Story",         backref='Genres')

class Author(db.Model, AuthorBase, ModificationInfoMixin):
	__tablename__ = 'author'
	__searchable__ = ['name']

	__table_args__ = (
		db.UniqueConstraint('story', 'name'),
		)

	series_row       = relationship("Story",         backref='Author')



class Language(db.Model, LanguageBase, ModificationInfoMixin):
	__tablename__ = 'language'
	__table_args__ = (
		db.UniqueConstraint('language'),
		)

class Covers(db.Model, CoversBase, ModificationInfoMixin):
	__tablename__ = 'covers'


class StoryChanges(db.Model, StoryBase, ModificationInfoMixin, ChangeLogMixin):
	__tablename__ = "serieschanges"
	srccol   = db.Column(db.Integer, db.ForeignKey('story.id', ondelete="SET NULL"), index=True)

class TagsChanges(db.Model, TagsBase, ModificationInfoMixin, ChangeLogMixin):
	__tablename__ = "tagschanges"
	srccol   = db.Column(db.Integer, db.ForeignKey('tags.id', ondelete="SET NULL"), index=True)

class GenresChanges(db.Model, GenresBase, ModificationInfoMixin, ChangeLogMixin):
	__tablename__ = "genreschanges"
	srccol   = db.Column(db.Integer, db.ForeignKey('genres.id', ondelete="SET NULL"), index=True)

class AuthorChanges(db.Model, AuthorBase, ModificationInfoMixin, ChangeLogMixin):
	__tablename__ = "authorchanges"
	srccol   = db.Column(db.Integer, db.ForeignKey('author.id', ondelete="SET NULL"), index=True)

class CoversChanges(db.Model, CoversBase, ModificationInfoMixin, ChangeLogMixin):
	__tablename__ = "coverschanges"
	srccol   = db.Column(db.Integer, db.ForeignKey('covers.id', ondelete="SET NULL"), index=True)


class LanguageChanges(db.Model, LanguageBase, ModificationInfoMixin, ChangeLogMixin):
	__tablename__ = "languagechanges"
	srccol   = db.Column(db.Integer, db.ForeignKey('language.id', ondelete="SET NULL"), index=True)


def create_trigger(cls):
	if cls.__tablename__.endswith("changes"):
		print("Not creating triggers on chagetable {name}.".format(name=cls.__tablename__))
		return

	print("Checking triggers exist on table {name}.".format(name=cls.__tablename__))

	# So this is fairly complex. We know that all the local colums (excepting "id") are
	# present in the changes table, however we can't simply say `INSERT INTO changes VALUES SELECT OLD.*`, because
	# the history table has additional columns, and I don't know if I trust any assumptions I make about the ordering anyways.

	colNames = []
	for column in cls.__table__.columns:
		if column.description != "id":
			colNames.append(column.description)

	# id -> srccol, so the backlink works.
	# The names have to be quoted, because some of them are keywords (ex: "group"), and therefore
	# were producing syntax issues
	intoCols = ", ".join(['"{}"'.format(name) for name in colNames+['srccol', 'operation']])

	# The Foreign key is null when we delete
	deleteFromCols = ", ".join(["OLD."+item for item in colNames]+['NULL', ])

	# Otherwise, mirror the new changes into the log table.
	oldFromCols    = ", ".join(["NEW."+item for item in colNames+['id', ]])
	newFromCols    = ", ".join(["NEW."+item for item in colNames+['id', ]])


	rawTrigger = """
		CREATE OR REPLACE FUNCTION {name}_update_func() RETURNS TRIGGER AS ${name}changes$
			BEGIN
				--
				-- Create a row in {name}changes to reflect the operation performed on emp,
				-- make use of the special variable TG_OP to work out the operation.
				--
				IF (TG_OP = 'DELETE') THEN
					INSERT INTO {name}changes ({intoCols}) SELECT {deleteFromCols}, 'D';
					RETURN OLD;
				ELSIF (TG_OP = 'UPDATE') THEN
					INSERT INTO {name}changes ({intoCols}) SELECT {oldFromCols}, 'U';
					RETURN OLD;
				ELSIF (TG_OP = 'INSERT') THEN
					INSERT INTO {name}changes ({intoCols}) SELECT {newFromCols}, 'I';
					RETURN NEW;
				END IF;
				RETURN NULL; -- result is ignored since this is an AFTER trigger
			END;
		${name}changes$ LANGUAGE plpgsql;

		DROP TRIGGER IF EXISTS {name}_change_trigger ON {name};
		CREATE TRIGGER {name}_change_trigger
		AFTER INSERT OR UPDATE OR DELETE ON {name}
			FOR EACH ROW EXECUTE PROCEDURE {name}_update_func();

		""".format(
				name           = cls.__tablename__,
				intoCols       = intoCols,
				deleteFromCols = deleteFromCols,
				oldFromCols    = oldFromCols,
				newFromCols    = newFromCols
				)
	db.engine.execute(
		DDL(
			rawTrigger
		)
	)
	# print(rawTrigger)

trigger_on = [
	Story,
	Tags,
	Genres,
	Author,
	Language,
	Covers,
]

def install_trigram_indice_on_column(table, column):

	idx_name = '{table}_{column}_trigram_idx'.format(table = table.__tablename__, column = column)
	create_idx_sql = '''
	CREATE INDEX
		{idx_name}
	ON
		{table}
	USING
		gin ({column} gin_trgm_ops)'''.format(idx_name=idx_name, table=table.__tablename__, column=column)

	try:
		db.engine.execute('''SELECT '{schema}.{idx}'::regclass;'''.format(schema='public', idx=idx_name))
		print("Do not need to create index", idx_name)
	except sqlalchemy.exc.ProgrammingError:
		# index doesn't exist, need to create it.
		print("Creating index {idx} on table {tbl}".format(idx=idx_name, tbl=table.__tablename__))
		db.engine.execute(
				DDL(
					create_idx_sql
				)
			)

def install_triggers():
	print("Installing triggers!")
	for classDefinition in trigger_on:
		create_trigger(classDefinition)


def install_region_enum(conn):
	print("Installing region enum type!")
	region_enum.create(bind=conn, checkfirst=True)

def install_tl_type_enum(conn):
	print("Installing tl_type enum type!")
	tl_type_enum.create(bind=conn, checkfirst=True)



def install_trigram_indices():
	import sys
	import inspect
	classes = inspect.getmembers(sys.modules[__name__], lambda member: inspect.isclass(member) and member.__module__ == __name__ )
	for dummy_classname, classtype in classes:
		if hasattr(classtype, "__searchable__") and issubclass(classtype, db.Model):
			for column in classtype.__searchable__:

				install_trigram_indice_on_column(classtype, column)



################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################
################################################################################################################################################################

class News_Posts(db.Model):
	__searchable__ = ['body']

	id          = db.Column(db.Integer, primary_key=True)
	title       = db.Column(db.Text)
	body        = db.Column(db.Text)
	timestamp   = db.Column(db.DateTime, index=True)
	user_id     = db.Column(db.Integer, db.ForeignKey('users.id'))
	seriesTopic = db.Column(db.Integer)


	def __repr__(self):  # pragma: no cover
		return '<Post %r (body size: %s)>' % (self.title, len(self.body))



class Ratings(db.Model):
	id          = db.Column(db.Integer, primary_key=True)
	user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
	series_id   = db.Column(db.Integer, db.ForeignKey('story.id'), index=True)
	source_ip   = db.Column(db.Text, index=True)

	rating      = db.Column(db.Float(), default=-1)

	__table_args__ = (
		db.UniqueConstraint('user_id', 'source_ip', 'series_id'),
		db.CheckConstraint('rating >=  0', name='rating_min'),
		db.CheckConstraint('rating <= 10', name='rating_max'),
		db.CheckConstraint('''(user_id IS NOT NULL AND source_ip IS NULL) OR (user_id IS NULL AND source_ip IS NOT NULL)''', name='rating_src'),
	)


	series_row       = relationship("Story",         backref='Ratings')


class Users(db.Model):
	id         = db.Column(db.Integer, primary_key=True)
	nickname   = db.Column(CIText(),  index=True, unique=True)
	password   = db.Column(db.String,  index=True, unique=True)
	email      = db.Column(db.String,  index=True, unique=True)
	verified   = db.Column(db.Integer, nullable=False)

	last_seen  = db.Column(db.DateTime)

	has_admin  = db.Column(db.Boolean, default=False)
	has_mod    = db.Column(db.Boolean, default=False)

	news_posts = db.relationship('News_Posts')
	# posts     = db.relationship('Post', backref='author', lazy='dynamic')


	@staticmethod
	def make_valid_nickname(nickname):
		return re.sub(r'[^a-zA-Z0-9_\.\-]', '', nickname)

	@staticmethod
	def make_unique_nickname(nickname):
		if Users.query.filter_by(nickname=nickname).first() is None:
			return nickname
		version = 2
		while True:
			new_nickname = nickname + str(version)
			if Users.query.filter_by(nickname=new_nickname).first() is None:
				break
			version += 1
		return new_nickname

	def is_authenticated(self):
		return self.verified

	def is_active(self):
		return self.verified

	def is_admin(self):
		return self.has_admin

	def is_mod(self):
		return self.has_mod

	def is_anonymous(self):
		return False

	def get_id(self):
		return str(self.id)  # python 3

	def avatar(self, size):
		return 'http://www.gravatar.com/avatar/%s?d=mm&s=%d' % \
			(md5(self.email.encode('utf-8')).hexdigest(), size)


	def __repr__(self):  # pragma: no cover
		return '<User -- %r>' % (self.nickname)

	def __init__(self, nickname, email, password, verified):
		self.nickname  = nickname
		self.email     = email
		self.password  = generate_password_hash(password)
		self.verified  = verified

class HttpRequestLog(db.Model):
	id             = db.Column(db.Integer, primary_key=True)
	access_time    = db.Column(db.DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)
	path           = db.Column(db.String)
	user_agent     = db.Column(db.String)
	referer        = db.Column(db.String)
	forwarded_for  = db.Column(db.String)
	originating_ip = db.Column(db.String)
