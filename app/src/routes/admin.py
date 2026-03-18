"""SU Admin API routes — user management, groups, proposals, organisations, CSV."""
import csv
import io
import os

from flask import Blueprint, request, jsonify, g, Response

from src.db import get_db
from src.services.auth_service import hash_password, verify_password
from src.services.audit_log import audit
from src.middleware.auth_middleware import require_auth, require_su

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# --- 7.a: List users ---

@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_su
def list_users():
    """GET /api/admin/users — list all users with membership detail."""
    session = get_db()

    from src.models.user import User
    from src.models.professional import Professional
    from src.models.patient import Patient
    from src.models.membership import Membership
    from src.models.group import Group
    from src.models.user_organisation import UserOrganisation

    users = session.query(User).all()
    result = []
    for u in users:
        entry = {
            'user_guid': u.guid,
            'email': u.email,
            'user_type': u.user_type,
            'is_su_admin': u.is_su_admin,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        }

        if u.user_type == 'professional':
            prof = session.query(Professional).filter_by(user_id=u.id).first()
            if prof:
                entry['professional_guid'] = prof.guid
                entry['professional_role'] = prof.professional_role
                entry['first_name'] = prof.first_name
                entry['last_name'] = prof.last_name

            # Memberships
            memberships = session.query(Membership).filter_by(user_guid=u.guid).all()
            entry['memberships'] = []
            for m in memberships:
                grp = session.query(Group).filter_by(guid=m.group_guid).first()
                entry['memberships'].append({
                    'group_guid': m.group_guid,
                    'group_name': grp.name if grp else None,
                    'status': m.status,
                    'is_admin': m.is_admin,
                })

            # Organisations
            user_orgs = session.query(UserOrganisation).filter_by(user_guid=u.guid).all()
            entry['organization_ids'] = [uo.organisation_guid for uo in user_orgs]

        elif u.user_type == 'patient':
            pat = session.query(Patient).filter_by(user_id=u.id).first()
            if pat:
                entry['patient_guid'] = pat.guid
                entry['organisation_guid'] = pat.organisation_guid

        result.append(entry)

    return jsonify(result), 200


# --- 7.b: Promote SU ---

@admin_bp.route('/promote-su', methods=['POST'])
@require_auth
@require_su
def promote_su():
    """POST /api/admin/promote-su — promote user to SU admin. Requires caller password."""
    session = get_db()
    caller = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    target_guid = data.get('user_guid', '').strip()
    caller_password = data.get('password', '')

    if not target_guid or not caller_password:
        return jsonify({"error": "invalid_request",
                        "message": "user_guid and password required"}), 400

    if not verify_password(caller_password, caller.password_hash):
        return jsonify({"error": "authentication_failed",
                        "message": "Password confirmation failed"}), 401

    from src.models.user import User
    target = session.query(User).filter_by(guid=target_guid).first()
    if target is None:
        return jsonify({"error": "not_found", "message": "User not found"}), 404

    if target.user_type != 'professional':
        return jsonify({"error": "invalid_request",
                        "message": "Only professionals can be SU admins"}), 400

    if target.is_su_admin:
        return jsonify({"error": "conflict", "message": "User is already SU admin"}), 409

    target.is_su_admin = True

    audit('promote_su', user_guid=caller.guid,
          detail={'target_guid': target_guid}, ip=request.remote_addr)

    return jsonify({"user_guid": target_guid, "is_su_admin": True}), 200


# --- 7.c: Delete user ---

