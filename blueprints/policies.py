"""Policies blueprint for managing both group and individual policies"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from sqlalchemy import or_, and_
from datetime import date

from extensions.db import db
from models.policy import GroupPolicy, IndividualPolicy
from models.entity import Entity
from models.contact import Contact, Client
from utils.decorators import account_mgmt_or_admin_required
from forms.accounts import GroupPolicyForm, IndividualPolicyForm
from utils.forms import SearchForm

policies_bp = Blueprint('policies', __name__)


@policies_bp.route('/policies')
@account_mgmt_or_admin_required
def policies():
    """List all policies with search and pagination"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    policy_type = request.args.get('type', 'all')  # all, group, individual
    status_filter = request.args.get('status', 'active')

    # Get group policies
    group_policies = []
    if policy_type in ['all', 'group']:
        group_query = db.session.query(GroupPolicy).join(Entity, GroupPolicy.entity_id == Entity.id)

        if request.args.get('q'):
            search_term = f"%{request.args.get('q')}%"
            group_query = group_query.filter(
                or_(
                    Entity.name.ilike(search_term),
                    GroupPolicy.policy_number.ilike(search_term),
                    GroupPolicy.product_type.ilike(search_term)
                )
            )

        if status_filter != 'all':
            if status_filter == 'terminated_lapsed':
                group_query = group_query.filter(GroupPolicy.status.in_(['terminated', 'lapsed']))
            else:
                group_query = group_query.filter(GroupPolicy.status == status_filter)

        group_policies = group_query.order_by(GroupPolicy.effective_date.desc()).all()

        # Individual policies query with search
        individual_query = db.session.query(IndividualPolicy).join(
            Client, IndividualPolicy.client_id == Client.id
        ).join(Contact, Client.contact_id == Contact.id)

        if request.args.get('q'):
            search_term = f"%{request.args.get('q')}%"
            individual_query = individual_query.filter(
                or_(
                    Contact.first_name.ilike(search_term),
                    Contact.last_name.ilike(search_term),
                    IndividualPolicy.policy_number.ilike(search_term),
                    IndividualPolicy.product_type.ilike(search_term)
                )
            )

        if status_filter != 'all':
            if status_filter == 'terminated_lapsed':
                individual_query = individual_query.filter(IndividualPolicy.status.in_(['terminated', 'lapsed']))
            else:
                individual_query = individual_query.filter(IndividualPolicy.status == status_filter)

        individual_policies = individual_query.order_by(IndividualPolicy.effective_date.desc()).all()

    # Combine and sort by date
    all_policies = []
    for policy in group_policies:
        all_policies.append({
            'type': 'group',
            'policy': policy,
            'client_name': policy.entity.name,
            'client_id': policy.entity.id,
            'effective_date': policy.effective_date
        })

    for policy in individual_policies:
        all_policies.append({
            'type': 'individual',
            'policy': policy,
            'client_name': policy.client.full_name,
            'client_id': policy.client.id,
            'effective_date': policy.effective_date
        })

    # Sort by effective date (newest first)
    all_policies.sort(key=lambda x: x['effective_date'] or date.min, reverse=True)

    # Manual pagination
    total = len(all_policies)
    start = (page - 1) * per_page
    end = start + per_page
    policies_page = all_policies[start:end]

    # Create pagination object
    has_prev = page > 1
    has_next = end < total
    prev_num = page - 1 if has_prev else None
    next_num = page + 1 if has_next else None

    class PaginationObject:
        def __init__(self, items, total, page, per_page, has_prev, has_next, prev_num, next_num, pages):
            self.items = items
            self.total = total
            self.page = page
            self.per_page = per_page
            self.has_prev = has_prev
            self.has_next = has_next
            self.prev_num = prev_num
            self.next_num = next_num
            self.pages = pages

    pagination = PaginationObject(
        items=policies_page,
        total=total,
        page=page,
        per_page=per_page,
        has_prev=has_prev,
        has_next=has_next,
        prev_num=prev_num,
        next_num=next_num,
        pages=(total + per_page - 1) // per_page
    )

    return render_template('policies/policies.html',
                         policies=pagination,
                         search_form=search_form,
                         policy_type=policy_type,
                         status_filter=status_filter)


@policies_bp.route('/policies/new')
@account_mgmt_or_admin_required
def new_policy():
    """Choose policy type to create"""
    return render_template('policies/new_policy_type.html')


