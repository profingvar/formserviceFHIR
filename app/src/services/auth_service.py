"""Auth service — login, password verification, access blob assembly."""
import bcrypt

from src.db import get_db
from src.models.user import User
from src.models.patient import Patient
from src.models.professional import Professional
from src.models.membership import Membership
from src.models.user_organisation import UserOrganisation


def verify_password(plain_password, password_hash):
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        password_hash.encode('utf-8'),
    )


def hash_password(plain_password):
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(
        plain_password.encode('utf-8'),
        bcrypt.gensalt(),
    ).decode('utf-8')


def authenticate_user(email, password, session):
    """Authenticate by email + password. Returns User or None."""
    user = session.query(User).filter_by(email=email).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def build_access_blob(user, session):
    """Build the access blob for /api/auth/me response.

    Returns dict with:
    - user_guid, email, user_type, is_su_admin
    - Patient: patient_guid, organisation_guid, in_registry, registries
    - Professional: professional_guid, professional_role, organization_ids, groups, effective_phases
    """
    blob = {
        'user_guid': user.guid,
        'email': user.email,
        'user_type': user.user_type,
        'is_su_admin': user.is_su_admin,
    }

    if user.user_type == 'patient':
        patient = session.query(Patient).filter_by(user_id=user.id).first()
        if patient:
            blob['patient_guid'] = patient.guid
            blob['organisation_guid'] = patient.organisation_guid
            blob['in_registry'] = patient.in_registry
            blob['registries'] = patient.registries or []
            blob['fhir_resource_type'] = Patient.FHIR_RESOURCE_TYPE

    elif user.user_type == 'professional':
        professional = session.query(Professional).filter_by(user_id=user.id).first()
        if professional:
            blob['professional_guid'] = professional.guid
            blob['professional_role'] = professional.professional_role
            blob['fhir_resource_type'] = Professional.FHIR_RESOURCE_TYPE

        # Organisation IDs (many-to-many)
        user_orgs = session.query(UserOrganisation).filter_by(user_guid=user.guid).all()
        blob['organization_ids'] = [uo.organisation_guid for uo in user_orgs]

        # Groups and effective phases
        memberships = session.query(Membership).filter_by(
            user_guid=user.guid, status='approved'
        ).all()

        groups = []
        effective_phases = set()
        for m in memberships:
            from src.models.group import Group
            group = session.query(Group).filter_by(guid=m.group_guid).first()
            if group:
                groups.append({
                    'group_guid': group.guid,
                    'group_name': group.name,
                    'group_type': group.group_type,
                    'status': m.status,
                    'is_admin': m.is_admin,
                })
                effective_phases.add(group.group_type)

        blob['groups'] = groups
        blob['effective_phases'] = sorted(effective_phases)

    return blob
