"""Account management forms for organizations and individuals."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, DecimalField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError, Email
from models.entity import Entity
from models.contact import Contact


class OrganizationForm(FlaskForm):
    """Form for creating and editing organizations."""
    name = StringField('Organization Name', validators=[DataRequired(), Length(max=200)])
    fein = StringField('FEIN', validators=[Optional(), Length(max=20)])
    sic_code = StringField('SIC Code', validators=[Optional(), Length(max=10)])
    industry = StringField('Industry', validators=[Optional(), Length(max=100)])
    is_applicable_large_employer = BooleanField('Applicable Large Employer (ALE)', default=False)
    primary_contact_id = SelectField('Primary Contact', coerce=lambda x: int(x) if x else None, validators=[Optional()])
    contact_role = StringField('Contact Role/Title', validators=[Optional(), Length(max=100)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=2)])
    zip = StringField('ZIP Code', validators=[Optional(), Length(max=10)])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Organization')

    def __init__(self, *args, **kwargs):
        super(OrganizationForm, self).__init__(*args, **kwargs)

        # Populate contact choices
        contacts = Contact.get_active().order_by(Contact.last_name, Contact.first_name).all()
        self.primary_contact_id.choices = [(None, 'Select Primary Contact (Optional)')] + [(c.id, c.full_name) for c in contacts]

    def validate_contact_role(self, field):
        """Validate that contact role is only provided when a contact is selected."""
        if field.data and not self.primary_contact_id.data:
            raise ValidationError('Please select a primary contact when providing a contact role.')


class IndividualForm(FlaskForm):
    """Form for creating and editing individuals."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    dob = DateField('Date of Birth', validators=[Optional()])
    ssn_last4 = StringField('SSN (Last 4)', validators=[Optional(), Length(max=4)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    mobile = StringField('Mobile', validators=[Optional(), Length(max=20)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=2)])
    zip = StringField('ZIP Code', validators=[Optional(), Length(max=10)])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Individual')


class GroupPolicyForm(FlaskForm):
    """Form for creating/editing group policies"""
    carrier_id = SelectField('Carrier', choices=[], validators=[Optional()])
    product_type = SelectField('Product Type', choices=[
        ('medical', 'Medical'),
        ('dental', 'Dental'),
        ('vision', 'Vision'),
        ('life', 'Life'),
        ('std', 'Short Term Disability'),
        ('ltd', 'Long Term Disability'),
        ('aso', 'ASO'),
        ('stop_loss', 'Stop Loss'),
        ('consulting_fee', 'Consulting Fee'),
        ('executive_benefits', 'Executive Benefits Consulting'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    policy_number = StringField('Policy Number', validators=[Optional(), Length(max=100)])
    effective_date = DateField('Effective Date', validators=[DataRequired()])
    renewal_date = DateField('Renewal Date', validators=[Optional()])
    funding = SelectField('Funding', choices=[
        ('fully_insured', 'Fully Insured'),
        ('self_funded', 'Self Funded'),
        ('level_funded', 'Level Funded'),
        ('not_applicable', 'Not Applicable')
    ], validators=[Optional()])
    estimated_monthly_revenue = DecimalField('Estimated Monthly Revenue',
                                           validators=[Optional(), NumberRange(min=0)], places=2)
    notes = TextAreaField('Notes')
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
        ('terminated', 'Terminated')
    ], default='active')

    def __init__(self, *args, **kwargs):
        self.policy_id = kwargs.pop('policy_id', None)  # For editing existing policies
        super(GroupPolicyForm, self).__init__(*args, **kwargs)
        # Populate carrier choices from active insurance vendors only
        from models.entity import VendorDetail
        carriers = Entity.query.join(VendorDetail).filter(
            VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
            Entity.status == 'active'
        ).order_by(Entity.name).all()
        self.carrier_id.choices = [('', 'Select Carrier'), ('not_applicable', 'Not Applicable')] + [(str(c.id), c.name) for c in carriers]


class IndividualPolicyForm(FlaskForm):
    """Form for creating/editing individual policies"""
    client_id = SelectField('Individual', choices=[], validators=[DataRequired()])
    carrier_id = SelectField('Carrier', choices=[], validators=[DataRequired()])
    product_type = SelectField('Product Type', choices=[
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('di', 'Disability Insurance'),
        ('ltc', 'Long-term Care'),
        ('annuity', 'Annuity'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    policy_number = StringField('Policy Number', validators=[Optional(), Length(max=100)])
    face_amount = DecimalField('Face Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    premium_amount = DecimalField('Premium Amount', validators=[Optional(), NumberRange(min=0)], places=2)
    premium_frequency = SelectField('Premium Frequency', choices=[
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual')
    ], validators=[Optional()])
    effective_date = DateField('Effective Date', validators=[DataRequired()])
    maturity_date = DateField('Maturity Date', validators=[Optional()])
    is_corporate_related = BooleanField('Corporate Related', default=False)
    corporate_entity_id = SelectField('Corporate Entity', choices=[], validators=[Optional()])
    corporate_explanation = StringField('Corporate Explanation', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('Notes')
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('lapsed', 'Lapsed'),
        ('terminated', 'Terminated'),
        ('pending', 'Pending')
    ], default='active')

    def __init__(self, *args, **kwargs):
        super(IndividualPolicyForm, self).__init__(*args, **kwargs)
        # Populate individual client choices  
        individuals = Contact.get_active().order_by(Contact.last_name, Contact.first_name).all()
        self.client_id.choices = [('', 'Select Individual')] + [(str(c.id), c.full_name) for c in individuals]
        # Populate carrier choices from Entity table (insurance vendors only)
        from models.entity import VendorDetail
        carriers = Entity.query.join(VendorDetail).filter(
            VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
            Entity.status == 'active'
        ).order_by(Entity.name).all()
        self.carrier_id.choices = [('', 'Select Carrier')] + [(str(c.id), c.name) for c in carriers]
        # Populate corporate entity choices - filter out vendors to only show actual organizations
        from models.entity import VendorDetail
        orgs = Entity.query.outerjoin(VendorDetail).filter(
            VendorDetail.id.is_(None),  # Only entities that are NOT vendors
            Entity.status == 'active'
        ).order_by(Entity.name).all()
        self.corporate_entity_id.choices = [('', 'Select Corporate Entity (Optional)')] + [(str(org.id), org.name) for org in orgs]


class OrgAffiliationForm(FlaskForm):
    """Form for creating organization affiliations."""
    organization_id = SelectField('Organization', choices=[(None, 'Select Organization')], coerce=lambda x: int(x) if x else None, validators=[DataRequired()])
    relationship = SelectField('Relationship', choices=[
        ('employee', 'Employee'),
        ('owner', 'Owner'),
        ('executive', 'Executive'),
        ('insured', 'Insured'),
        ('beneficiary', 'Beneficiary'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Create Affiliation')

    def __init__(self, *args, **kwargs):
        super(OrgAffiliationForm, self).__init__(*args, **kwargs)

        # Populate organization choices
        orgs = Entity.query.filter_by(status='active').order_by(Entity.name).all()
        self.organization_id.choices = [(None, 'Select Organization')] + [(org.id, org.name) for org in orgs]