@policies_bp.route('/policies/group/new', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def create_group_policy():
    """Create new group policy"""
    form = GroupPolicyForm()

    # Get organizations for entity selection
    organizations = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.entity_id.choices = [(org.id, org.name) for org in organizations]

    # Get all vendors for carrier choices (not just insurers)
    from models.entity import VendorDetail
    vendors = Entity.query.join(VendorDetail).filter(
        Entity.status == 'active'
    ).order_by(Entity.name).all()
    form.carrier_id.choices = [(v.id, v.name) for v in vendors]

    form.product_type.choices = [
        ('medical', 'Medical'),
        ('dental', 'Dental'),
        ('vision', 'Vision'),
        ('life', 'Life'),
        ('std', 'Short Term Disability'),
        ('ltd', 'Long Term Disability'),
        ('administration_services', 'Administration Services'),
        ('other', 'Other')
    ]

    if form.validate_on_submit():
        policy = GroupPolicy(
            entity_id=form.entity_id.data,
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

        flash(f'Group policy created successfully.', 'success')
        return redirect(url_for('policies.policies'))

    return render_template('policies/group_policy_form.html', form=form, policy=None)


@policies_bp.route('/policies/individual/new', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def create_individual_policy():
    """Create new individual policy"""
    form = IndividualPolicyForm()

    # Get individuals for client selection - but we're actually showing contacts
    individuals = Contact.query.filter_by(status='active').order_by(Contact.last_name, Contact.first_name).all()
    form.client_id.choices = [(ind.id, ind.full_name) for ind in individuals]

    # Get all vendors for carrier choices (not just insurers)
    from models.entity import VendorDetail
    vendors = Entity.query.join(VendorDetail).filter(
        Entity.status == 'active'
    ).order_by(Entity.name).all()
    form.carrier_id.choices = [(v.id, v.name) for v in vendors]

    # Get corporate entities for corporate relationship
    organizations = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.corporate_entity_id.choices = [('', 'Select Organization...')] + [(org.id, org.name) for org in organizations]

    if form.validate_on_submit():
        # Get the contact_id from the form (which is actually storing contact IDs, not client IDs)
        contact_id = form.client_id.data

        # Find or create the Client record for this contact
        client = Client.query.filter_by(contact_id=contact_id).first()
        if not client:
            # Create client record if it doesn't exist
            client = Client(contact_id=contact_id)
            db.session.add(client)
            db.session.flush()  # Get the client ID

        # Handle corporate entity ID conversion
        corporate_entity_id = None
        if form.is_corporate_related.data and form.corporate_entity_id.data:
            try:
                corporate_entity_id = int(form.corporate_entity_id.data)
            except (ValueError, TypeError):
                corporate_entity_id = None

        policy = IndividualPolicy(
            client_id=client.id,
            carrier_id=form.carrier_id.data,
            product_type=form.product_type.data,
            policy_number=form.policy_number.data,
            face_amount=form.face_amount.data,
            effective_date=form.effective_date.data,
            status=form.status.data,
            is_corporate_related=form.is_corporate_related.data,
            corporate_entity_id=corporate_entity_id,
            corporate_explanation=form.corporate_explanation.data if form.is_corporate_related.data else None,
            notes=form.notes.data
        )

        db.session.add(policy)
        db.session.commit()

        flash(f'Individual policy created successfully.', 'success')
        return redirect(url_for('policies.individual_policy_detail', policy_id=policy.id))

    return render_template('policies/individual_policy_form.html', form=form, policy=None)


@policies_bp.route('/policies/group/<int:policy_id>')
@account_mgmt_or_admin_required
def group_policy_detail(policy_id):
    """View group policy details"""
    policy = GroupPolicy.query.get_or_404(policy_id)
    return render_template('policies/group_policy_detail.html', policy=policy)


@policies_bp.route('/policies/individual/<int:policy_id>')
@account_mgmt_or_admin_required
def individual_policy_detail(policy_id):
    """View individual policy details"""
    policy = IndividualPolicy.query.get_or_404(policy_id)
    return render_template('policies/individual_policy_detail.html', policy=policy)


@policies_bp.route('/policies/group/<int:policy_id>/edit', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def edit_group_policy(policy_id):
    """Edit group policy"""
    policy = GroupPolicy.query.get_or_404(policy_id)
    form = GroupPolicyForm(obj=policy)

    # Get organizations for entity selection
    organizations = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.entity_id.choices = [(org.id, org.name) for org in organizations]

    # Get all vendors for carrier choices (not just insurers)
    from models.entity import VendorDetail
    vendors = Entity.query.join(VendorDetail).filter(
        Entity.status == 'active'
    ).order_by(Entity.name).all()
    form.carrier_id.choices = [(v.id, v.name) for v in vendors]

    form.product_type.choices = [
        ('medical', 'Medical'),
        ('dental', 'Dental'),
        ('vision', 'Vision'),
        ('life', 'Life'),
        ('std', 'Short Term Disability'),
        ('ltd', 'Long Term Disability'),
        ('administration_services', 'Administration Services'),
        ('other', 'Other')
    ]

    if form.validate_on_submit():
        policy.entity_id = form.entity_id.data
        policy.carrier_id = form.carrier_id.data
        policy.product_type = form.product_type.data
        policy.policy_number = form.policy_number.data
        policy.effective_date = form.effective_date.data
        policy.renewal_date = form.renewal_date.data
        policy.funding = form.funding.data
        policy.estimated_monthly_revenue = form.estimated_monthly_revenue.data
        policy.status = form.status.data
        policy.notes = form.notes.data

        db.session.commit()

        flash(f'Group policy updated successfully.', 'success')
        return redirect(url_for('policies.group_policy_detail', policy_id=policy.id))

    return render_template('policies/group_policy_form.html', form=form, policy=policy)


@policies_bp.route('/policies/individual/<int:policy_id>/edit', methods=['GET', 'POST'])
@account_mgmt_or_admin_required
def edit_individual_policy(policy_id):
    """Edit individual policy"""
    policy = IndividualPolicy.query.get_or_404(policy_id)
    form = IndividualPolicyForm()

    # Get insurance vendors for carrier choices
    from models.entity import VendorDetail
    vendors = Entity.query.join(VendorDetail).filter(
        VendorDetail.vendor_type.in_(['insurer', 'general_agent', 'mgu']),
        Entity.status == 'active'
    ).order_by(Entity.name).all()
    form.carrier_id.choices = [('', 'Select Carrier')] + [(str(v.id), v.name) for v in vendors]

    # Get corporate entities for corporate relationship
    organizations = Entity.query.filter_by(status='active').order_by(Entity.name).all()
    form.corporate_entity_id.choices = [('', 'Select Organization...')] + [(str(org.id), org.name) for org in organizations]

    # Set product type choices
    form.product_type.choices = [
        ('', 'Select Product Type'),
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('di', 'Disability Insurance'),
        ('ltc', 'Long-term Care'),
        ('annuity', 'Annuity'),
        ('other', 'Other')
    ]

    # Pre-populate form on GET
    if request.method == 'GET':
        form.carrier_id.data = str(policy.carrier_id) if policy.carrier_id else ''
        form.product_type.data = policy.product_type
        form.policy_number.data = policy.policy_number
        form.face_amount.data = policy.face_amount
        form.premium_amount.data = policy.premium_amount
        form.premium_frequency.data = policy.premium_frequency
        form.effective_date.data = policy.effective_date
        form.maturity_date.data = policy.maturity_date
        form.is_corporate_related.data = policy.is_corporate_related
        form.corporate_entity_id.data = str(policy.corporate_entity_id) if policy.corporate_entity_id else ''
        form.corporate_explanation.data = policy.corporate_explanation
        form.status.data = policy.status
        form.notes.data = policy.notes

    if form.validate_on_submit():
        # Convert string IDs to integers
        carrier_id = int(form.carrier_id.data) if form.carrier_id.data else None

        corporate_entity_id = None
        if form.corporate_entity_id.data and form.corporate_entity_id.data != '':
            try:
                corporate_entity_id = int(form.corporate_entity_id.data)
            except (ValueError, TypeError):
                corporate_entity_id = None

        # Update policy
        policy.carrier_id = carrier_id
        policy.product_type = form.product_type.data
        policy.policy_number = form.policy_number.data
        policy.face_amount = form.face_amount.data
        policy.premium_amount = form.premium_amount.data
        policy.premium_frequency = form.premium_frequency.data
        policy.effective_date = form.effective_date.data
        policy.maturity_date = form.maturity_date.data
        policy.is_corporate_related = form.is_corporate_related.data
        policy.corporate_entity_id = corporate_entity_id
        policy.corporate_explanation = form.corporate_explanation.data
        policy.status = form.status.data
        policy.notes = form.notes.data

        db.session.commit()

        flash(f'Individual policy updated successfully.', 'success')
        return redirect(url_for('policies.individual_policy_detail', policy_id=policy.id))

    return render_template('policies/individual_policy_form.html', form=form, policy=policy)


@policies_bp.route('/policies/group/<int:policy_id>/terminate', methods=['POST'])
@account_mgmt_or_admin_required
def terminate_group_policy(policy_id):
    """Terminate a group policy"""
    policy = GroupPolicy.query.get_or_404(policy_id)

    # Update policy status to terminated
    policy.status = 'terminated'
    db.session.commit()

    flash(f'Group policy {policy.policy_number or "for " + policy.carrier.name if policy.carrier else ""} terminated successfully.', 'success')
    return '', 204  # No content response for AJAX call


@policies_bp.route('/individual/<int:policy_id>/lapse', methods=['POST'])
@account_mgmt_or_admin_required
def lapse_individual_policy(policy_id):
    """Lapse individual policy"""
    policy = IndividualPolicy.query.get_or_404(policy_id)

    if policy.status != 'active':
        flash('Only active policies can be lapsed.', 'warning')
        return redirect(url_for('policies.individual_policy_detail', policy_id=policy_id))

    policy.status = 'lapsed'
    db.session.commit()

    flash(f'Policy {policy.policy_number or policy_id} has been lapsed.', 'success')
    return jsonify({'success': True})