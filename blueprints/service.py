"""Service blueprint for service ticket management and reporting"""
import csv
import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from sqlalchemy import func, case, and_, or_

from extensions.db import db
from models.service import ServiceTicket, ServiceNote
from models.user import User
# Organization model replaced by Entity model as Entity # Alias Organization to Entity as per the change request
from models.contact import Contact, Client
from models.entity import Entity
from utils.decorators import service_or_admin_required
from utils.forms import ServiceTicketForm, ServiceNoteForm

service_bp = Blueprint('service', __name__)


@service_bp.route('/tickets')
@service_or_admin_required
def tickets():
    """List service tickets with filters and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = ServiceTicket.query

    # Apply filters
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter(ServiceTicket.status == status_filter)

    priority_filter = request.args.get('priority')
    if priority_filter:
        query = query.filter(ServiceTicket.priority == priority_filter)

    assigned_to_filter = request.args.get('assigned_to', type=int)
    if assigned_to_filter:
        query = query.filter(ServiceTicket.assigned_to_user_id == assigned_to_filter)

    client_type_filter = request.args.get('client_type')
    if client_type_filter:
        query = query.filter(ServiceTicket.client_type == client_type_filter)

    search_term = request.args.get('q')
    if search_term:
        query = query.filter(ServiceTicket.title.ilike(f'%{search_term}%'))

    tickets = query.order_by(ServiceTicket.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    status_choices = ServiceTicket.get_status_choices()
    priority_choices = ServiceTicket.get_priority_choices()
    client_type_choices = ServiceTicket.get_client_type_choices()

    return render_template('service/tickets.html', 
                         tickets=tickets, 
                         users=users,
                         status_choices=status_choices,
                         priority_choices=priority_choices,
                         client_type_choices=client_type_choices)


@service_bp.route('/tickets/new', methods=['GET', 'POST'])
@service_or_admin_required
def create_ticket():
    """Create new service ticket"""
    form = ServiceTicketForm()

    # Populate form choices
    form.status.choices = ServiceTicket.get_status_choices()

    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    form.assigned_to_user_id.choices = [(0, 'Unassigned')] + [(u.id, u.full_name) for u in users]

    # Populate client choices based on selected client_type
    client_type = request.form.get('client_type') or request.args.get('client_type', 'organization')
    if client_type == 'organization':
        clients = Entity.get_organizations().all() # Changed to use Entity
        form.client_id.choices = [(c.id, c.name) for c in clients]
    else:
        clients = Client.query.join(Contact).filter(Contact.status == 'active').order_by(Contact.last_name, Contact.first_name).all()
        form.client_id.choices = [(c.contact_id, c.contact.full_name) for c in clients]

    if form.validate_on_submit():
        ticket = ServiceTicket(
            title=form.title.data,
            description=form.description.data,
            client_type=form.client_type.data,
            client_id=form.client_id.data,
            priority=form.priority.data,
            status=form.status.data,
            due_date=form.due_date.data,
            assigned_to_user_id=form.assigned_to_user_id.data or None,
            created_by_user_id=current_user.id
        )

        db.session.add(ticket)
        db.session.commit()

        flash(f'Service ticket "{ticket.title}" created successfully.', 'success')
        return redirect(url_for('service.ticket_detail', ticket_id=ticket.id))

    return render_template('service/ticket_form.html', form=form, ticket=None)


@service_bp.route('/tickets/<int:ticket_id>')
@service_or_admin_required
def ticket_detail(ticket_id):
    """View service ticket details"""
    ticket = ServiceTicket.query.get_or_404(ticket_id)
    notes = ServiceNote.query.filter_by(ticket_id=ticket_id).order_by(ServiceNote.created_at.desc()).all()

    # Get linked contacts through the relationship
    ticket_contacts = ticket.contacts

    return render_template('service/ticket_detail.html', 
                         ticket=ticket, 
                         notes=notes,
                         ticket_contacts=ticket_contacts)


@service_bp.route('/tickets/<int:ticket_id>/edit', methods=['GET', 'POST'])
@service_or_admin_required
def edit_ticket(ticket_id):
    """Edit service ticket"""
    ticket = ServiceTicket.query.get_or_404(ticket_id)
    form = ServiceTicketForm(obj=ticket)

    # Populate form choices
    form.status.choices = ServiceTicket.get_status_choices()

    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    form.assigned_to_user_id.choices = [(0, 'Unassigned')] + [(u.id, u.full_name) for u in users]

    # Populate client choices
    if ticket.client_type == 'organization':
        clients = Entity.get_organizations().all() # Changed to use Entity
        form.client_id.choices = [(c.id, c.name) for c in clients]
    else:
        clients = Client.query.join(Contact).filter(Contact.status == 'active').order_by(Contact.last_name, Contact.first_name).all()
        form.client_id.choices = [(c.contact_id, c.contact.full_name) for c in clients]

    if form.validate_on_submit():
        ticket.title = form.title.data
        ticket.description = form.description.data
        ticket.client_type = form.client_type.data
        ticket.client_id = form.client_id.data
        ticket.priority = form.priority.data
        ticket.status = form.status.data
        ticket.due_date = form.due_date.data
        ticket.assigned_to_user_id = form.assigned_to_user_id.data or None

        db.session.commit()

        flash(f'Service ticket "{ticket.title}" updated successfully.', 'success')
        return redirect(url_for('service.ticket_detail', ticket_id=ticket.id))

    return render_template('service/ticket_form.html', form=form, ticket=ticket)


@service_bp.route('/tickets/<int:ticket_id>/notes', methods=['POST'])
@service_or_admin_required
def add_note(ticket_id):
    """Add note to service ticket"""
    ticket = ServiceTicket.query.get_or_404(ticket_id)
    form = ServiceNoteForm()

    if form.validate_on_submit():
        note = ServiceNote(
            ticket_id=ticket_id,
            author_user_id=current_user.id,
            body=form.body.data
        )

        db.session.add(note)
        db.session.commit()

        flash('Note added successfully.', 'success')

    return redirect(url_for('service.ticket_detail', ticket_id=ticket_id))


@service_bp.route('/tickets/<int:ticket_id>/close', methods=['POST'])
@service_or_admin_required
def close_ticket(ticket_id):
    """Close service ticket"""
    ticket = ServiceTicket.query.get_or_404(ticket_id)
    ticket.status = 'complete'
    db.session.commit()

    flash(f'Service ticket "{ticket.title}" closed successfully.', 'success')
    return redirect(url_for('service.ticket_detail', ticket_id=ticket_id))


@service_bp.route('/reports')
@service_or_admin_required
def reports():
    """Service reporting dashboard"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    client_type = request.args.get('client_type')
    client_id = request.args.get('client_id', type=int)
    assigned_to = request.args.get('assigned_to', type=int)
    status_filters = request.args.getlist('status')
    priority = request.args.get('priority')
    search = request.args.get('search')

    # Base query
    query = ServiceTicket.query

    # Apply filters
    if start_date:
        query = query.filter(ServiceTicket.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(ServiceTicket.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    if client_type:
        query = query.filter(ServiceTicket.client_type == client_type)
    if client_id:
        query = query.filter(ServiceTicket.client_id == client_id)
    if assigned_to:
        query = query.filter(ServiceTicket.assigned_to_user_id == assigned_to)
    if status_filters:
        query = query.filter(ServiceTicket.status.in_(status_filters))
    if priority:
        query = query.filter(ServiceTicket.priority == priority)
    if search:
        query = query.filter(ServiceTicket.title.ilike(f'%{search}%'))

    # Generate summary by client
    client_summary = generate_client_summary(query)

    # Generate breakdown by assigned user
    user_breakdown = generate_user_breakdown(query)

    # Get filter options
    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    organizations = Entity.get_organizations().all() # Changed to use Entity
    clients = Client.query.join(Contact).filter(Contact.status == 'active').order_by(Contact.last_name, Contact.first_name).all() # Changed to use Client

    return render_template('service/reports.html',
                         client_summary=client_summary,
                         user_breakdown=user_breakdown,
                         users=users,
                         organizations=organizations,
                         clients=clients, # Changed to use Client
                         status_choices=ServiceTicket.get_status_choices(),
                         priority_choices=ServiceTicket.get_priority_choices())


def generate_client_summary(base_query):
    """Generate summary statistics grouped by client"""
    # Get the list of ticket IDs from the base query
    ticket_ids = [ticket.id for ticket in base_query.all()]
    
    # If no tickets match the filter, return empty list
    if not ticket_ids:
        return []
    
    # Query for organization clients
    org_summary = db.session.query(
        Entity.id, # Changed to use Entity
        Entity.name.label('client_name'), # Changed to use Entity
        db.literal('organization').label('client_type'),
        func.count(ServiceTicket.id).label('total_tickets'),
        func.sum(case((ServiceTicket.status.in_(ServiceTicket.get_open_statuses()), 1), else_=0)).label('open_count'),
        func.sum(case((ServiceTicket.status == 'complete_pending_confirmation', 1), else_=0)).label('pending_confirmation_count'),
        func.sum(case((ServiceTicket.status == 'complete', 1), else_=0)).label('complete_count'),
        func.avg(
            case((ServiceTicket.status.in_(ServiceTicket.get_open_statuses()), 
                 func.julianday('now') - func.julianday(ServiceTicket.created_at)), else_=None)
        ).label('avg_age_open'),
        func.min(
            case((ServiceTicket.status.in_(ServiceTicket.get_open_statuses()), ServiceTicket.due_date), else_=None)
        ).label('oldest_open_due_date')
    ).join(
        ServiceTicket, and_(
            Entity.id == ServiceTicket.client_id, # Changed to use Entity
            ServiceTicket.client_type == 'organization'
        )
    ).filter(
        ServiceTicket.id.in_(ticket_ids)
    ).group_by(Entity.id, Entity.name).all() # Changed to use Entity

    # Query for individual clients
    ind_summary = db.session.query(
        Client.contact_id, # Changed to use Client.contact_id
        Contact.first_name.concat(' ').concat(Contact.last_name).label('client_name'), # Changed to use Contact
        db.literal('individual').label('client_type'),
        func.count(ServiceTicket.id).label('total_tickets'),
        func.sum(case((ServiceTicket.status.in_(ServiceTicket.get_open_statuses()), 1), else_=0)).label('open_count'),
        func.sum(case((ServiceTicket.status == 'complete_pending_confirmation', 1), else_=0)).label('pending_confirmation_count'),
        func.sum(case((ServiceTicket.status == 'complete', 1), else_=0)).label('complete_count'),
        func.avg(
            case((ServiceTicket.status.in_(ServiceTicket.get_open_statuses()), 
                 func.julianday('now') - func.julianday(ServiceTicket.created_at)), else_=None)
        ).label('avg_age_open'),
        func.min(
            case((ServiceTicket.status.in_(ServiceTicket.get_open_statuses()), ServiceTicket.due_date), else_=None)
        ).label('oldest_open_due_date')
    ).join(
        Contact, Client.contact_id == Contact.id
    ).join(
        ServiceTicket, and_(
            Client.contact_id == ServiceTicket.client_id, # Changed to use Client.contact_id
            ServiceTicket.client_type == 'individual'
        )
    ).filter(
        ServiceTicket.id.in_(ticket_ids)
    ).group_by(Client.contact_id, Contact.first_name, Contact.last_name).all() # Changed to use Client.contact_id and Contact

    return list(org_summary) + list(ind_summary)


def generate_user_breakdown(base_query):
    """Generate breakdown by assigned user per client"""
    # Get the list of ticket IDs from the base query
    ticket_ids = [ticket.id for ticket in base_query.all()]
    
    # If no tickets match the filter, return empty list
    if not ticket_ids:
        return []
    
    # This is a simplified version - in production you'd want more sophisticated pivot logic
    breakdown = db.session.query(
        ServiceTicket.client_type,
        ServiceTicket.client_id,
        (User.first_name + ' ' + User.last_name).label('assigned_user'),
        func.count(ServiceTicket.id).label('ticket_count')
    ).outerjoin(
        User, ServiceTicket.assigned_to_user_id == User.id
    ).filter(
        ServiceTicket.id.in_(ticket_ids)
    ).group_by(
        ServiceTicket.client_type,
        ServiceTicket.client_id,
        ServiceTicket.assigned_to_user_id,
        User.first_name,
        User.last_name
    ).all()

    return breakdown


@service_bp.route('/reports/export')
@service_or_admin_required
def export_csv():
    """Export service reports to CSV"""
    # Similar filtering logic as reports route
    query = ServiceTicket.query
    # Apply same filters...

    client_summary = generate_client_summary(query)

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Client Name', 'Client Type', 'Open Count', 
        'Pending Confirmation', 'Complete Count', 
        'Avg Age Open (Days)', 'Oldest Open Due Date', 'Total Tickets'
    ])

    # Write data
    for row in client_summary:
        writer.writerow([
            row.client_name,
            row.client_type,
            row.open_count or 0,
            row.pending_confirmation_count or 0,
            row.complete_count or 0,
            round(row.avg_age_open or 0, 1),
            row.oldest_open_due_date or '',
            row.total_tickets
        ])

    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=service_report_{date.today()}.csv'

    return response


@service_bp.route('/api/clients')
@service_or_admin_required
def api_clients():
    """API endpoint to get clients by type"""
    client_type = request.args.get('type', 'organization')

    if client_type == 'organization':
        clients = Entity.get_organizations().all() # Changed to use Entity
        return jsonify([{'id': c.id, 'name': c.name} for c in clients])
    else:
        clients = Client.query.join(Contact).filter(Contact.status == 'active').order_by(Contact.last_name, Contact.first_name).all() # Changed to use Client
        return jsonify([{'id': c.contact_id, 'name': c.contact.full_name} for c in clients]) # Changed to use Client and Contact

# New route to display table structure
@service_bp.route('/tickets/schema')
@service_or_admin_required
def ticket_schema():
    """Display the schema of the ServiceTicket table."""
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = inspector.get_columns('service_ticket')
    schema = {col['name']: str(col['type']) for col in columns}
    return render_template('service/schema.html', schema=schema, table_name='ServiceTicket')