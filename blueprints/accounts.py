"""Accounts blueprint for organization and individual client management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy import or_
import json

from extensions.db import db
from models.entity import Entity, VendorDetail
from models.contact import Contact, Client, ContactLink
from models.policy import GroupPolicy, IndividualPolicy
from models.wizard import WizardState
from utils.decorators import account_mgmt_or_admin_required
from forms.accounts import OrganizationForm, IndividualForm, GroupPolicyForm, IndividualPolicyForm
from utils.forms import SearchForm
from forms.accounts import GroupPolicyForm as AccountsGroupPolicyForm # Import the correct form class

accounts_bp = Blueprint('accounts', __name__)


# Organization routes
@accounts_bp.route('/organizations')
@account_mgmt_or_admin_required
def organizations():
    """List ALL organizations (entities) with search and pagination"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = Entity.query

    # Apply search filter
    if request.args.get('q'):
        search_term = f"%{request.args.get('q')}%"
        query = query.filter(Entity.name.ilike(search_term))

    # Apply status filter
    status_filter = request.args.get('status', 'active')
    if status_filter != 'all':
        query = query.filter(Entity.status == status_filter)

    # Apply industry filter
    industry_filter = request.args.get('industry')
    if industry_filter:
        query = query.filter(Entity.industry.ilike(f'%{industry_filter}%'))

    organizations = query.order_by(Entity.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('accounts/organizations.html',
                         organizations=organizations,
                         search_form=search_form,
                         view_type='all')


@accounts_bp.route('/orgs')
@account_mgmt_or_admin_required
def corporate_clients():
    """List corporate clients only (organizations with at least one group policy)"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    # Query only entities that are NOT vendors AND have at least one group policy (any status)
    query = Entity.query.outerjoin(VendorDetail).filter(VendorDetail.id.is_(None))

    # Join with GroupPolicy to filter for entities with ANY policies (not just active)
    query = query.join(GroupPolicy, Entity.id == GroupPolicy.entity_id).distinct()

    # Apply search filter
    if request.args.get('q'):
        search_term = f"%{request.args.get('q')}%"
        query = query.filter(Entity.name.ilike(search_term))

    # Apply status filter to the ENTITY status (not policy status)
    status_filter = request.args.get('status', 'active')
    if status_filter != 'all':
        query = query.filter(Entity.status == status_filter)

    # Apply industry filter
    industry_filter = request.args.get('industry')
    if industry_filter:
        query = query.filter(Entity.industry.ilike(f'%{industry_filter}%'))

    organizations = query.order_by(Entity.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('accounts/organizations.html',
                         organizations=organizations,
                         search_form=search_form,
                         view_type='clients')


@accounts_bp.route('/orgs/new', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def create_organization():
    """Create new organization"""
    form = OrganizationForm()

    if form.validate_on_submit():
        organization = Entity(
            name=form.name.data,
            fein=form.fein.data,
            sic_code=form.sic_code.data,
            industry=form.industry.data,
            is_applicable_large_employer=form.is_applicable_large_employer.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            state=form.state.data,
            zip=form.zip.data,
            notes=form.notes.data,
            status=request.form.get('status', 'active')
        )

        db.session.add(organization)
        db.session.commit()

        # Create contact link if primary contact is specified
        primary_contact_id = form.primary_contact_id.data
        if primary_contact_id:
            contact_link = ContactLink(
                contact_id=primary_contact_id,
                entity_id=organization.id,
                role_at_entity=form.contact_role.data,
                is_primary=True
            )
            db.session.add(contact_link)
            db.session.commit()

        flash(f'Organization "{organization.name}" created successfully.', 'success')
        return redirect(url_for('accounts.organization_detail', org_id=organization.id))

    return render_template('accounts/organization_form.html', form=form, organization=None)


@accounts_bp.route('/orgs/<int:org_id>')
@account_mgmt_or_admin_required
def organization_detail(org_id):
    """View organization details"""
    organization = Entity.query.get_or_404(org_id) # Updated to use Entity

    # Get linked contacts
    contact_links = ContactLink.query.filter_by(
        entity_id=org_id
    ).join(Contact).order_by(ContactLink.is_primary.desc(), Contact.last_name, Contact.first_name).all()

    # Get recent service tickets involving these contacts
    recent_tickets = []
    if contact_links:
        contact_ids = [cl.contact_id for cl in contact_links]
        from models.service import ServiceTicket
        from models.contact import service_ticket_contact
        # Get recent tickets through the association table
        recent_tickets = db.session.query(ServiceTicket).join(
            service_ticket_contact
        ).filter(
            service_ticket_contact.c.contact_id.in_(contact_ids)
        ).order_by(ServiceTicket.updated_at.desc()).limit(10).all()

    return render_template('accounts/organization_detail.html',
                         organization=organization,
                         contact_links=contact_links,
                         recent_tickets=recent_tickets)


@accounts_bp.route('/orgs/<int:org_id>/edit', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def edit_organization(org_id):
    """Edit organization"""
    organization = Entity.query.get_or_404(org_id) # Updated to use Entity
    form = OrganizationForm()

    # Pre-populate form data on GET request
    if request.method == 'GET':
        form.name.data = organization.name
        form.fein.data = organization.fein
        form.sic_code.data = organization.sic_code
        form.industry.data = organization.industry
        form.is_applicable_large_employer.data = organization.is_applicable_large_employer
        form.address_line1.data = organization.address_line1
        form.address_line2.data = organization.address_line2
        form.city.data = organization.city
        form.state.data = organization.state
        form.zip.data = organization.zip
        form.notes.data = organization.notes

        # Pre-populate form with existing contact link
        current_primary = next((link for link in organization.contact_links if link.is_primary), None)
        if current_primary:
            form.primary_contact_id.data = current_primary.contact_id
            form.contact_role.data = current_primary.role_at_entity

    if form.validate_on_submit():
        organization.name = form.name.data
        organization.fein = form.fein.data
        organization.sic_code = form.sic_code.data
        organization.industry = form.industry.data
        organization.is_applicable_large_employer = form.is_applicable_large_employer.data
        organization.address_line1 = form.address_line1.data
        organization.address_line2 = form.address_line2.data
        organization.city = form.city.data
        organization.state = form.state.data
        organization.zip = form.zip.data
        organization.notes = form.notes.data
        organization.status = request.form.get('status', 'active')

        # Update primary contact link
        primary_contact_id = form.primary_contact_id.data

        # Remove existing primary contact link
        existing_primary = ContactLink.query.filter_by(
            entity_id=organization.id,
            is_primary=True
        ).first()
        if existing_primary:
            db.session.delete(existing_primary)

        # Create new primary contact link if specified
        if primary_contact_id:
            contact_link = ContactLink(
                contact_id=primary_contact_id,
                entity_id=organization.id,
                role_at_entity=form.contact_role.data,
                is_primary=True
            )
            db.session.add(contact_link)

        db.session.commit()

        flash(f'Organization "{organization.name}" updated successfully.', 'success')
        return redirect(url_for('accounts.organization_detail', org_id=organization.id))

    return render_template('accounts/organization_form.html', form=form, organization=organization)


@accounts_bp.route('/orgs/<int:org_id>/inactivate', methods=['POST'])
@account_mgmt_or_admin_required
def inactivate_organization(org_id):
    """Inactivate organization"""
    organization = Entity.query.get_or_404(org_id) # Updated to use Entity

    # Check for active policies
    active_policies = [p for p in organization.group_policies if p.status == 'active']
    if active_policies:
        flash(f'Cannot inactivate organization with {len(active_policies)} active policies. Inactivate policies first.', 'warning')
        return redirect(url_for('accounts.organization_detail', org_id=org_id))

    organization.status = 'inactive'
    db.session.commit()

    flash(f'Organization "{organization.name}" inactivated successfully.', 'success')
    return redirect(url_for('accounts.organizations'))


@accounts_bp.route('/orgs/<int:org_id>/delete', methods=['POST'])
@login_required
def delete_organization(org_id):
    """Delete organization (admin only)"""
    from flask_login import current_user

    # Check if user is admin
    if not current_user.has_role('admin'):
        flash('Only administrators can delete organizations.', 'danger')
        return redirect(url_for('accounts.organization_detail', org_id=org_id))

    organization = Entity.query.get_or_404(org_id)

    # Check for any policies
    if organization.group_policies:
        flash(f'Cannot delete organization with {len(organization.group_policies)} policies. Remove policies first.', 'warning')
        return redirect(url_for('accounts.organization_detail', org_id=org_id))

    # Check for contact links
    if organization.contact_links:
        flash(f'Cannot delete organization with {len(organization.contact_links)} contact links. Remove links first.', 'warning')
        return redirect(url_for('accounts.organization_detail', org_id=org_id))

    org_name = organization.name
    db.session.delete(organization)
    db.session.commit()

    flash(f'Organization "{org_name}" deleted successfully.', 'success')
    return redirect(url_for('accounts.organizations'))


@accounts_bp.route('/orgs/<int:org_id>/policies')
@account_mgmt_or_admin_required
def organization_policies(org_id):
    """List organization policies"""
    organization = Entity.query.get_or_404(org_id) # Updated to use Entity
    policies = GroupPolicy.query.filter_by(organization_id=org_id).order_by(GroupPolicy.effective_date.desc()).all()

    return render_template('accounts/organization_detail.html',
                         organization=organization,
                         policies=policies,
                         tab='policies')


@accounts_bp.route('/orgs/<int:org_id>/policies/new', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def create_group_policy(org_id):
    """Create new group policy"""
    organization = Entity.query.get_or_404(org_id)
    form = AccountsGroupPolicyForm() # Use the correct form class

    # Populate form choices
    form.product_type.choices = [
        ('medical', 'Medical'),
        ('dental', 'Dental'),
        ('vision', 'Vision'),
        ('life', 'Life'),
        ('std', 'Short Term Disability'),
        ('ltd', 'Long Term Disability'),
        ('consulting_fee', 'Consulting Fee'),
        ('executive_benefits', 'Executive Benefits Consulting'),
        ('other', 'Other')
    ]
    form.funding.choices = [
        ('fully_insured', 'Fully Insured'),
        ('self_funded', 'Self Funded'),
        ('level_funded', 'Level Funded'),
        ('not_applicable', 'Not Applicable')
    ]

    # Get insurance vendors for carrier choices
    from models.entity import VendorDetail
    insurers = Entity.query.join(VendorDetail).filter(
        VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
        Entity.status == 'active'
    ).order_by(Entity.name).all()
    form.carrier_id.choices = [('', 'Select Carrier'), ('not_applicable', 'Not Applicable')] + [(str(i.id), i.name) for i in insurers]

    if form.validate_on_submit():
        # Handle carrier_id - convert string to int or None
        carrier_id = None
        if form.carrier_id.data and form.carrier_id.data != '' and form.carrier_id.data != 'not_applicable':
            try:
                carrier_id = int(form.carrier_id.data)
            except (ValueError, TypeError):
                carrier_id = None

        policy = GroupPolicy(
            entity_id=org_id,
            carrier_id=carrier_id,
            product_type=form.product_type.data,
            policy_number=form.policy_number.data,
            effective_date=form.effective_date.data,
            renewal_date=form.renewal_date.data,
            funding=form.funding.data,
            estimated_monthly_revenue=form.estimated_monthly_revenue.data,
            status=form.status.data,
            notes=form.notes.data
        )

        db.session.add(policy)
        db.session.commit()

        carrier_name = policy.carrier.name if policy.carrier else "N/A"
        flash(f'Group policy for {carrier_name} created successfully.', 'success')
        return redirect(url_for('accounts.organization_detail', org_id=org_id))

    return render_template('accounts/policy_form.html',
                         form=form,
                         policy=None,
                         entity=organization,
                         policy_type='group')


# Individual routes
@accounts_bp.route('/individuals')
@account_mgmt_or_admin_required
def individuals():
    """List individual clients only (contacts with at least one individual policy)"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    # Query only contacts that have at least one individual policy (any status)
    from models.contact import Client
    query = Contact.query.join(Client, Contact.id == Client.contact_id).join(IndividualPolicy, Client.id == IndividualPolicy.client_id).distinct()

    # Apply search filter
    if request.args.get('q'):
        search_term = f"%{request.args.get('q')}%"
        query = query.filter(
            or_(
                Contact.first_name.ilike(search_term),
                Contact.last_name.ilike(search_term),
                Contact.work_email.ilike(search_term),
                Contact.personal_email.ilike(search_term)
            )
        )

    # Apply status filter to the CONTACT status (not policy status)
    status_filter = request.args.get('status', 'active')
    if status_filter != 'all':
        query = query.filter(Contact.status == status_filter)

    individuals = query.order_by(Contact.last_name, Contact.first_name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('accounts/individuals.html',
                         individuals=individuals,
                         search_form=search_form)


@accounts_bp.route('/individuals/new', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def create_individual():
    """Create new individual"""
    form = IndividualForm()

    if form.validate_on_submit():
        # Create Contact record first
        contact = Contact(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            dob=form.dob.data,
            work_email=form.email.data,
            phone=form.phone.data,
            mobile=form.mobile.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            state=form.state.data,
            zip=form.zip.data,
            status=form.status.data,
            notes=form.notes.data
        )

        db.session.add(contact)
        db.session.flush()  # Get the contact ID

        # Create Client record
        client = Client(
            contact_id=contact.id,
            ssn_last4=form.ssn_last4.data
        )

        db.session.add(client)
        db.session.commit()

        flash(f'Individual "{contact.full_name}" created successfully.', 'success')
        return redirect(url_for('accounts.individual_detail', individual_id=contact.id))

    return render_template('accounts/individual_form.html', form=form, individual=None)


@accounts_bp.route('/individuals/<int:individual_id>')
@account_mgmt_or_admin_required
def individual_detail(individual_id):
    """View individual details"""
    individual = Contact.query.get_or_404(individual_id) # Assuming 'Individual' is now a type of 'Contact'

    # Get linked contacts
    contact_links = ContactLink.query.filter_by(
        entity_type='individual',
        entity_id=individual_id
    ).join(Contact).order_by(ContactLink.is_primary.desc(), Contact.last_name, Contact.first_name).all()

    # Get organization affiliations through contact links
    affiliations = ContactLink.query.filter_by(contact_id=individual_id).join(Entity).all()

    return render_template('accounts/individual_detail.html',
                         individual=individual,
                         contact_links=contact_links,
                         affiliations=affiliations)


@accounts_bp.route('/individuals/<int:individual_id>/edit', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def edit_individual(individual_id):
    """Edit individual"""
    individual = Contact.query.get_or_404(individual_id) # Assuming 'Individual' is now a type of 'Contact'
    form = IndividualForm()

    # Pre-populate form data on GET request
    if request.method == 'GET':
        form.first_name.data = individual.first_name
        form.last_name.data = individual.last_name
        form.dob.data = individual.dob if hasattr(individual, 'dob') else None
        form.email.data = individual.work_email
        form.phone.data = individual.phone
        form.mobile.data = individual.mobile
        form.address_line1.data = individual.address_line1 if hasattr(individual, 'address_line1') else None
        form.address_line2.data = individual.address_line2 if hasattr(individual, 'address_line2') else None
        form.city.data = individual.city if hasattr(individual, 'city') else None
        form.state.data = individual.state if hasattr(individual, 'state') else None
        form.zip.data = individual.zip if hasattr(individual, 'zip') else None
        form.notes.data = individual.notes

    if form.validate_on_submit():
        individual.first_name = form.first_name.data
        individual.last_name = form.last_name.data
        individual.dob = form.dob.data
        individual.ssn_last4 = form.ssn_last4.data
        individual.email = form.email.data
        individual.phone = form.phone.data
        individual.address_line1 = form.address_line1.data
        individual.address_line2 = form.address_line2.data
        individual.city = form.city.data
        individual.state = form.state.data
        individual.zip = form.zip.data
        individual.status = form.status.data
        individual.notes = form.notes.data

        db.session.commit()

        flash(f'Individual "{individual.full_name}" updated successfully.', 'success')
        return redirect(url_for('accounts.individual_detail', individual_id=individual.id))

    return render_template('accounts/individual_form.html', form=form, individual=individual)


@accounts_bp.route('/individuals/<int:individual_id>/inactivate', methods=['POST'])
@account_mgmt_or_admin_required
def inactivate_individual(individual_id):
    """Inactivate individual"""
    individual = Contact.query.get_or_404(individual_id) # Assuming 'Individual' is now a type of 'Contact'

    # Check for active policies
    active_policies = [p for p in individual.individual_policies if p.status == 'active']
    if active_policies:
        flash(f'Cannot inactivate individual with {len(active_policies)} active policies. Inactivate policies first.', 'warning')
        return redirect(url_for('accounts.individual_detail', individual_id=individual_id))

    individual.status = 'inactive'
    db.session.commit()

    flash(f'Individual "{individual.full_name}" inactivated successfully.', 'success')
    return redirect(url_for('accounts.individuals'))


@accounts_bp.route('/individuals/<int:individual_id>/policies/new', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def create_individual_policy(individual_id):
    """Create new individual policy"""
    individual = Contact.query.get_or_404(individual_id)
    form = IndividualPolicyForm()

    # Populate form choices with insurance vendors only
    from models.entity import VendorDetail
    vendors = Entity.query.join(VendorDetail).filter(
        VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
        Entity.status == 'active'
    ).order_by(Entity.name).all()
    form.carrier_id.choices = [('', 'Select Carrier')] + [(str(v.id), v.name) for v in vendors]

    # Get corporate entities for corporate relationship
    organizations = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.corporate_entity_id.choices = [('', 'Select Organization...')] + [(str(org.id), org.name) for org in organizations]

    # Set product type choices (ensure this is set before form validation)
    form.product_type.choices = [
        ('', 'Select Product Type'),
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('di', 'Disability Insurance'),
        ('ltc', 'Long-term Care'),
        ('annuity', 'Annuity'),
        ('other', 'Other')
    ]

    if form.validate_on_submit():
        # Get the client record for this individual
        client = Client.query.filter_by(contact_id=individual_id).first()
        if not client:
            # Create client record if it doesn't exist
            client = Client(contact_id=individual_id)
            db.session.add(client)
            db.session.flush()

        # Convert string IDs to integers, handle 'not_applicable' case
        carrier_id = None
        if form.carrier_id.data and form.carrier_id.data != 'not_applicable':
            carrier_id = int(form.carrier_id.data)

        corporate_entity_id = None
        if form.corporate_entity_id.data and form.corporate_entity_id.data != '':
            try:
                corporate_entity_id = int(form.corporate_entity_id.data)
            except (ValueError, TypeError):
                corporate_entity_id = None

        policy = IndividualPolicy(
            client_id=client.id,
            carrier_id=carrier_id,
            product_type=form.product_type.data,
            policy_number=form.policy_number.data,
            face_amount=form.face_amount.data,
            effective_date=form.effective_date.data,
            is_corporate_related=form.is_corporate_related.data,
            corporate_entity_id=corporate_entity_id,
            corporate_explanation=form.corporate_explanation.data,
            status=form.status.data,
            notes=form.notes.data
        )

        db.session.add(policy)
        db.session.commit()

        flash(f'Individual policy created successfully.', 'success')
        return redirect(url_for('policies.individual_policy_detail', policy_id=policy.id))

    return render_template('accounts/policy_form.html',
                         form=form,
                         policy=None,
                         entity=individual,
                         policy_type='individual')


@accounts_bp.route('/individuals/<int:individual_id>/affiliations/new', methods=['POST'])
@account_mgmt_or_admin_required
def create_affiliation(individual_id):
    """Create organization affiliation for individual"""
    individual = Contact.query.get_or_404(individual_id)

    entity_id = request.form.get('organization_id', type=int)
    role_at_entity = request.form.get('relationship')
    notes = request.form.get('notes')

    if entity_id and role_at_entity:
        entity = Entity.query.get(entity_id)
        if entity:
            # Check if link already exists
            existing_link = ContactLink.query.filter_by(
                contact_id=individual_id,
                entity_id=entity_id
            ).first()

            if existing_link:
                flash(f'Contact is already linked to {entity.name}.', 'warning')
            else:
                contact_link = ContactLink(
                    contact_id=individual_id,
                    entity_id=entity_id,
                    role_at_entity=role_at_entity
                )

                db.session.add(contact_link)
                db.session.commit()

                flash(f'Contact linked to {entity.name} successfully.', 'success')
        else:
            flash('Invalid organization selected.', 'danger')
    else:
        flash('Organization and relationship are required.', 'danger')

    return redirect(url_for('accounts.individual_detail', individual_id=individual_id))


# Wizard routes for streamlined individual client + policy creation
@accounts_bp.route('/wizard/individual-policy/start', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def wizard_individual_policy_start():
    """Step 1: Create individual client"""
    form = IndividualForm()

    if form.validate_on_submit():
        # Create wizard state in database (secure server-side storage)
        wizard = WizardState.create_wizard('individual_policy', current_user.id)

        # Store form data securely on server
        wizard.step_data = json.dumps({
            'individual': {
                'first_name': form.first_name.data,
                'last_name': form.last_name.data,
                'dob': form.dob.data.isoformat() if form.dob.data else None,
                'ssn_last4': form.ssn_last4.data,
                'email': form.email.data,
                'phone': form.phone.data,
                'mobile': form.mobile.data,
                'address_line1': form.address_line1.data,
                'address_line2': form.address_line2.data,
                'city': form.city.data,
                'state': form.state.data,
                'zip': form.zip.data,
                'status': form.status.data,
                'notes': form.notes.data
            }
        })
        db.session.commit()

        # Store only the secure token in client session
        session['wizard_token'] = wizard.token
        return redirect(url_for('accounts.wizard_individual_policy_entity'))

    return render_template('accounts/wizard_individual_step1.html', form=form, step=1)


@accounts_bp.route('/wizard/individual-policy/entity', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def wizard_individual_policy_entity():
    """Step 2: Select or create corporate entity"""
    # Get wizard state from server
    wizard_token = session.get('wizard_token')
    if not wizard_token:
        flash('Please start from the beginning.', 'warning')
        return redirect(url_for('accounts.wizard_individual_policy_start'))

    wizard = WizardState.get_by_token(wizard_token)
    if not wizard or wizard.user_id != current_user.id:
        flash('Wizard session expired. Please start again.', 'warning')
        return redirect(url_for('accounts.wizard_individual_policy_start'))

    if request.method == 'POST':
        entity_id = request.form.get('entity_id')
        is_corporate_related = request.form.get('is_corporate_related') == 'yes'
        corporate_explanation = request.form.get('corporate_explanation', '')

        # Update wizard state
        wizard_data = json.loads(wizard.step_data)
        wizard_data['entity'] = {
            'entity_id': int(entity_id) if entity_id and entity_id != 'none' else None,
            'is_corporate_related': is_corporate_related,
            'corporate_explanation': corporate_explanation
        }
        wizard.step_data = json.dumps(wizard_data)
        db.session.commit()

        return redirect(url_for('accounts.wizard_individual_policy_details'))

    # Get active entities for dropdown (limited to first 100)
    entities = Entity.query.outerjoin(VendorDetail).filter(
        VendorDetail.id.is_(None),
        Entity.status == 'active'
    ).order_by(Entity.name).limit(100).all()

    wizard_data = json.loads(wizard.step_data)
    return render_template('accounts/wizard_individual_step2.html',
                         entities=entities,
                         step=2,
                         wizard_data=wizard_data.get('individual', {}))


@accounts_bp.route('/wizard/individual-policy/policy', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def wizard_individual_policy_details():
    """Step 3: Add policy details"""
    # Get wizard state from server
    wizard_token = session.get('wizard_token')
    if not wizard_token:
        flash('Please start from the beginning.', 'warning')
        return redirect(url_for('accounts.wizard_individual_policy_start'))

    wizard = WizardState.get_by_token(wizard_token)
    if not wizard or wizard.user_id != current_user.id:
        flash('Wizard session expired. Please start again.', 'warning')
        return redirect(url_for('accounts.wizard_individual_policy_start'))

    wizard_data = json.loads(wizard.step_data)
    if 'individual' not in wizard_data or 'entity' not in wizard_data:
        flash('Please complete previous steps.', 'warning')
        return redirect(url_for('accounts.wizard_individual_policy_start'))

    form = IndividualPolicyForm()

    # Populate form choices
    form.product_type.choices = [
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('di', 'Disability Insurance'),
        ('ltc', 'Long-term Care'),
        ('annuity', 'Annuity'),
        ('other', 'Other')
    ]

    form.premium_frequency.choices = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual')
    ]

    # Get insurance vendors for carrier choices
    insurers = Entity.query.join(VendorDetail).filter(
        VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
        Entity.status == 'active'
    ).all()
    form.carrier_id.choices = [(i.id, i.name) for i in insurers]

    if form.validate_on_submit():
        # Create all records in a transaction
        try:
            from datetime import datetime
            individual_data = wizard_data['individual']
            entity_data = wizard_data['entity']

            # Create Contact
            contact = Contact(
                first_name=individual_data['first_name'],
                last_name=individual_data['last_name'],
                dob=datetime.fromisoformat(individual_data['dob']) if individual_data.get('dob') else None,
                work_email=individual_data.get('email'),
                phone=individual_data.get('phone'),
                mobile=individual_data.get('mobile'),
                address_line1=individual_data.get('address_line1'),
                address_line2=individual_data.get('address_line2'),
                city=individual_data.get('city'),
                state=individual_data.get('state'),
                zip=individual_data.get('zip'),
                status=individual_data.get('status', 'active'),
                notes=individual_data.get('notes')
            )
            db.session.add(contact)
            db.session.flush()

            # Create Client
            client = Client(
                contact_id=contact.id,
                ssn_last4=individual_data.get('ssn_last4')
            )
            db.session.add(client)
            db.session.flush()

            # Create Policy
            policy = IndividualPolicy(
                client_id=client.id,
                carrier_id=form.carrier_id.data,
                product_type=form.product_type.data,
                policy_number=form.policy_number.data,
                face_amount=form.face_amount.data,
                premium_amount=form.premium_amount.data,
                premium_frequency=form.premium_frequency.data,
                effective_date=form.effective_date.data,
                maturity_date=form.maturity_date.data,
                status=form.status.data,
                is_corporate_related=entity_data.get('is_corporate_related', False),
                corporate_entity_id=entity_data.get('entity_id'),
                corporate_explanation=entity_data.get('corporate_explanation'),
                notes=form.notes.data
            )
            db.session.add(policy)

            db.session.commit()

            # Delete wizard state (cleanup)
            db.session.delete(wizard)
            db.session.commit()

            # Clear session token
            session.pop('wizard_token', None)

            flash(f'Individual client "{contact.full_name}" and policy created successfully!', 'success')
            return redirect(url_for('accounts.wizard_individual_policy_success',
                                  individual_id=contact.id,
                                  policy_id=policy.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating records: {str(e)}', 'danger')
            return redirect(url_for('accounts.wizard_individual_policy_start'))

    return render_template('accounts/wizard_individual_step3.html',
                         form=form,
                         step=3,
                         wizard_data=wizard_data)


@accounts_bp.route('/wizard/individual-policy/success/<int:individual_id>/<int:policy_id>')
@account_mgmt_or_admin_required
def wizard_individual_policy_success(individual_id, policy_id):
    """Success page with next action options"""
    contact = Contact.query.get_or_404(individual_id)
    policy = IndividualPolicy.query.get_or_404(policy_id)

    return render_template('accounts/wizard_individual_success.html',
                         contact=contact,
                         policy=policy)


# Wizard routes for streamlined corporate client + group policy creation
@accounts_bp.route('/wizard/group-policy/start', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def wizard_group_policy_start():
    """Step 1: Create corporate client"""
    form = OrganizationForm()

    # Remove primary_contact_id validation for wizard flow
    form.primary_contact_id.validators = []

    if form.validate_on_submit():
        # Create wizard state in database (secure server-side storage)
        wizard = WizardState.create_wizard('group_policy', current_user.id)

        # Store form data securely on server
        wizard.step_data = json.dumps({
            'organization': {
                'name': form.name.data,
                'fein': form.fein.data,
                'sic_code': form.sic_code.data,
                'industry': form.industry.data,
                'is_applicable_large_employer': form.is_applicable_large_employer.data,
                'address_line1': form.address_line1.data,
                'address_line2': form.address_line2.data,
                'city': form.city.data,
                'state': form.state.data,
                'zip': form.zip.data,
                'notes': form.notes.data
            }
        })
        db.session.commit()

        # Store only the secure token in client session
        session['wizard_token_group'] = wizard.token
        return redirect(url_for('accounts.wizard_group_policy_details'))

    return render_template('accounts/wizard_group_step1.html', form=form, step=1)


@accounts_bp.route('/wizard/group-policy/policy', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def wizard_group_policy_details():
    """Step 2: Add group policy details"""
    # Get wizard state from server
    wizard_token = session.get('wizard_token_group')
    if not wizard_token:
        flash('Please start from the beginning.', 'warning')
        return redirect(url_for('accounts.wizard_group_policy_start'))

    wizard = WizardState.get_by_token(wizard_token)
    if not wizard or wizard.user_id != current_user.id:
        flash('Wizard session expired. Please start again.', 'warning')
        return redirect(url_for('accounts.wizard_group_policy_start'))

    wizard_data = json.loads(wizard.step_data)
    if 'organization' not in wizard_data:
        flash('Please complete previous steps.', 'warning')
        return redirect(url_for('accounts.wizard_group_policy_start'))

    form = GroupPolicyForm()

    # Remove entity_id requirement since we're creating the entity
    form.entity_id.validators = []

    # Get insurance vendors for carrier choices
    from models.entity import VendorDetail
    insurers = Entity.query.join(VendorDetail).filter(
        VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
        Entity.status == 'active'
    ).all()
    form.carrier_id.choices = [('', 'Select Carrier')] + [(i.id, i.name) for i in insurers]

    if form.validate_on_submit():
        # Create all records in a transaction
        try:
            org_data = wizard_data['organization']

            # Create Entity
            entity = Entity(
                name=org_data['name'],
                fein=org_data.get('fein'),
                sic_code=org_data.get('sic_code'),
                industry=org_data.get('industry'),
                is_applicable_large_employer=org_data.get('is_applicable_large_employer', False),
                address_line1=org_data.get('address_line1'),
                address_line2=org_data.get('address_line2'),
                city=org_data.get('city'),
                state=org_data.get('state'),
                zip=org_data.get('zip'),
                status='active',
                notes=org_data.get('notes')
            )
            db.session.add(entity)
            db.session.flush()

            # Create Group Policy
            policy = GroupPolicy(
                entity_id=entity.id,
                carrier_id=form.carrier_id.data,
                product_type=form.product_type.data,
                policy_number=form.policy_number.data,
                effective_date=form.effective_date.data,
                renewal_date=form.renewal_date.data,
                funding=form.funding.data,
                estimated_monthly_revenue=form.estimated_monthly_revenue.data,
                status=form.status.data,
                notes=form.notes.data
            )
            db.session.add(policy)

            db.session.commit()

            # Delete wizard state (cleanup)
            db.session.delete(wizard)
            db.session.commit()

            # Clear session token
            session.pop('wizard_token_group', None)

            flash(f'Corporate client "{entity.name}" and group policy created successfully!', 'success')
            return redirect(url_for('accounts.wizard_group_policy_success',
                                  entity_id=entity.id,
                                  policy_id=policy.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating records: {str(e)}', 'danger')
            return redirect(url_for('accounts.wizard_group_policy_start'))

    return render_template('accounts/wizard_group_step2.html',
                         form=form,
                         step=2,
                         wizard_data=wizard_data)


@accounts_bp.route('/wizard/group-policy/success/<int:entity_id>/<int:policy_id>')
@account_mgmt_or_admin_required
def wizard_group_policy_success(entity_id, policy_id):
    """Success page with next action options"""
    entity = Entity.query.get_or_404(entity_id)
    policy = GroupPolicy.query.get_or_404(policy_id)

    return render_template('accounts/wizard_group_success.html',
                         entity=entity,
                         policy=policy)


# API endpoint for entity autocomplete
@accounts_bp.route('/api/entities/search')
@account_mgmt_or_admin_required
def api_entity_search():
    """API endpoint for entity autocomplete search"""
    q = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)

    if not q or len(q) < 2:
        return jsonify([])

    entities = Entity.query.outerjoin(VendorDetail).filter(
        VendorDetail.id.is_(None),
        Entity.status == 'active',
        Entity.name.ilike(f'%{q}%')
    ).order_by(Entity.name).limit(limit).all()

    results = [{
        'id': e.id,
        'name': e.name,
        'industry': e.industry,
        'city': e.city,
        'state': e.state
    } for e in entities]

    return jsonify(results)


# Quick-add entity endpoint
@accounts_bp.route('/api/entities/quick-add', methods=['POST'])
@account_mgmt_or_admin_required
def api_entity_quick_add():
    """Quick-add entity from modal"""
    name = request.form.get('name')
    industry = request.form.get('industry')
    city = request.form.get('city')
    state = request.form.get('state')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    entity = Entity(
        name=name,
        industry=industry,
        city=city,
        state=state,
        status='active'
    )

    db.session.add(entity)
    db.session.commit()

    return jsonify({
        'id': entity.id,
        'name': entity.name,
        'industry': entity.industry,
        'city': entity.city,
        'state': entity.state
    })