@admin_bp.route('/users/<user_guid>', methods=['DELETE'])
@require_auth
@require_su
def delete_user(user_guid):
    """DELETE /api/admin/users/<user_guid> — delete user. Cascade null on decided_by refs."""
    session = get_db()
    caller = g.current_user

    from src.models.user import User
    target = session.query(User).filter_by(guid=user_guid).first()
    if target is None:
        return jsonify({"error": "not_found", "message": "User not found"}), 404

    if target.guid == caller.guid:
        return jsonify({"error": "invalid_request", "message": "Cannot delete yourself"}), 400

    # Null out decided_by references
    from src.models.membership import Membership
    from src.models.group_proposal import GroupProposal
    from src.models.leader_request import LeaderRequest
    from src.models.access_request import AccessRequest

    session.query(Membership).filter_by(decided_by_guid=user_guid).update(
        {'decided_by_guid': None}, synchronize_session='fetch')
    session.query(GroupProposal).filter_by(decided_by_guid=user_guid).update(
        {'decided_by_guid': None}, synchronize_session='fetch')
    session.query(LeaderRequest).filter_by(decided_by_guid=user_guid).update(
        {'decided_by_guid': None}, synchronize_session='fetch')
    session.query(AccessRequest).filter_by(decided_by_guid=user_guid).update(
        {'decided_by_guid': None}, synchronize_session='fetch')

    # Delete memberships for this user
    session.query(Membership).filter_by(user_guid=user_guid).delete(synchronize_session='fetch')

    # Delete user (cascades to patient/professional via relationship)
    session.delete(target)

    audit('delete_user', user_guid=caller.guid,
          detail={'deleted_guid': user_guid, 'email': target.email},
          ip=request.remote_addr)

    return jsonify({"message": "User deleted", "user_guid": user_guid}), 200


# --- 7.d: Delete group ---

@admin_bp.route('/groups/<group_guid>', methods=['DELETE'])
@require_auth
@require_su
def delete_group(group_guid):
    """DELETE /api/admin/groups/<group_guid> — delete group with cascade."""
    session = get_db()
    caller = g.current_user

    from src.models.group import Group
    from src.models.membership import Membership
    from src.models.invite import Invite

    group = session.query(Group).filter_by(guid=group_guid).first()
    if group is None:
        return jsonify({"error": "not_found", "message": "Group not found"}), 404

    # Delete related memberships and invites
    session.query(Membership).filter_by(group_guid=group_guid).delete(synchronize_session='fetch')
    session.query(Invite).filter_by(group_guid=group_guid).delete(synchronize_session='fetch')
    session.delete(group)

    audit('delete_group', user_guid=caller.guid,
          detail={'group_guid': group_guid, 'group_name': group.name},
          ip=request.remote_addr)

    return jsonify({"message": "Group deleted", "group_guid": group_guid}), 200


# --- 7.e: Assign group admin ---

@admin_bp.route('/assign-group-admin', methods=['POST'])
@require_auth
@require_su
def assign_group_admin():
    """POST /api/admin/assign-group-admin — set user as admin in group."""
    session = get_db()
    caller = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    user_guid = data.get('user_guid', '').strip()
    group_guid = data.get('group_guid', '').strip()

    if not user_guid or not group_guid:
        return jsonify({"error": "invalid_request",
                        "message": "user_guid and group_guid required"}), 400

    from src.models.membership import Membership
    membership = session.query(Membership).filter_by(
        user_guid=user_guid, group_guid=group_guid
    ).first()

    if membership is None:
        return jsonify({"error": "not_found",
                        "message": "User is not a member of this group"}), 404

    membership.is_admin = True

    audit('assign_group_admin', user_guid=caller.guid,
          detail={'target_guid': user_guid, 'group_guid': group_guid},
          ip=request.remote_addr)

    return jsonify({"user_guid": user_guid, "group_guid": group_guid, "is_admin": True}), 200


# --- 7.f: Group proposals ---

@admin_bp.route('/group-proposals', methods=['GET'])
@require_auth
@require_su
def list_group_proposals():
    """GET /api/admin/group-proposals — list pending proposals."""
    session = get_db()
    from src.models.group_proposal import GroupProposal

    proposals = session.query(GroupProposal).filter_by(status='pending').all()
    return jsonify([{
        'proposal_guid': p.guid,
        'proposed_name': p.proposed_name,
        'group_type': p.group_type,
        'requested_by_guid': p.requested_by_guid,
        'status': p.status,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    } for p in proposals]), 200


