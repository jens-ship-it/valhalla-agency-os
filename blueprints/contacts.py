"""Contacts blueprint for universal contact management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.contact import Contact, ContactLink
from models.entity import Entity
from forms.contacts import ContactForm
from extensions.db import db
from extensions.csrf import csrf
from utils.decorators import require_roles
from sqlalchemy import or_
from models.coi import COI
from models.service import ServiceTicket
from utils.forms import SearchForm, COIForm

contacts_bp = Blueprint('contacts', __name__)


@contacts_bp.route('/')
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def contacts():
    """List contacts with search and pagination"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = Contact.query

    # Apply search filter
    if request.args.get('q'):
        search_term = f"%{request.args.get('q')}%"
        query = query.filter(
            or_(
                Contact.first_name.ilike(search_term),
                Contact.last_name.ilike(search_term),
                Contact.email.ilike(search_term)
            )
        )

    # Apply status filter
    status_filter = request.args.get('status', 'active')
    if status_filter != 'all':
        query = query.filter(Contact.status == status_filter)

    contacts = query.order_by(Contact.last_name, Contact.first_name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('contacts/contacts.html',
                         contacts=contacts,
                         search_form=search_form)


@contacts_bp.route('/new', methods=['GET', 'POST'])
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def create_contact():
    """Create new contact"""
    form = ContactForm()

    if form.validate_on_submit():
        contact = Contact(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            work_email=form.email.data,
            phone=form.phone.data,
            mobile=form.mobile.data,
            notes=form.notes.data,
            status=form.status.data
        )

        db.session.add(contact)
        db.session.commit()

        # Auto-link to entity if specified in query params
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id', type=int)
        if entity_type and entity_id:
            contact_link = ContactLink(
                contact_id=contact.id,
                entity_id=entity_id,
                role_at_entity=request.form.get('role_at_entity', ''),
                is_primary=request.args.get('is_primary', 'false').lower() == 'true'
            )
            db.session.add(contact_link)
            db.session.commit()

        flash(f'Contact "{contact.full_name}" created successfully.', 'success')

        # Check for return_to parameter (for organization form flow)
        return_to = request.args.get('return_to')
        if return_to == 'organization_form':
            flash(f'Contact "{contact.full_name}" created. You can now select them in the organization form.', 'info')
            return redirect(url_for('contacts.contact_detail', contact_id=contact.id))

        # Redirect back to entity if auto-linking
        if entity_type and entity_id:
            if entity_type == 'organization':
                return redirect(url_for('accounts.organization_detail', org_id=entity_id))
            elif entity_type == 'individual':
                return redirect(url_for('accounts.individual_detail', individual_id=entity_id))
            elif entity_type == 'vendor':
                return redirect(url_for('vendors.vendor_detail', vendor_id=entity_id))

        return redirect(url_for('contacts.contact_detail', contact_id=contact.id))

    return render_template('contacts/contact_form.html', form=form, contact=None)


@contacts_bp.route('/<int:contact_id>')
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def contact_detail(contact_id):
    """View contact details"""
    contact = Contact.query.get_or_404(contact_id)

    # Get linked entities
    contact_links = ContactLink.query.filter_by(contact_id=contact_id).all()

    # Get service tickets involving this contact through the relationship
    service_tickets = contact.service_tickets

    return render_template('contacts/contact_detail.html',
                         contact=contact,
                         contact_links=contact_links,
                         service_tickets=service_tickets)


@contacts_bp.route('/<int:contact_id>/edit', methods=['GET', 'POST'])
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def edit_contact(contact_id):
    """Edit contact"""
    contact = Contact.query.get_or_404(contact_id)
    form = ContactForm()

    # Pre-populate form data on GET request
    if request.method == 'GET':
        form.first_name.data = contact.first_name
        form.last_name.data = contact.last_name
        form.email.data = contact.work_email
        form.phone.data = contact.phone
        form.mobile.data = contact.mobile
        form.notes.data = contact.notes
        form.status.data = contact.status

    if form.validate_on_submit():
        contact.first_name = form.first_name.data
        contact.last_name = form.last_name.data
        contact.work_email = form.email.data
        contact.phone = form.phone.data
        contact.mobile = form.mobile.data
        contact.notes = form.notes.data
        contact.status = form.status.data

        db.session.commit()

        flash(f'Contact "{contact.full_name}" updated successfully.', 'success')
        return redirect(url_for('contacts.contact_detail', contact_id=contact.id))

    return render_template('contacts/contact_form.html', form=form, contact=contact)


@contacts_bp.route('/<int:contact_id>/inactivate', methods=['POST'])
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def inactivate_contact(contact_id):
    """Inactivate contact"""
    contact = Contact.query.get_or_404(contact_id)
    contact.status = 'inactive'
    db.session.commit()

    flash(f'Contact "{contact.full_name}" inactivated successfully.', 'success')
    return redirect(url_for('contacts.contacts'))


@contacts_bp.route('/<int:contact_id>/delete', methods=['POST'])
@require_roles('admin')
def delete_contact(contact_id):
    """Delete contact (admin only)"""
    contact = Contact.query.get_or_404(contact_id)
    contact_name = contact.full_name

    try:
        db.session.delete(contact)
        db.session.commit()
        flash(f'Contact "{contact_name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting contact: {str(e)}', 'danger')

    return redirect(url_for('contacts.contacts'))


@contacts_bp.route('/search')
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def search_contacts():
    """API endpoint for contact search (HTMX/JSON)"""
    query_string = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)

    contacts = Contact.get_active().filter(
        or_(
            Contact.first_name.ilike(f'%{query_string}%'),
            Contact.last_name.ilike(f'%{query_string}%'),
            Contact.work_email.ilike(f'%{query_string}%'),
            Contact.personal_email.ilike(f'%{query_string}%')
        )
    ).limit(limit).all()

    results = [
        {
            'id': contact.id,
            'name': contact.full_name,
            'title': getattr(contact, 'title', ''),
            'email': contact.preferred_email,
            'phone': contact.preferred_phone
        }
        for contact in contacts
    ]

    return jsonify(results)


