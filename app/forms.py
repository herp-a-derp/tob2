
import binascii
from flask_wtf import Form
from wtforms import StringField
from wtforms import BooleanField
from wtforms import TextAreaField
from wtforms import PasswordField
from wtforms import RadioField
from wtforms import SelectField
from wtforms import HiddenField
from wtforms.fields import RadioField
from wtforms.fields.html5 import DateTimeField
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

class LoginForm(Form):
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


class PostForm(Form):
	title   = StringField('Title',     validators=[DataRequired(), Length(max=128)])
	content = TextAreaField('Content', validators=[DataRequired()])


ratings = [
	( 0,  0),
	( 1,  1),
	( 2,  2),
	( 3,  3),
	( 4,  4),
	( 5,  5),
	( 6,  6),
	( 7,  7),
	( 8,  8),
	( 9,  9),
	(10, 10),
]

class ReviewForm(Form):
	nickname         = StringField('Nickname',   validators=[DataRequired(), Length(min=5, max=30)])
	overall_rating   = RadioField("Overall Rating", choices=ratings)
	be_rating        = RadioField("BE Content", choices=ratings)
	chars_rating     = RadioField("Characters", choices=ratings)
	technical_rating = RadioField("Technical Quality", choices=ratings)

	comments         = TextAreaField('Comments', validators=[DataRequired(), Length(min=5, max=1000)])

class SearchForm(Form):
	search = StringField('search', validators=[DataRequired()])

