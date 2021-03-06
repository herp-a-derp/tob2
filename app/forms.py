
import binascii
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import BooleanField
from wtforms import TextAreaField
from wtforms import PasswordField
from wtforms import RadioField
from wtforms import SelectField
from wtforms import HiddenField
from wtforms.fields import RadioField
from wtforms.validators import DataRequired
from wtforms.validators import Length
from wtforms.validators import Email
from wtforms.validators import EqualTo
from wtforms.validators import ValidationError
from wtforms.validators import URL
from .models import Users
from flask_bcrypt import check_password_hash
from app.models import Users
from app import db

def loginError():
	raise ValidationError("Your username or password is incorrect.")

class LoginForm(FlaskForm):
	username =   StringField('Username', validators=[DataRequired(), Length(min=5)])
	password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
	remember_me = BooleanField('remember_me', default=False)

	# Validate on both the username and password,
	# because we don't want to accidentally leak if a user
	# exists or not
	def validate_password(form, field):
		user = Users.query.filter_by(nickname=form.username.data).first()
		if user is None:
			loginError()

		# Handle flask's new annoying way of mis-packing password strings. Sigh.
		if user.password.startswith("\\x"):
			print("Mis-packed password! Fixing!")
			old = user.password
			user.password = binascii.unhexlify(user.password[2:]).decode("utf-8")
			print("Old: ", old, "new: ", user.password)
			db.session.commit()

		if not check_password_hash(user.password, form.password.data):
			loginError()


class PostForm(FlaskForm):
	title   = StringField('Title',     validators=[DataRequired(), Length(max=128)])
	content = TextAreaField('Content', validators=[DataRequired()])


ratings = [
	('10', '10'),
	( '9',  '9'),
	( '8',  '8'),
	( '7',  '7'),
	( '6',  '6'),
	( '5',  '5'),
	( '4',  '4'),
	( '3',  '3'),
	( '2',  '2'),
	( '1',  '1'),
	( '0',  '0'),
]

class ReviewForm(FlaskForm):
	nickname         = StringField('Nickname',          validators=[DataRequired(), Length(min=5, max=60)])
	overall_rating   = SelectField("Overall Rating",    choices=ratings)
	be_rating        = SelectField("BE Content",        choices=ratings)
	chars_rating     = SelectField("Characters",        choices=ratings)
	technical_rating = SelectField("Technical Quality", choices=ratings)

	comments         = TextAreaField('Comments', validators=[DataRequired(), Length(min=30, max=1000)])

class SearchForm(FlaskForm):
	search = StringField('search', validators=[DataRequired()])