@admin_bp.route('/group-proposals', methods=['POST'])
@require_auth
@require_su
def decide_group_proposal():
    """POST /api/admin/group-proposals — approve or reject. Approve creates the group."""
    session = get_db()
    caller = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    proposal_guid = data.get('proposal_guid', '').strip()
    decision = data.get('decision', '').strip().lower()

    if not proposal_guid or decision not in ('approved', 'rejected'):
        return jsonify({"error": "invalid_request",
                        "message": "proposal_guid and decision (approved/rejected) required"}), 400

    from src.models.group_proposal import GroupProposal
    proposal = session.query(GroupProposal).filter_by(guid=proposal_guid).first()
    if proposal is None:
        return jsonify({"error": "not_found", "message": "Proposal not found"}), 404

    if proposal.status != 'pending':
        return jsonify({"error": "conflict",
                        "message": f"Already decided ({proposal.status})"}), 409

    proposal.status = decision
    proposal.decided_by_guid = caller.guid

    group_guid = None
    if decision == 'approved':
        from src.models.group import Group
        group = Group(name=proposal.proposed_name, group_type=proposal.group_type)
        session.add(group)
        session.flush()
        group_guid = group.guid

    audit('group_proposal_decide', user_guid=caller.guid,
          detail={'proposal_guid': proposal_guid, 'decision': decision,
                  'group_guid': group_guid},
          ip=request.remote_addr)

    return jsonify({
        "proposal_guid": proposal_guid,
        "status": decision,
        "group_guid": group_guid,
    }), 200


# --- 7.g: Leader requests ---

