"""Admin forms for user and role management."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo
from wtforms.widgets import CheckboxInput, ListWidget
from models.role import Role


class MultiCheckboxField(SelectMultipleField):
    """Multi-checkbox field for role selection."""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class UserForm(FlaskForm):
    """Form for creating new users."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')])
    is_active = BooleanField('Active', default=True)
    roles = MultiCheckboxField('Roles', coerce=int)
    submit = SubmitField('Create User')
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.roles.choices = [(role.id, role.name.replace('_', ' ').title()) for role in Role.query.order_by(Role.name).all()]


class UserEditForm(FlaskForm):
    """Form for editing existing users."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password (leave blank to keep current)', validators=[Optional(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[
        EqualTo('password', message='Passwords must match')])
    is_active = BooleanField('Active')
    roles = MultiCheckboxField('Roles', coerce=int)
    submit = SubmitField('Update User')
    
    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.roles.choices = [(role.id, role.name.replace('_', ' ').title()) for role in Role.query.order_by(Role.name).all()]
