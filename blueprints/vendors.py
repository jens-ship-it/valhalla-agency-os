"""Vendors blueprint for vendor/partner management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.entity import Entity, VendorDetail
from models.distribution import Distribution
from models.contact import Contact, ContactLink
from forms.vendors import VendorForm, VendorSearchForm
from extensions.db import db
from utils.decorators import role_required

vendors_bp = Blueprint('vendors', __name__)


@vendors_bp.route('/')
@role_required('marketing', 'account_mgmt', 'admin')
def vendors():
    """List vendors with search and pagination"""
    search_form = VendorSearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    # Query entities with vendor details
    query = Entity.query.join(VendorDetail).filter(VendorDetail.entity_id == Entity.id)

    # Apply search filter
    if request.args.get('q'):
        search_term = f"%{request.args.get('q')}%"
        query = query.filter(
            db.or_(
                Entity.name.ilike(search_term),
                VendorDetail.vendor_type.ilike(search_term)
            )
        )

    # Apply type filter
    type_filter = request.args.get('vendor_type')
    if type_filter:
        query = query.filter(VendorDetail.vendor_type == type_filter)

    # Apply status filter
    status_filter = request.args.get('status', 'active')
    if status_filter != 'all':
        query = query.filter(Entity.status == status_filter)

    vendors = query.order_by(Entity.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get vendor type choices from VendorDetail
    vendor_type_choices = [
        ('broker_partner', 'Broker Partner'), 
        ('general_agent', 'General Agent'), 
        ('insurer', 'Insurer'), 
        ('administration_services', 'Administration Services'), 
        ('mgu', 'MGU'), 
        ('pbm', 'PBM'), 
        ('consultant', 'Consultant'), 
        ('actuary', 'Actuary'), 
        ('attorney', 'Attorney')
    ]

    # Calculate vendor type counts for all active vendors (not just current page)
    all_vendors_query = Entity.query.join(VendorDetail).filter(
        VendorDetail.entity_id == Entity.id,
        Entity.status == 'active'
    )
    
    vendor_counts = {
        'insurers': all_vendors_query.filter(VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu'])).count(),
        'tpas': all_vendors_query.filter(VendorDetail.vendor_type.in_(['administration_services', 'tpa'])).count(),
        'broker_partners': all_vendors_query.filter(VendorDetail.vendor_type == 'broker_partner').count(),
        'consultants': all_vendors_query.filter(VendorDetail.vendor_type == 'consultant').count()
    }

    return render_template('vendors/vendors.html',
                         vendors=vendors,
                         search_form=search_form,
                         vendor_type_choices=vendor_type_choices,
                         vendor_counts=vendor_counts,
                         view_type='vendors')


@vendors_bp.route('/new', methods=['GET', 'POST'])
@role_required('marketing', 'account_mgmt', 'admin')
def create_vendor():
    """Create new vendor"""
    form = VendorForm()
    form.vendor_type.choices = [('broker_partner', 'Broker Partner'), ('general_agent', 'General Agent'), ('insurer', 'Insurer'), ('administration_services', 'Administration Services'), ('mgu', 'MGU'), ('pbm', 'PBM'), ('consultant', 'Consultant'), ('actuary', 'Actuary'), ('attorney', 'Attorney')]

    if form.validate_on_submit():
        # Create an Entity first
        entity = Entity(
            name=form.name.data,
            status=form.status.data,
            phone=form.phone.data,
            email=form.email.data,
            website=form.website.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            state=form.state.data,
            zip=form.zip.data,
            notes=form.notes.data
        )
        db.session.add(entity)
        db.session.flush() # Flush to get the entity.id

        # Create VendorDetail linked to the Entity
        vendor_detail = VendorDetail(
            entity_id=entity.id,
            vendor_type=form.vendor_type.data,
            description=form.role_description.data
        )
        db.session.add(vendor_detail)
        db.session.commit()

        flash(f'Vendor "{entity.name}" created successfully.', 'success')
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity.id))

    return render_template('vendors/vendor_form.html', form=form, vendor=None)


@vendors_bp.route('/<int:vendor_id>')
@role_required('marketing', 'account_mgmt', 'admin')
def vendor_detail(vendor_id):
    """View vendor details"""
    entity = Entity.query.get_or_404(vendor_id)
    if not hasattr(entity, 'vendor_detail') or not entity.vendor_detail:
        from werkzeug.exceptions import NotFound
        raise NotFound(f"Vendor with id {vendor_id} not found")

    # Assuming Vendor is a wrapper or represents VendorDetail data linked to Entity
    # If Vendor model directly maps to vendor_detail table, adjust accordingly.
    # For now, assuming VendorDetail holds the vendor-specific info.
    vendor_detail = entity.vendor_detail 

    # Get linked contacts
    contact_links = ContactLink.query.filter_by(
        entity_id=vendor_id
    ).join(Contact).order_by(ContactLink.is_primary.desc(), Contact.last_name, Contact.first_name).all()

    return render_template('vendors/vendor_detail.html',
                         entity=entity,
                         vendor=entity,
                         vendor_detail=vendor_detail,
                         contact_links=contact_links)


@vendors_bp.route('/<int:vendor_id>/edit', methods=['GET', 'POST'])
@role_required('marketing', 'account_mgmt', 'admin')
def edit_vendor(vendor_id):
    """Edit vendor"""
    entity = Entity.query.get_or_404(vendor_id)
    if not hasattr(entity, 'vendor_detail') or not entity.vendor_detail:
        from werkzeug.exceptions import NotFound
        raise NotFound(f"Vendor with id {vendor_id} not found")

    vendor_detail = entity.vendor_detail

    # Create form and set choices first
    form = VendorForm()
    form.vendor_type.choices = [('broker_partner', 'Broker Partner'), ('general_agent', 'General Agent'), ('insurer', 'Insurer'), ('administration_services', 'Administration Services'), ('mgu', 'MGU'), ('pbm', 'PBM'), ('consultant', 'Consultant'), ('actuary', 'Actuary'), ('attorney', 'Attorney')]

    # Pre-populate form data on GET request
    if request.method == 'GET':
        form.name.data = entity.name
        form.vendor_type.data = vendor_detail.vendor_type
        form.role_description.data = vendor_detail.description
        form.phone.data = entity.phone
        form.email.data = entity.email
        form.website.data = entity.website
        form.address_line1.data = entity.address_line1
        form.address_line2.data = entity.address_line2
        form.city.data = entity.city
        form.state.data = entity.state
        form.zip.data = entity.zip
        form.notes.data = entity.notes
        form.status.data = entity.status


    if form.validate_on_submit():
        # Update Entity
        entity.name = form.name.data
        entity.status = form.status.data
        entity.phone = form.phone.data
        entity.email = form.email.data
        entity.website = form.website.data
        entity.address_line1 = form.address_line1.data
        entity.address_line2 = form.address_line2.data
        entity.city = form.city.data
        entity.state = form.state.data
        entity.zip = form.zip.data
        entity.notes = form.notes.data

        # Update VendorDetail
        vendor_detail.vendor_type = form.vendor_type.data
        vendor_detail.description = form.role_description.data

        db.session.commit()

        flash(f'Vendor "{entity.name}" updated successfully.', 'success')
        return redirect(url_for('vendors.vendor_detail', vendor_id=entity.id))

    return render_template('vendors/vendor_form.html', form=form, entity=entity, vendor=entity, vendor_detail=vendor_detail)


@vendors_bp.route('/<int:vendor_id>/inactivate', methods=['POST'])
@role_required('marketing', 'account_mgmt', 'admin')
def inactivate_vendor(vendor_id):
    """Inactivate vendor"""
    entity = Entity.query.get_or_404(vendor_id)
    if not hasattr(entity, 'vendor_detail') or not entity.vendor_detail:
        from werkzeug.exceptions import NotFound
        raise NotFound(f"Vendor with id {vendor_id} not found")

    entity.status = 'inactive'
    db.session.commit()

    flash(f'Vendor "{entity.name}" inactivated successfully.', 'success')
    return redirect(url_for('vendors.vendors'))

@vendors_bp.route('/broker-partners')
@login_required
@role_required('marketing', 'admin')
def broker_partners():
    """List all broker partners and their relationships"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')

    # Get broker partners (entities with vendor_type = 'broker_partner')
    query = Entity.query.join(VendorDetail).filter(
        VendorDetail.vendor_type == 'broker_partner',
        Entity.status == 'active'
    )

    if search:
        query = query.filter(Entity.name.ilike(f'%{search}%'))

    brokers = query.order_by(Entity.name).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('vendors/broker_partners.html', brokers=brokers, search=search)