@admin_bp.route('/leader-requests', methods=['GET'])
@require_auth
@require_su
def list_leader_requests():
    """GET /api/admin/leader-requests — list pending leader requests."""
    session = get_db()
    from src.models.leader_request import LeaderRequest

    requests = session.query(LeaderRequest).filter_by(status='pending').all()
    return jsonify([{
        'leader_request_guid': r.guid,
        'user_guid': r.user_guid,
        'group_guid': r.group_guid,
        'status': r.status,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in requests]), 200


@admin_bp.route('/leader-requests', methods=['POST'])
@require_auth
@require_su
def decide_leader_request():
    """POST /api/admin/leader-requests — approve or reject. Approve sets is_admin on membership."""
    session = get_db()
    caller = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    leader_request_guid = data.get('leader_request_guid', '').strip()
    decision = data.get('decision', '').strip().lower()

    if not leader_request_guid or decision not in ('approved', 'rejected'):
        return jsonify({"error": "invalid_request",
                        "message": "leader_request_guid and decision required"}), 400

    from src.models.leader_request import LeaderRequest
    lr = session.query(LeaderRequest).filter_by(guid=leader_request_guid).first()
    if lr is None:
        return jsonify({"error": "not_found", "message": "Leader request not found"}), 404

    if lr.status != 'pending':
        return jsonify({"error": "conflict",
                        "message": f"Already decided ({lr.status})"}), 409

    lr.status = decision
    lr.decided_by_guid = caller.guid

    if decision == 'approved':
        from src.models.membership import Membership
        membership = session.query(Membership).filter_by(
            user_guid=lr.user_guid, group_guid=lr.group_guid
        ).first()
        if membership:
            membership.is_admin = True

    audit('leader_request_decide', user_guid=caller.guid,
          detail={'leader_request_guid': leader_request_guid, 'decision': decision},
          ip=request.remote_addr)

    return jsonify({
        "leader_request_guid": leader_request_guid,
        "status": decision,
    }), 200


# --- 7.h: Access requests ---

@admin_bp.route('/access-requests', methods=['GET'])
@require_auth
@require_su
def list_access_requests():
    """GET /api/admin/access-requests — list pending/endorsed access requests."""
    session = get_db()
    from src.models.access_request import AccessRequest

    requests = session.query(AccessRequest).filter(
        AccessRequest.status.in_(['pending', 'endorsed'])
    ).all()
    return jsonify([{
        'access_request_guid': r.guid,
        'email': r.email,
        'first_name': r.first_name,
        'last_name': r.last_name,
        'professional_role': r.professional_role,
        'organisation_guid': r.organisation_guid,
        'requested_phases': r.requested_phases or [],
        'chosen_leader_guid': r.chosen_leader_guid,
        'status': r.status,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in requests]), 200


@admin_bp.route('/access-requests', methods=['POST'])
@require_auth
@require_su
def decide_access_request():
    """POST /api/admin/access-requests — endorse, approve, or reject.

    Approve creates user + professional + memberships for requested phases.
    """
    session = get_db()
    caller = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    access_request_guid = data.get('access_request_guid', '').strip()
    decision = data.get('decision', '').strip().lower()

    if not access_request_guid or decision not in ('endorsed', 'approved', 'rejected'):
        return jsonify({"error": "invalid_request",
                        "message": "access_request_guid and decision required"}), 400

    from src.models.access_request import AccessRequest
    ar = session.query(AccessRequest).filter_by(guid=access_request_guid).first()
    if ar is None:
        return jsonify({"error": "not_found", "message": "Access request not found"}), 404

    if ar.status in ('approved', 'rejected'):
        return jsonify({"error": "conflict",
                        "message": f"Already decided ({ar.status})"}), 409

    ar.status = decision
    ar.decided_by_guid = caller.guid

    user_guid = None
    if decision == 'approved':
        # Create user + professional
        from src.models.user import User
        from src.models.professional import Professional
        from src.models.user_organisation import UserOrganisation
        from src.models.membership import Membership
        from src.models.group import Group

        user = User(
            email=ar.email,
            password_hash=ar.password_hash,
            user_type='professional',
            is_su_admin=False,
        )
        session.add(user)
        session.flush()

        prof = Professional(
            user_id=user.id,
            professional_role=ar.professional_role,
            first_name=ar.first_name,
            last_name=ar.last_name,
        )
        session.add(prof)

        # Link to organisation
        uo = UserOrganisation(user_guid=user.guid, organisation_guid=ar.organisation_guid)
        session.add(uo)

        # Create memberships for requested phases
        for phase in (ar.requested_phases or []):
            groups = session.query(Group).filter_by(group_type=phase).all()
            for group in groups:
                mem = Membership(
                    user_guid=user.guid,
                    group_guid=group.guid,
                    status='approved',
                    is_admin=False,
                    decided_by_guid=caller.guid,
                )
                session.add(mem)

        session.flush()
        user_guid = user.guid

    audit('access_request_decide', user_guid=caller.guid,
          detail={'access_request_guid': access_request_guid,
                  'decision': decision, 'created_user_guid': user_guid},
          ip=request.remote_addr)

    return jsonify({
        "access_request_guid": access_request_guid,
        "status": decision,
        "user_guid": user_guid,
    }), 200


# --- 7.i: Organisations ---

@admin_bp.route('/organisations', methods=['GET'])
@require_auth
@require_su
def list_organisations():
    """GET /api/admin/organisations — list all organisations. FHIR Organization shape."""
    session = get_db()
    from src.models.organisation import Organisation

    orgs = session.query(Organisation).all()
    return jsonify([{
        'resourceType': Organisation.FHIR_RESOURCE_TYPE,
        'organisation_guid': o.guid,
        'name': o.name,
        'created_at': o.created_at.isoformat() if o.created_at else None,
    } for o in orgs]), 200


@admin_bp.route('/organisations', methods=['POST'])
@require_auth
@require_su
def create_organisation():
    """POST /api/admin/organisations — create new organisation."""
    session = get_db()
    caller = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    name = data.get('name', '').strip()

    if not name:
        return jsonify({"error": "invalid_request", "message": "name required"}), 400

    from src.models.organisation import Organisation
    existing = session.query(Organisation).filter_by(name=name).first()
    if existing:
        return jsonify({"error": "conflict", "message": "Organisation name already exists"}), 409

    org = Organisation(name=name)
    session.add(org)
    session.flush()

    audit('create_organisation', user_guid=caller.guid,
          detail={'org_guid': org.guid, 'name': name}, ip=request.remote_addr)

    return jsonify({
        'resourceType': Organisation.FHIR_RESOURCE_TYPE,
        'organisation_guid': org.guid,
        'name': org.name,
    }), 201


# --- 7.j: Export/Import users ---

@admin_bp.route('/export-users', methods=['GET'])
@require_auth
@require_su
def export_users():
    """GET /api/admin/export-users — CSV export of users."""
    session = get_db()
    from src.models.user import User
    from src.models.professional import Professional
    from src.models.patient import Patient

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['user_guid', 'email', 'user_type', 'is_su_admin',
                     'first_name', 'last_name', 'professional_role', 'created_at'])

    users = session.query(User).all()
    for u in users:
        first_name, last_name, role = '', '', ''
        if u.user_type == 'professional':
            prof = session.query(Professional).filter_by(user_id=u.id).first()
            if prof:
                first_name = prof.first_name or ''
                last_name = prof.last_name or ''
                role = prof.professional_role or ''
        writer.writerow([u.guid, u.email, u.user_type, u.is_su_admin,
                        first_name, last_name, role,
                        u.created_at.isoformat() if u.created_at else ''])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=users_export.csv'},
    )


