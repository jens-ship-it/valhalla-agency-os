"""Sales blueprint for deal pipeline management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from extensions.db import db
from models.sales import Deal
from models.deal_note import DealNote
from models.user import User
from models.contact import Client, Contact
from models.entity import Entity
from utils.decorators import sales_or_admin_required
from utils.forms import DealForm, SearchForm

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/deals')
@sales_or_admin_required
def deals():
    """List deals with filters and pagination"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = Deal.query

    # Apply filters
    stage_filter = request.args.get('stage')
    if stage_filter:
        query = query.filter(Deal.stage == stage_filter)

    owner_filter = request.args.get('owner', type=int)
    if owner_filter:
        query = query.filter(Deal.owner_user_id == owner_filter)

    search_term = request.args.get('q')
    if search_term:
        query = query.filter(Deal.name.ilike(f'%{search_term}%'))

    deals = query.order_by(Deal.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    stage_choices = Deal.get_stage_choices()

    # Group deals by stage for kanban view
    deals_by_stage = {}
    for stage_code, stage_name in stage_choices:
        stage_deals = Deal.query.filter_by(stage=stage_code).order_by(Deal.est_close_date.asc()).limit(10).all()
        deals_by_stage[stage_code] = {
            'name': stage_name,
            'deals': stage_deals
        }

    return render_template('sales/deals.html',
                         deals=deals,
                         deals_by_stage=deals_by_stage,
                         users=users,
                         stage_choices=stage_choices,
                         search_form=search_form)


@sales_bp.route('/deals/new', methods=['GET', 'POST'])
@sales_or_admin_required
def create_deal():
    """Create new deal"""
    form = DealForm()

    # Populate form choices
    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    form.owner_user_id.choices = [(u.id, u.full_name) for u in users]

    entities = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.entity_id.choices = [(0, 'Select Organization (Optional)')] + [(e.id, e.name) for e in entities]

    contacts = Contact.query.filter_by(status='active').order_by(Contact.last_name, Contact.first_name).all()
    form.contact_id.choices = [(0, 'Select Individual (Optional)')] + [(c.id, c.full_name) for c in contacts]

    # Default owner to current user
    if not form.owner_user_id.data:
        form.owner_user_id.data = current_user.id

    if form.validate_on_submit():
        deal = Deal(
            name=form.name.data,
            entity_id=form.entity_id.data or None,
            client_id=form.client_id.data or None,
            stage=form.stage.data,
            owner_user_id=form.owner_user_id.data,
            est_close_date=form.est_close_date.data,
            est_premium_value=form.est_premium_value.data,
            notes=form.notes.data
        )

        db.session.add(deal)
        db.session.commit()

        flash(f'Deal "{deal.name}" created successfully.', 'success')
        return redirect(url_for('sales.deals'))

    return render_template('sales/deal_form.html', form=form, deal=None)


@sales_bp.route('/deals/<int:deal_id>/edit', methods=['GET', 'POST'])
@sales_or_admin_required
def edit_deal(deal_id):
    """Edit deal"""
    deal = Deal.query.get_or_404(deal_id)
    form = DealForm(obj=deal)

    # Populate form choices
    users = User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all()
    form.owner_user_id.choices = [(u.id, u.full_name) for u in users]

    entities = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.entity_id.choices = [(0, 'Select Organization (Optional)')] + [(e.id, e.name) for e in entities]

    contacts = Contact.query.filter_by(status='active').order_by(Contact.last_name, Contact.first_name).all()
    form.contact_id.choices = [(0, 'Select Individual (Optional)')] + [(c.id, c.full_name) for c in contacts]


    if form.validate_on_submit():
        deal.name = form.name.data
        deal.entity_id = form.entity_id.data or None
        deal.client_id = form.client_id.data or None
        deal.stage = form.stage.data
        deal.owner_user_id = form.owner_user_id.data
        deal.est_close_date = form.est_close_date.data
        deal.est_premium_value = form.est_premium_value.data
        deal.notes = form.notes.data

        db.session.commit()

        flash(f'Deal "{deal.name}" updated successfully.', 'success')
        return redirect(url_for('sales.deals'))

    return render_template('sales/deal_form.html', form=form, deal=deal)


@sales_bp.route('/deals/<int:deal_id>/stage', methods=['POST'])
@sales_or_admin_required
def update_deal_stage(deal_id):
    """Update deal stage (for HTMX interactions)"""
    deal = Deal.query.get_or_404(deal_id)
    new_stage = request.form.get('stage')

    if new_stage in [choice[0] for choice in Deal.get_stage_choices()]:
        deal.stage = new_stage
        db.session.commit()
        flash(f'Deal "{deal.name}" moved to {new_stage}.', 'success')

    # Additional logic for "Closed Won" stage: convert contact to client and add policy details
    if new_stage == 'Closed Won':
        # This is a placeholder. In a real application, you would:
        # 1. Find the contact associated with the deal.
        # 2. If the contact is not already a client, create a new Client record for them.
        # 3. Prompt for or gather policy details (e.g., policy number, type, start date).
        # 4. Save the policy details, linking them to the new client.
        # For now, we'll just flash a message indicating the next steps.
        flash(f'Deal "{deal.name}" is Closed Won. Please convert the contact to a client and add policy details.', 'info')

    return redirect(url_for('sales.deals'))


@sales_bp.route('/api/deals/active')
@sales_or_admin_required
def api_active_deals():
    """API endpoint to get active deals for dropdown"""
    try:
        # Simple query without complex joins first
        deals = Deal.query.filter(Deal.stage < 5).order_by(Deal.name).all()

        if not deals:
            # Return empty array if no deals found
            return jsonify([])

        deals_data = []
        for deal in deals:
            try:
                # Safely get client name
                client_name = 'Unknown Client'
                if hasattr(deal, 'entity') and deal.entity:
                    client_name = deal.entity.name
                elif hasattr(deal, 'contact') and deal.contact:
                    client_name = deal.contact.full_name
                
                # Safely get owner name
                owner_name = 'Unassigned'
                if hasattr(deal, 'owner') and deal.owner:
                    owner_name = deal.owner.full_name
                
                deals_data.append({
                    'id': deal.id,
                    'name': deal.name,
                    'client_name': client_name,
                    'stage_name': deal.stage_name,
                    'owner_name': owner_name
                })
            except Exception as deal_error:
                print(f"Error processing deal {deal.id}: {str(deal_error)}")
                # Skip this deal and continue
                continue

        return jsonify(deals_data)
    except Exception as e:
        print(f"Error in api_active_deals: {str(e)}")
        # Return empty array instead of error to prevent frontend crash
        return jsonify([])


@sales_bp.route('/api/deals/<int:deal_id>/notes', methods=['POST'])
@sales_or_admin_required
def api_add_deal_note(deal_id):
    """API endpoint to add a note to a deal"""
    deal = Deal.query.get_or_404(deal_id)

    data = request.get_json()
    note_body = data.get('body', '').strip()

    if not note_body:
        return jsonify({'success': False, 'message': 'Note body is required'}), 400

    # Create the deal note
    note = DealNote(
        deal_id=deal.id,
        user_id=current_user.id,
        body=note_body
    )

    db.session.add(note)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Note added successfully',
        'note_id': note.id
    })


