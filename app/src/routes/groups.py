"""Professional & Group API routes — groups, membership, admin, invites."""
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, g

from src.db import get_db
from src.services.audit_log import audit
from src.middleware.auth_middleware import require_auth, require_professional, require_group_admin

groups_bp = Blueprint('groups', __name__, url_prefix='/api/groups')


@groups_bp.route('', methods=['GET'])
@require_auth
@require_professional
def list_groups():
    """GET /api/groups — list own approved groups. FHIR Group shape."""
    session = get_db()
    user = g.current_user

    from src.models.membership import Membership
    from src.models.group import Group

    memberships = session.query(Membership).filter_by(
        user_guid=user.guid, status='approved'
    ).all()

    groups = []
    for m in memberships:
        group = session.query(Group).filter_by(guid=m.group_guid).first()
        if group:
            groups.append({
                'resourceType': Group.FHIR_RESOURCE_TYPE,
                'group_guid': group.guid,
                'name': group.name,
                'category': group.category,
                'is_admin': m.is_admin,
                'membership_status': m.status,
            })

    return jsonify(groups), 200


@groups_bp.route('/request-membership', methods=['POST'])
@require_auth
@require_professional
def request_membership():
    """POST /api/groups/request-membership — request to join a group."""
    session = get_db()
    user = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    group_guid = data.get('group_guid', '').strip()

    if not group_guid:
        return jsonify({"error": "invalid_request", "message": "group_guid required"}), 400

    from src.models.group import Group
    group = session.query(Group).filter_by(guid=group_guid).first()
    if group is None:
        return jsonify({"error": "not_found", "message": "Group not found"}), 404

    from src.models.membership import Membership
    existing = session.query(Membership).filter_by(
        user_guid=user.guid, group_guid=group_guid
    ).first()
    if existing:
        return jsonify({"error": "conflict",
                        "message": f"Membership already exists (status: {existing.status})"}), 409

    membership = Membership(
        user_guid=user.guid,
        group_guid=group_guid,
        status='pending',
        is_admin=False,
    )
    session.add(membership)
    session.flush()

    audit('membership_request', user_guid=user.guid,
          detail={'group_guid': group_guid, 'group_name': group.name},
          ip=request.remote_addr)

    return jsonify({
        "membership_guid": membership.guid,
        "group_guid": group_guid,
        "status": "pending",
    }), 201


@groups_bp.route('/request-admin', methods=['POST'])
@require_auth
@require_professional
def request_admin():
    """POST /api/groups/request-admin — request group admin role."""
    session = get_db()
    user = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    group_guid = data.get('group_guid', '').strip()

    if not group_guid:
        return jsonify({"error": "invalid_request", "message": "group_guid required"}), 400

    from src.models.group import Group
    group = session.query(Group).filter_by(guid=group_guid).first()
    if group is None:
        return jsonify({"error": "not_found", "message": "Group not found"}), 404

    from src.models.leader_request import LeaderRequest
    existing = session.query(LeaderRequest).filter_by(
        user_guid=user.guid, group_guid=group_guid, status='pending'
    ).first()
    if existing:
        return jsonify({"error": "conflict", "message": "Pending admin request already exists"}), 409

    lr = LeaderRequest(
        user_guid=user.guid,
        group_guid=group_guid,
        status='pending',
    )
    session.add(lr)
    session.flush()

    audit('leader_request', user_guid=user.guid,
          detail={'group_guid': group_guid, 'group_name': group.name},
          ip=request.remote_addr)

    return jsonify({
        "leader_request_guid": lr.guid,
        "group_guid": group_guid,
        "status": "pending",
    }), 201


@groups_bp.route('/admin/pending', methods=['GET'])
@require_auth
@require_group_admin
def admin_pending():
    """GET /api/groups/admin/pending — list pending memberships for admin's groups."""
    session = get_db()
    user = g.current_user

    from src.models.membership import Membership
    from src.models.group import Group
    from src.models.user import User

    # Get groups where user is admin (or SU admin sees all)
    if user.is_su_admin:
        groups = session.query(Group).all()
        admin_group_guids = [g_obj.guid for g_obj in groups]
    else:
        admin_memberships = session.query(Membership).filter_by(
            user_guid=user.guid, status='approved', is_admin=True
        ).all()
        admin_group_guids = [m.group_guid for m in admin_memberships]

    if not admin_group_guids:
        return jsonify([]), 200

    pending = session.query(Membership).filter(
        Membership.group_guid.in_(admin_group_guids),
        Membership.status == 'pending'
    ).all()

    result = []
    for m in pending:
        group = session.query(Group).filter_by(guid=m.group_guid).first()
        req_user = session.query(User).filter_by(guid=m.user_guid).first()
        result.append({
            'membership_guid': m.guid,
            'user_guid': m.user_guid,
            'user_email': req_user.email if req_user else None,
            'group_guid': m.group_guid,
            'group_name': group.name if group else None,
            'status': m.status,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        })

    return jsonify(result), 200


