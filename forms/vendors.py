"""Vendor management forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, URL


class VendorSearchForm(FlaskForm):
    """Form for searching vendors."""
    q = StringField('Search', validators=[Optional(), Length(max=200)])
    vendor_type = SelectField('Vendor Type', choices=[('', 'All Types')], validators=[Optional()])
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('all', 'All')
    ], default='active', validators=[Optional()])


class VendorForm(FlaskForm):
    """Form for creating and editing vendors."""
    name = StringField('Vendor Name', validators=[DataRequired(), Length(max=200)])
    vendor_type = SelectField('Vendor Type', choices=[
        ('broker_partner', 'Broker Partner'),
        ('general_agent', 'General Agent'),
        ('insurer', 'Insurer'),
        ('administration_services', 'Administration Services'),
        ('mgu', 'MGU'),
        ('pbm', 'PBM'),
        ('consultant', 'Consultant'),
        ('actuary', 'Actuary'),
        ('attorney', 'Attorney')
    ], validators=[DataRequired()])
    role_description = TextAreaField('Role Description')
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Length(max=120)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=2)])
    zip = StringField('ZIP Code', validators=[Optional(), Length(max=10)])
    website = StringField('Website', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('Notes')
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    submit = SubmitField('Save Vendor')