@sales_bp.route('/deals/<int:deal_id>/convert', methods=['GET', 'POST'])
@login_required
def convert_deal(deal_id):
    """Convert a deal to a client with policy"""
    deal = Deal.query.get_or_404(deal_id)

    if request.method == 'POST':
        # Create client from contact
        client = Client(
            contact_id=deal.contact_id,
            status='active',
            created_at=datetime.utcnow()
        )
        db.session.add(client)

        # Update deal status
        deal.status = 'sold'
        deal.closed_at = datetime.utcnow()

        db.session.commit()

        flash(f'Deal converted successfully! {deal.contact.full_name} is now a client.', 'success')
        return redirect(url_for('sales.deals'))

    return render_template('sales/convert_deal.html', deal=deal)


@sales_bp.route('/prospect-view')
@sales_or_admin_required
def prospect_view():
    """Prospect view showing all prospects and their opportunities"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    # Get all active prospects (entities and contacts)
    entities = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    contacts = Contact.query.filter_by(status='active').order_by(Contact.last_name, Contact.first_name).all()

    # Apply search filter if provided
    search_term = request.args.get('q')
    if search_term:
        entities = [
            entity for entity in entities
            if search_term.lower() in entity.name.lower()
        ]
        contacts = [
            contact for contact in contacts
            if search_term.lower() in contact.full_name.lower()
        ]

    # Build prospects data with deal information
    prospects_data = {}
    
    # Process entity prospects
    for entity in entities:
        entity_deals = Deal.query.filter_by(entity_id=entity.id).all()
        prospects_data[f"entity_{entity.id}"] = {
            'type': 'entity',
            'prospect': entity,
            'deals': entity_deals,
            'total_value': sum(deal.est_premium_value or 0 for deal in entity_deals),
            'open_deals': len([deal for deal in entity_deals if deal.is_open]),
            'last_activity': max([deal.updated_at for deal in entity_deals]) if entity_deals else entity.updated_at
        }

    # Process contact prospects  
    for contact in contacts:
        contact_deals = Deal.query.filter_by(contact_id=contact.id).all()
        prospects_data[f"contact_{contact.id}"] = {
            'type': 'contact',
            'prospect': contact,
            'deals': contact_deals,
            'total_value': sum(deal.est_premium_value or 0 for deal in contact_deals),
            'open_deals': len([deal for deal in contact_deals if deal.is_open]),
            'last_activity': max([deal.updated_at for deal in contact_deals]) if contact_deals else contact.updated_at
        }

    # Convert to list and sort by last activity
    prospects_list = list(prospects_data.values())
    prospects_list.sort(key=lambda x: x['last_activity'] or datetime.min, reverse=True)

    # Paginate
    total = len(prospects_list)
    start = (page - 1) * per_page
    end = start + per_page
    prospects_page = prospects_list[start:end]

    # Create pagination object manually
    class Pagination:
        def __init__(self, page, per_page, total, items):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = items
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self):
            for num in range(1, self.pages + 1):
                yield num

    prospects = Pagination(page, per_page, total, prospects_page)

    return render_template('sales/prospect_view.html',
                         prospects=prospects,
                         search_form=search_form)


@sales_bp.route('/api/opportunities')
@login_required
def api_opportunities():
    """API endpoint to get opportunities for note dropdown"""
    try:
        deals = Deal.query.filter(Deal.status.in_(['prospecting', 'qualified', 'proposal', 'negotiation'])).all()
        opportunities = []
        for deal in deals:
            opportunities.append({
                'id': deal.id,
                'title': f"{deal.contact.full_name} - {deal.product_type or 'Unknown Product'}"
            })
        return jsonify({'success': True, 'opportunities': opportunities})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500