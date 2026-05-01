"""Common form utilities and base classes"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, DecimalField, BooleanField, PasswordField, FieldList, FormField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from wtforms.widgets import TextArea
from models.coi import COI


class SearchForm(FlaskForm):
    """Base search form"""
    q = StringField('Search', validators=[Optional(), Length(max=200)])


class BaseModelForm(FlaskForm):
    """Base form with common fields"""
    notes = TextAreaField('Notes', validators=[Optional()], widget=TextArea())


class UserForm(FlaskForm):
    """Form for creating/editing users"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[Optional(), Length(min=8)])
    is_active = BooleanField('Active', default=True)
    role_names = FieldList(StringField('Role'), min_entries=0)


class ServiceTicketForm(BaseModelForm):
    """Form for creating/editing service tickets"""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    client_type = SelectField('Client Type', choices=[('organization', 'Organization'), ('individual', 'Individual')], validators=[DataRequired()])
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')], default='normal')
    status = SelectField('Status', choices=[], validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[Optional()])
    assigned_to_user_id = SelectField('Assigned To', coerce=int, validators=[Optional()], default=0)


class ServiceNoteForm(FlaskForm):
    """Form for adding service notes"""
    body = TextAreaField('Note', validators=[DataRequired()], widget=TextArea())


class OrganizationForm(BaseModelForm):
    """Form for creating/editing organizations"""
    name = StringField('Organization Name', validators=[DataRequired(), Length(max=200)])
    fein = StringField('FEIN', validators=[Optional(), Length(max=20)])
    industry = StringField('Industry', validators=[Optional(), Length(max=100)])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    primary_contact_name = StringField('Primary Contact', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=50)])
    zip = StringField('ZIP Code', validators=[Optional(), Length(max=20)])


class IndividualForm(BaseModelForm):
    """Form for creating/editing individuals"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    dob = DateField('Date of Birth', validators=[Optional()])
    ssn_last4 = StringField('SSN (Last 4)', validators=[Optional(), Length(max=4)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=50)])
    zip = StringField('ZIP Code', validators=[Optional(), Length(max=20)])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')


class VendorForm(BaseModelForm):
    """Form for creating/editing vendors"""
    name = StringField('Vendor Name', validators=[DataRequired(), Length(max=200)])
    vendor_type = SelectField('Vendor Type', choices=[], validators=[DataRequired()])
    role_description = TextAreaField('Role/Services Description', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    website = StringField('Website', validators=[Optional(), Length(max=200)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=50)])
    zip = StringField('ZIP Code', validators=[Optional(), Length(max=20)])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')


class GroupPolicyForm(BaseModelForm):
    """Form for creating/editing group policies"""
    carrier_id = SelectField('Carrier', choices=[], validators=[DataRequired()], coerce=int)
    product_type = SelectField('Product Type', choices=[], validators=[DataRequired()])
    policy_number = StringField('Policy Number', validators=[Optional(), Length(max=100)])
    effective_date = DateField('Effective Date', validators=[DataRequired()])
    renewal_date = DateField('Renewal Date', validators=[Optional()])
    funding = SelectField('Funding', choices=[], validators=[DataRequired()])
    estimated_monthly_revenue = DecimalField('Estimated Revenue', validators=[Optional(), NumberRange(min=0)], render_kw={'step': '0.01'})
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive'), ('pending', 'Pending')], default='active')


class IndividualPolicyForm(BaseModelForm):
    """Form for creating/editing individual policies"""
    carrier_id = SelectField('Carrier', choices=[], validators=[DataRequired()], coerce=int)
    product_type = SelectField('Product Type', choices=[], validators=[DataRequired()])
    policy_number = StringField('Policy Number', validators=[Optional(), Length(max=100)])
    face_amount = DecimalField('Face Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    effective_date = DateField('Effective Date', validators=[DataRequired()])
    status = SelectField('Status', choices=[('active', 'Active'), ('lapsed', 'Lapsed'), ('terminated', 'Terminated'), ('pending', 'Pending')], default='active')
    corporate_related = BooleanField('Corporate Related', default=False)
    corporate_entity_id = SelectField('Corporate Entity ID', coerce=int, validators=[Optional()])
    corporate_explanation = StringField('Corporate Explanation', validators=[Optional(), Length(max=100)])


class ContactForm(BaseModelForm):
    """Form for creating/editing contacts"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    work_email = StringField('Work Email', validators=[Optional(), Email(), Length(max=120)])
    personal_email = StringField('Personal Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    mobile = StringField('Mobile', validators=[Optional(), Length(max=20)])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')


class ContactLinkForm(FlaskForm):
    """Form for linking contacts to entities"""
    contact_id = SelectField('Contact', coerce=int, validators=[DataRequired()])
    role_at_entity = StringField('Role at Organization', validators=[Optional(), Length(max=100)])
    is_primary = BooleanField('Primary Contact', default=False)

class COIForm(BaseModelForm):
    """Form for creating/editing COI records"""
    contact_id = SelectField('Contact', coerce=int, validators=[DataRequired()])
    user_id = SelectField('Salesperson', coerce=int, validators=[DataRequired()])
    category = SelectField('Category', choices=COI.get_category_choices(), validators=[DataRequired()])
    explanation = TextAreaField('Explanation', validators=[Optional()], render_kw={'rows': 3})
    notes = TextAreaField('Notes', validators=[Optional()], render_kw={'rows': 4})
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], validators=[DataRequired()])
    submit = SubmitField('Save COI Record')


class DealForm(FlaskForm):
    """Form for creating and editing deals"""
    name = StringField('Deal Name', validators=[DataRequired(), Length(min=1, max=200)])

    # Client selection - either organization or individual
    entity_id = SelectField('Organization', coerce=int, validators=[Optional()])
    contact_id = SelectField('Individual Client', choices=[], validators=[Optional()], coerce=int)

    stage = SelectField('Stage', choices=[
        (0, 'Lead'),
        (1, 'Qualified'),
        (2, 'Proposal'),
        (3, 'Negotiation'),
        (4, 'Verbal Agreement'),
        (5, 'Closed')
    ], coerce=int, validators=[DataRequired()])

    owner_user_id = SelectField('Deal Owner', coerce=int, validators=[DataRequired()])
    est_close_date = DateField('Estimated Close Date', validators=[Optional()])
    est_premium_value = DecimalField('Estimated Revenue', validators=[Optional(), NumberRange(min=0)], render_kw={'step': '0.01'})
    recurring = SelectField('Revenue Type', choices=[
        ('Recurring', 'Recurring'),
        ('Nonrecurring', 'Nonrecurring')
    ], validators=[DataRequired()])
    actual_close_date = DateField('Actual Close Date', validators=[Optional()])

    product_type = StringField('Product Type', validators=[Optional(), Length(max=100)])
    competition = StringField('Competition', validators=[Optional(), Length(max=200)])
    next_step = TextAreaField('Next Step', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])

    submit = SubmitField('Save Deal')

class DealNoteForm(BaseModelForm):
    """Form for adding deal notes"""
    deal_id = SelectField('Deal', coerce=int, validators=[DataRequired()])
    body = TextAreaField('Note', validators=[DataRequired()], widget=TextArea())
    submit = SubmitField('Add Note')