@contacts_bp.route('/links', methods=['POST'])
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def create_link():
    """Create contact link to entity"""
    contact_id = request.form.get('contact_id', type=int)
    entity_id = request.form.get('entity_id', type=int)
    role_at_entity = request.form.get('role_at_entity', '')
    is_primary = request.form.get('is_primary', 'false').lower() == 'true'
    entity_type = request.form.get('entity_type') # Added this to make the redirect work

    if not all([contact_id, entity_id]):
        flash('Missing required parameters for contact link.', 'danger')
        return redirect(request.referrer or url_for('contacts.contacts'))

    # Check if link already exists
    existing_link = ContactLink.query.filter_by(
        contact_id=contact_id,
        entity_id=entity_id
    ).first()

    if existing_link:
        flash('Contact is already linked to this entity.', 'warning')
        return redirect(request.referrer or url_for('contacts.contacts'))

    contact_link = ContactLink(
        contact_id=contact_id,
        entity_id=entity_id,
        role_at_entity=role_at_entity,
        is_primary=is_primary
    )

    db.session.add(contact_link)
    db.session.commit()

    contact = Contact.query.get(contact_id)
    flash(f'Contact "{contact.full_name}" linked successfully.', 'success')

    # Redirect back to entity
    if entity_type == 'organization':
        return redirect(url_for('accounts.organization_detail', org_id=entity_id))
    elif entity_type == 'individual':
        return redirect(url_for('accounts.individual_detail', individual_id=entity_id))
    elif entity_type == 'vendor':
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity_id))

    return redirect(url_for('contacts.contacts'))


@contacts_bp.route('/links/<int:link_id>/update', methods=['POST'])
@login_required
def update_link(link_id):
    """Update contact link"""
    contact_link = ContactLink.query.get_or_404(link_id)

    contact_link.role_at_entity = request.form.get('role_at_entity', '')
    contact_link.is_primary = request.form.get('is_primary', 'false').lower() == 'true'

    db.session.commit()

    flash('Contact link updated successfully.', 'success')

    # Redirect back to the appropriate entity detail page
    entity = contact_link.entity
    if entity.is_vendor:
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity.id))
    elif entity.is_organization:
        return redirect(url_for('accounts.organization_detail', org_id=entity.id))
    elif entity.is_individual:
        return redirect(url_for('accounts.individual_detail', individual_id=entity.id))

    return redirect(url_for('contacts.contacts'))


@contacts_bp.route('/links/update', methods=['POST'])
@require_roles('service', 'account_mgmt', 'marketing', 'admin')
def update_contact_link():
    """Update contact link via form submission"""
    link_id = request.form.get('link_id', type=int)

    if not link_id:
        flash('Missing link ID.', 'danger')
        return redirect(request.referrer or url_for('contacts.contacts'))

    contact_link = ContactLink.query.get_or_404(link_id)

    contact_link.role_at_entity = request.form.get('role_at_entity', '')
    contact_link.is_primary = request.form.get('is_primary', 'false').lower() == 'true'

    db.session.commit()

    flash('Contact link updated successfully.', 'success')

    # Redirect back to the appropriate entity detail page
    entity = contact_link.entity
    if entity.is_vendor:
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity.id))
    elif entity.is_organization:
        return redirect(url_for('accounts.organization_detail', org_id=entity.id))
    elif entity.is_individual:
        return redirect(url_for('accounts.individual_detail', individual_id=entity.id))

    return redirect(url_for('contacts.contacts'))


@contacts_bp.route('/links/<int:link_id>/mark-primary', methods=['POST'])
@login_required
def mark_primary(link_id):
    """Mark contact link as primary"""
    contact_link = ContactLink.query.get_or_404(link_id)

    # Remove primary status from other links for this entity
    ContactLink.query.filter_by(
        entity_id=contact_link.entity_id,
        is_primary=True
    ).update({'is_primary': False})

    # Set this link as primary
    contact_link.is_primary = True
    db.session.commit()

    flash('Primary contact updated successfully.', 'success')

    # Redirect back to the appropriate entity detail page
    entity = contact_link.entity
    if hasattr(entity, 'vendor_detail') and entity.vendor_detail:
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity.id))
    else:
        return redirect(url_for('accounts.organization_detail', org_id=entity.id))