@admin_bp.route('/import-users', methods=['POST'])
@require_auth
@require_su
def import_users():
    """POST /api/admin/import-users — import users from CSV."""
    session = get_db()
    caller = g.current_user

    if 'file' not in request.files:
        return jsonify({"error": "invalid_request", "message": "CSV file required"}), 400

    file = request.files['file']
    content = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))

    from src.models.user import User
    from src.models.professional import Professional

    created = 0
    skipped = 0
    errors = []

    for row in reader:
        email = row.get('email', '').strip()
        if not email:
            continue

        if session.query(User).filter_by(email=email).first():
            skipped += 1
            continue

        user_type = row.get('user_type', 'professional')
        user = User(
            email=email,
            password_hash=hash_password('changeme01'),  # Temporary password
            user_type=user_type,
            is_su_admin=row.get('is_su_admin', '').lower() == 'true',
        )
        session.add(user)
        session.flush()

        if user_type == 'professional':
            prof = Professional(
                user_id=user.id,
                professional_role=row.get('professional_role', 'other'),
                first_name=row.get('first_name', ''),
                last_name=row.get('last_name', ''),
            )
            session.add(prof)

        created += 1

    audit('import_users', user_guid=caller.guid,
          detail={'created': created, 'skipped': skipped}, ip=request.remote_addr)

    return jsonify({
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }), 200


# --- 7.k: Oath overview ---

@admin_bp.route('/oath-overview', methods=['GET'])
@require_auth
@require_su
def get_oath_overview():
    """GET /api/admin/oath-overview — read oath_overview.csv."""
    from flask import current_app
    oath_path = os.path.join(current_app.root_path, '..', 'oath_overview.csv')

    if not os.path.exists(oath_path):
        return jsonify([]), 200

    with open(oath_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return jsonify(rows), 200


@admin_bp.route('/oath-overview', methods=['PUT'])
@require_auth
@require_su
def update_oath_overview():
    """PUT /api/admin/oath-overview — update oath_overview.csv."""
    from flask import current_app
    session = get_db()
    caller = g.current_user

    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "invalid_request", "message": "Array of rows required"}), 400

    oath_path = os.path.join(current_app.root_path, '..', 'oath_overview.csv')

    if not data:
        return jsonify({"error": "invalid_request", "message": "Empty data"}), 400

    fieldnames = list(data[0].keys())
    with open(oath_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    audit('oath_overview_update', user_guid=caller.guid,
          detail={'rows': len(data)}, ip=request.remote_addr)

    return jsonify({"message": "Oath overview updated", "rows": len(data)}), 200
