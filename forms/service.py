"""Service ticket forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from wtforms.widgets import Select
from models.user import User
from models.organization import Organization
from models.individual import Individual
from models.contact import Contact


class ServiceTicketForm(FlaskForm):
    """Form for creating and editing service tickets."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    client_type = SelectField('Client Type', choices=[('organization', 'Organization'), ('individual', 'Individual')], validators=[DataRequired()])
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='normal', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('not_started', 'Not Started'),
        ('started', 'Started'),
        ('started_waiting_on_someone_else', 'Started - Waiting on Someone Else'),
        ('complete_pending_confirmation', 'Complete - Pending Confirmation'),
        ('complete', 'Complete')
    ], default='not_started', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[Optional()])
    assigned_to_user_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    contacts = SelectMultipleField('Related Contacts', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Ticket')
    
    def __init__(self, *args, **kwargs):
        super(ServiceTicketForm, self).__init__(*args, **kwargs)
        
        # Populate user choices
        users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
        self.assigned_to_user_id.choices = [('', 'Unassigned')] + [(user.id, user.full_name) for user in users]
        
        # Populate client choices based on client_type
        self.client_id.choices = []
        if self.client_type.data == 'organization':
            orgs = Organization.query.filter_by(status='active').order_by(Organization.name).all()
            self.client_id.choices = [(org.id, org.name) for org in orgs]
        elif self.client_type.data == 'individual':
            individuals = Individual.query.filter_by(status='active').order_by(Individual.last_name, Individual.first_name).all()
            self.client_id.choices = [(ind.id, ind.full_name) for ind in individuals]
        
        # Populate contact choices
        contacts = Contact.query.filter_by(status='active').order_by(Contact.last_name, Contact.first_name).all()
        self.contacts.choices = [(contact.id, f'{contact.full_name} ({contact.email})') for contact in contacts]


class ServiceNoteForm(FlaskForm):
    """Form for adding notes to service tickets."""
    body = TextAreaField('Note', validators=[DataRequired()])
    submit = SubmitField('Add Note')


class ServiceReportForm(FlaskForm):
    """Form for service reporting filters."""
    date_start = DateField('Start Date', validators=[Optional()])
    date_end = DateField('End Date', validators=[Optional()])
    client_type = SelectField('Client Type', choices=[('', 'All'), ('organization', 'Organization'), ('individual', 'Individual')], validators=[Optional()])
    assigned_to = SelectField('Assigned To', coerce=int, validators=[Optional()])
    status = SelectMultipleField('Status', choices=[
        ('not_started', 'Not Started'),
        ('started', 'Started'),
        ('started_waiting_on_someone_else', 'Started - Waiting on Someone Else'),
        ('complete_pending_confirmation', 'Complete - Pending Confirmation'),
        ('complete', 'Complete')
    ], validators=[Optional()])
    submit = SubmitField('Generate Report')
    
    def __init__(self, *args, **kwargs):
        super(ServiceReportForm, self).__init__(*args, **kwargs)
        
        # Populate user choices
        users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
        self.assigned_to.choices = [('', 'All')] + [(user.id, user.full_name) for user in users]