@groups_bp.route('/admin/decide', methods=['POST'])
@require_auth
@require_group_admin
def admin_decide():
    """POST /api/groups/admin/decide — approve or reject pending membership."""
    session = get_db()
    user = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    membership_guid = data.get('membership_guid', '').strip()
    decision = data.get('decision', '').strip().lower()

    if not membership_guid or decision not in ('approved', 'rejected'):
        return jsonify({"error": "invalid_request",
                        "message": "membership_guid and decision (approved/rejected) required"}), 400

    from src.models.membership import Membership
    membership = session.query(Membership).filter_by(guid=membership_guid).first()
    if membership is None:
        return jsonify({"error": "not_found", "message": "Membership not found"}), 404

    if membership.status != 'pending':
        return jsonify({"error": "conflict",
                        "message": f"Membership already decided (status: {membership.status})"}), 409

    # Verify admin has authority over this group (SU can decide any)
    if not user.is_su_admin:
        admin_m = session.query(Membership).filter_by(
            user_guid=user.guid, group_guid=membership.group_guid,
            status='approved', is_admin=True
        ).first()
        if admin_m is None:
            return jsonify({"error": "forbidden",
                            "message": "Not admin of this group"}), 403

    membership.status = decision
    membership.decided_by_guid = user.guid

    audit('membership_decide', user_guid=user.guid,
          detail={'membership_guid': membership_guid, 'decision': decision,
                  'target_user_guid': membership.user_guid,
                  'group_guid': membership.group_guid},
          ip=request.remote_addr)

    return jsonify({
        "membership_guid": membership.guid,
        "status": membership.status,
        "decided_by": user.guid,
    }), 200


@groups_bp.route('/admin/invite', methods=['POST'])
@require_auth
@require_group_admin
def admin_invite():
    """POST /api/groups/admin/invite — create time-limited invite token."""
    session = get_db()
    user = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    group_guid = data.get('group_guid', '').strip()
    hours_valid = int(data.get('hours_valid', 48))

    if not group_guid:
        return jsonify({"error": "invalid_request", "message": "group_guid required"}), 400

    from src.models.group import Group
    group = session.query(Group).filter_by(guid=group_guid).first()
    if group is None:
        return jsonify({"error": "not_found", "message": "Group not found"}), 404

    # Verify admin authority
    if not user.is_su_admin:
        from src.models.membership import Membership
        admin_m = session.query(Membership).filter_by(
            user_guid=user.guid, group_guid=group_guid,
            status='approved', is_admin=True
        ).first()
        if admin_m is None:
            return jsonify({"error": "forbidden", "message": "Not admin of this group"}), 403

    from src.models.invite import Invite
    invite_token = str(uuid.uuid4())
    invite = Invite(
        group_guid=group_guid,
        token=invite_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours_valid),
        created_by_guid=user.guid,
    )
    session.add(invite)
    session.flush()

    audit('invite_created', user_guid=user.guid,
          detail={'group_guid': group_guid, 'group_name': group.name,
                  'hours_valid': hours_valid},
          ip=request.remote_addr)

    return jsonify({
        "invite_guid": invite.guid,
        "token": invite_token,
        "group_guid": group_guid,
        "expires_at": invite.expires_at.isoformat(),
    }), 201


@groups_bp.route('/join-by-invite', methods=['POST'])
@require_auth
@require_professional
def join_by_invite():
    """POST /api/groups/join-by-invite — redeem invite token → pending membership."""
    session = get_db()
    user = g.current_user

    data = request.get_json() if request.is_json else request.form.to_dict()
    invite_token = data.get('token', '').strip()

    if not invite_token:
        return jsonify({"error": "invalid_request", "message": "token required"}), 400

    from src.models.invite import Invite
    invite = session.query(Invite).filter_by(token=invite_token).first()
    if invite is None:
        return jsonify({"error": "not_found", "message": "Invalid invite token"}), 404

    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return jsonify({"error": "expired", "message": "Invite token has expired"}), 410

    from src.models.membership import Membership
    existing = session.query(Membership).filter_by(
        user_guid=user.guid, group_guid=invite.group_guid
    ).first()
    if existing:
        return jsonify({"error": "conflict",
                        "message": f"Membership already exists (status: {existing.status})"}), 409

    membership = Membership(
        user_guid=user.guid,
        group_guid=invite.group_guid,
        status='pending',
        is_admin=False,
    )
    session.add(membership)
    session.flush()

    audit('join_by_invite', user_guid=user.guid,
          detail={'group_guid': invite.group_guid, 'invite_guid': invite.guid},
          ip=request.remote_addr)

    return jsonify({
        "membership_guid": membership.guid,
        "group_guid": invite.group_guid,
        "status": "pending",
    }), 201
