"""Public / Catalog API routes — no auth required. Rate limited."""
import re

from flask import Blueprint, request, jsonify

from src.db import get_db
from src.services.auth_service import hash_password
from src.services.audit_log import audit
from src.middleware.rate_limit import rate_limit

public_bp = Blueprint('public', __name__, url_prefix='/api/public')


@public_bp.route('/organisations', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def list_organisations():
    """GET /api/public/organisations — organisation catalog (single source of truth)."""
    session = get_db()
    from src.models.organisation import Organisation

    orgs = session.query(Organisation).all()
    return jsonify([{
        'organisation_guid': o.guid,
        'name': o.name,
        'push_endpoint_url': o.push_endpoint_url,
    } for o in orgs]), 200


@public_bp.route('/organisations/<org_guid>/members', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def list_organisation_members(org_guid):
    """GET /api/public/organisations/<guid>/members — professionals in an org."""
    session = get_db()
    from src.models.organisation import Organisation
    from src.models.user_organisation import UserOrganisation
    from src.models.user import User
    from src.models.professional import Professional

    org = session.query(Organisation).filter_by(guid=org_guid).first()
    if org is None:
        return jsonify({"error": "not_found"}), 404

    links = session.query(UserOrganisation).filter_by(organisation_guid=org_guid).all()
    members = []
    for link in links:
        user = session.query(User).filter_by(guid=link.user_guid).first()
        if user and user.user_type == 'professional':
            prof = session.query(Professional).filter_by(user_id=user.id).first()
            members.append({
                'user_guid': user.guid,
                'first_name': prof.first_name if prof else '',
                'last_name': prof.last_name if prof else '',
                'professional_role': prof.professional_role if prof else '',
                'email': user.email,
            })

    return jsonify(members), 200


@public_bp.route('/groups', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def list_groups():
    """GET /api/public/groups — read-only group catalog."""
    session = get_db()
    from src.models.group import Group

    groups = session.query(Group).all()
    return jsonify([{
        'group_guid': g.guid,
        'name': g.name,
        'category': g.category,
    } for g in groups]), 200


@public_bp.route('/group-leaders', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def list_group_leaders():
    """GET /api/public/group-leaders — list group leaders + SU admins (for access request form)."""
    session = get_db()
    from src.models.user import User
    from src.models.professional import Professional
    from src.models.membership import Membership

    leaders = set()

    # Group admins
    admin_memberships = session.query(Membership).filter_by(
        status='approved', is_admin=True
    ).all()
    for m in admin_memberships:
        leaders.add(m.user_guid)

    # SU admins
    su_users = session.query(User).filter_by(is_su_admin=True).all()
    for u in su_users:
        leaders.add(u.guid)

    result = []
    for guid in leaders:
        user = session.query(User).filter_by(guid=guid).first()
        if user and user.user_type == 'professional':
            prof = session.query(Professional).filter_by(user_id=user.id).first()
            result.append({
                'user_guid': user.guid,
                'first_name': prof.first_name if prof else '',
                'last_name': prof.last_name if prof else '',
                'is_su_admin': user.is_su_admin,
            })

    return jsonify(result), 200


@public_bp.route('/access-request', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def submit_access_request():
    """POST /api/public/access-request — submit professional access request."""
    session = get_db()

    data = request.get_json() if request.is_json else request.form.to_dict()

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    professional_role = data.get('professional_role', '').strip()
    organisation_guid = data.get('organisation_guid', '').strip()
    requested_phases = data.get('requested_phases', [])
    chosen_leader_guid = data.get('chosen_leader_guid', '').strip()

    # Handle string-encoded lists
    if isinstance(requested_phases, str):
        requested_phases = [p.strip() for p in requested_phases.split(',') if p.strip()]

    # Validation
    errors = []
    if not email:
        errors.append('email is required')
    if not password or len(password) < 8:
        errors.append('password must be at least 8 characters')
    if not first_name:
        errors.append('first_name is required')
    if not last_name:
        errors.append('last_name is required')
    if professional_role not in ('doctor', 'nurse', 'other'):
        errors.append('professional_role must be doctor, nurse, or other')
    if not organisation_guid:
        errors.append('organisation_guid is required')
    if not chosen_leader_guid:
        errors.append('chosen_leader_guid is required')

    if errors:
        return jsonify({"error": "validation_error", "messages": errors}), 400

    # Check org exists
    from src.models.organisation import Organisation
    org = session.query(Organisation).filter_by(guid=organisation_guid).first()
    if org is None:
        return jsonify({"error": "not_found", "message": "Organisation not found"}), 404

    # Check leader exists
    from src.models.user import User
    leader = session.query(User).filter_by(guid=chosen_leader_guid).first()
    if leader is None:
        return jsonify({"error": "not_found", "message": "Chosen leader not found"}), 404

    # Check email not already in use
    existing = session.query(User).filter_by(email=email).first()
    if existing:
        return jsonify({"error": "conflict", "message": "Email already registered"}), 409

    from src.models.access_request import AccessRequest
    ar = AccessRequest(
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        professional_role=professional_role,
        organisation_guid=organisation_guid,
        requested_phases=requested_phases,
        chosen_leader_guid=chosen_leader_guid,
        status='pending',
    )
    session.add(ar)
    session.flush()

    audit('access_request_submit', detail={
        'email': email, 'organisation_guid': organisation_guid,
    }, ip=request.remote_addr)

    return jsonify({
        "access_request_guid": ar.guid,
        "status": "pending",
        "message": "Access request submitted. A leader will review your request.",
    }), 201