@contacts_bp.route('/links/<int:link_id>/unmark-primary', methods=['POST'])
@login_required
def unmark_primary(link_id):
    """Remove primary status from contact link"""
    contact_link = ContactLink.query.get_or_404(link_id)

    # Remove primary status
    contact_link.is_primary = False
    db.session.commit()

    flash('Primary contact status removed successfully.', 'success')

    # Redirect back to the appropriate entity detail page
    entity = contact_link.entity
    if hasattr(entity, 'vendor_detail') and entity.vendor_detail:
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity.id))
    else:
        return redirect(url_for('accounts.organization_detail', org_id=entity.id))


@contacts_bp.route('/links/<int:link_id>/delete', methods=['POST'])
@login_required
def delete_link(link_id):
    """Delete contact link"""
    contact_link = ContactLink.query.get_or_404(link_id)
    entity_id = contact_link.entity_id

    db.session.delete(contact_link)
    db.session.commit()

    flash('Contact unlinked successfully.', 'success')

    # Redirect back to organization detail page
    return redirect(url_for('accounts.organization_detail', org_id=entity_id))



@contacts_bp.route('/contact/<int:contact_id>/coi')
@login_required
def contact_coi(contact_id):
    """View COI records for a contact"""
    contact = Contact.query.get_or_404(contact_id)
    coi_records = COI.get_by_contact(contact_id).order_by(COI.created_at.desc()).all()

    return render_template('contacts/contact_coi.html',
                         contact=contact,
                         coi_records=coi_records)


@contacts_bp.route('/coi/new', methods=['GET', 'POST'])
@login_required
def create_coi():
    """Create new COI record"""
    from models.user import User

    form = COIForm()
    form.user_id.choices = [(u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()]

    if form.validate_on_submit():
        coi = COI(
            contact_id=form.contact_id.data,
            user_id=form.user_id.data,
            category=form.category.data,
            explanation=form.explanation.data,
            notes=form.notes.data,
            status=form.status.data
        )

        db.session.add(coi)
        db.session.commit()

        flash(f'COI record created for {coi.contact.full_name}', 'success')
        return redirect(url_for('contacts.contact_detail', contact_id=coi.contact_id))

    return render_template('contacts/coi_form.html', form=form, title='New COI Record')


@contacts_bp.route('/coi/<int:coi_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_coi(coi_id):
    """Edit COI record"""
    from models.user import User

    coi = COI.query.get_or_404(coi_id)
    form = COIForm(obj=coi)
    form.user_id.choices = [(u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()]

    if form.validate_on_submit():
        coi.contact_id = form.contact_id.data
        coi.user_id = form.user_id.data
        coi.category = form.category.data
        coi.explanation = form.explanation.data
        coi.notes = form.notes.data
        coi.status = form.status.data

        db.session.commit()

        flash(f'COI record updated for {coi.contact.full_name}', 'success')
        return redirect(url_for('contacts.contact_detail', contact_id=coi.contact_id))

    return render_template('contacts/coi_form.html', form=form, coi=coi, title='Edit COI Record')


@contacts_bp.route('/coi/<int:coi_id>/delete', methods=['POST'])
@login_required
def delete_coi(coi_id):
    """Delete COI record"""
    coi = COI.query.get_or_404(coi_id)
    contact_id = coi.contact_id
    contact_name = coi.contact.full_name

    db.session.delete(coi)
    db.session.commit()

    flash(f'COI record deleted for {contact_name}', 'success')
    return redirect(url_for('contacts.contact_detail', contact_id=contact_id))


@contacts_bp.route('/coi')
@login_required
def coi_list():
    """List all COI records"""
    from models.user import User

    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = COI.query

    # Apply filters
    category_filter = request.args.get('category')
    if category_filter:
        query = query.filter(COI.category == category_filter)

    user_filter = request.args.get('user', type=int)
    if user_filter:
        query = query.filter(COI.user_id == user_filter)

    search_term = request.args.get('q')
    if search_term:
        query = query.join(Contact).filter(
            db.or_(
                Contact.first_name.ilike(f'%{search_term}%'),
                Contact.last_name.ilike(f'%{search_term}%'),
                COI.explanation.ilike(f'%{search_term}%')
            )
        )

    coi_records = query.order_by(COI.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    categories = COI.get_category_choices()

    return render_template('contacts/coi_list.html',
                         coi_records=coi_records,
                         users=users,
                         categories=categories)


@contacts_bp.route('/search_contacts')
@login_required
@csrf.exempt
def ajax_search_contacts():
    """AJAX endpoint to search contacts"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify([])

    contacts = Contact.query.filter(
        db.or_(
            Contact.first_name.contains(query),
            Contact.last_name.contains(query),
            Contact.email.contains(query)
        )
    ).limit(10).all()

    return jsonify([{
        'id': contact.id,
        'name': f"{contact.first_name} {contact.last_name}",
        'email': contact.email
    } for contact in contacts])