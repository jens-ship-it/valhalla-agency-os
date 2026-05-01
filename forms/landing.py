"""Landing page forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class DemoRequestForm(FlaskForm):
    """Demo request form for landing page."""
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    company = StringField('Company', validators=[Optional(), Length(max=100)])
    team_size = SelectField('Team Size', 
        choices=[
            ('', 'Select team size...'),
            ('1-10', '1-10 people'),
            ('11-50', '11-50 people'),
            ('51-200', '51-200 people'),
            ('201+', '201+ people')
        ],
        validators=[Optional()])
    notes = TextAreaField('Tell us about your needs', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Request a Demo')