@vendors_bp.route('/broker-partners/<int:broker_id>/clients')
@login_required
@role_required('marketing', 'admin')
def broker_clients(broker_id):
    """Show clients for a specific broker partner"""
    broker = Entity.query.join(VendorDetail).filter(
        Entity.id == broker_id,
        VendorDetail.vendor_type == 'broker_partner'
    ).first_or_404()

    # Get active distribution relationships for this broker
    relationships = Distribution.query.filter_by(
        broker_id=broker_id,
        status='active'
    ).join(Entity, Distribution.entity_id == Entity.id).all()
    
    # Get available clients (organizations that aren't already linked to this broker)
    linked_client_ids = [r.entity_id for r in relationships]
    available_clients = Entity.query.outerjoin(VendorDetail).filter(
        VendorDetail.id.is_(None),  # Not vendors
        Entity.status == 'active',
        ~Entity.id.in_(linked_client_ids) if linked_client_ids else True
    ).order_by(Entity.name).all()

    return render_template('vendors/broker_clients.html',
                         broker=broker, 
                         relationships=relationships,
                         available_clients=available_clients)


@vendors_bp.route('/broker-partners/<int:broker_id>/link-client', methods=['POST'])
@login_required
@role_required('marketing', 'admin')
def link_client_to_broker(broker_id):
    """Link a client organization to a broker partner"""
    from flask import request, flash, redirect, url_for
    
    broker = Entity.query.join(VendorDetail).filter(
        Entity.id == broker_id,
        VendorDetail.vendor_type == 'broker_partner'
    ).first_or_404()
    
    client_id = request.form.get('client_id', type=int)
    relationship_type = request.form.get('relationship_type', 'distribution')
    notes = request.form.get('notes', '')
    
    if not client_id:
        flash('Please select a client to link.', 'danger')
        return redirect(url_for('vendors.broker_clients', broker_id=broker_id))
    
    # Check if relationship already exists
    existing = Distribution.query.filter_by(
        entity_id=client_id,
        broker_id=broker_id,
        status='active'
    ).first()
    
    if existing:
        flash('Client is already linked to this broker partner.', 'warning')
        return redirect(url_for('vendors.broker_clients', broker_id=broker_id))
    
    # Create new distribution relationship
    distribution = Distribution(
        entity_id=client_id,
        broker_id=broker_id,
        relationship_type=relationship_type,
        status='active',
        notes=notes
    )
    
    db.session.add(distribution)
    db.session.commit()
    
    client = Entity.query.get(client_id)
    flash(f'Successfully linked {client.name} to {broker.name}.', 'success')
    return redirect(url_for('vendors.broker_clients', broker_id=broker_id))


@vendors_bp.route('/distribution/<int:relationship_id>/remove', methods=['POST'])
@login_required
@role_required('marketing', 'admin')
def remove_client_relationship(relationship_id):
    """Remove a client-broker relationship"""
    from flask import flash, redirect, url_for
    
    relationship = Distribution.query.get_or_404(relationship_id)
    broker_id = relationship.broker_id
    client_name = relationship.client_entity.name
    broker_name = relationship.broker_entity.name
    
    # Mark as inactive instead of deleting
    relationship.status = 'inactive'
    db.session.commit()
    
    flash(f'Removed relationship between {client_name} and {broker_name}.', 'success')
    return redirect(url_for('vendors.broker_clients', broker_id=broker_id))