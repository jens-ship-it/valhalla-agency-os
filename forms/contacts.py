"""Contact management forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email


class ContactForm(FlaskForm):
    """Form for creating and editing contacts."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    mobile = StringField('Mobile', validators=[Optional(), Length(max=20)])
    notes = TextAreaField('Notes')
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    submit = SubmitField('Save Contact')


class ContactLinkForm(FlaskForm):
    """Form for linking contacts to entities."""
    contact_id = SelectField('Contact', coerce=int, validators=[DataRequired()])
    entity_type = SelectField('Entity Type', choices=[
        ('organization', 'Organization'),
        ('individual', 'Individual'),
        ('vendor', 'Vendor')
    ], validators=[DataRequired()])
    entity_id = SelectField('Entity', coerce=int, validators=[DataRequired()])
    role_at_entity = StringField('Role at Entity', validators=[Optional(), Length(max=100)])
    is_primary = SelectField('Primary Contact', choices=[('false', 'No'), ('true', 'Yes')], default='false')
    submit = SubmitField('Link Contact')
