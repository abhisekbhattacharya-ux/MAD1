from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, FloatField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange

# ------------------- User Registration -------------------
class RegisterForm(FlaskForm):
    fullname = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    address = StringField('Address')
    pincode = StringField('Pin Code')
    submit = SubmitField('Sign-Up')

# ------------------- User Login -------------------
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# ------------------- Edit Profile -------------------
class EditProfileForm(FlaskForm):
    fullname = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])    
    address = StringField('Address')
    pincode = StringField('Pin Code')
    submit = SubmitField('Update')

# ------------------- Add Parking Lot -------------------
class AddLotForm(FlaskForm):
    prime_location_name = StringField('Location Name', validators=[DataRequired()])
    address = StringField('Address')
    pin_code = StringField('Pin Code')
    maximum_spots = IntegerField('Maximum Number of Spots', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Lot')

# ------------------- Add Parking Spot -------------------
class AddSpotForm(FlaskForm):
    lot_id = SelectField('Parking Lot', coerce=int, validators=[DataRequired()])
    spot_number = StringField('Spot Number', validators=[DataRequired()])
    status = SelectField('Status', choices=[('A', 'Available'), ('O', 'Occupied')], validators=[DataRequired()])
    submit = SubmitField('Add Spot')

# ------------------- Reserve Spot -------------------
class ReserveSpotForm(FlaskForm):
    lot = SelectField('Select Parking Lot', coerce=int, validators=[DataRequired()])
    spot = SelectField('Select Spot', coerce=int, validators=[DataRequired()])
    start_time = DateTimeField('Start Time (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    end_time = DateTimeField('End Time (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_end_time(form, field):
        if field.data <= form.start_time.data:
            raise ValidationError('End time must be after start time.')

