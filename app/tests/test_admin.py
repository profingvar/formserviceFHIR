"""Phase 7 tests — SU Admin API: users, promote, delete, groups, proposals, orgs, CSV."""
import io
import uuid

import pytest

from src.app import create_app
from src.db import get_session
from src.services.auth_service import hash_password
from src.models.user import User
from src.models.professional import Professional
from src.models.patient import Patient
from src.models.organisation import Organisation
from src.models.user_organisation import UserOrganisation
from src.models.group import Group
from src.models.membership import Membership
from src.models.group_proposal import GroupProposal
from src.models.leader_request import LeaderRequest
from src.models.access_request import AccessRequest


SECRET = 'test-secret-key-not-for-production'


@pytest.fixture
def app():
    import os
    from src.middleware.rate_limit import reset_rate_limits
    reset_rate_limits()
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': SECRET,
        'WTF_CSRF_ENABLED': False,
        'SESSION_EXPIRY_HOURS': 1,
        'ALLOWED_ORIGINS': [],
        'ALLOWED_CALLBACK_URLS': [],
        'SERVICE_CREDENTIALS': {},
    })
    # Save/restore oath_overview.csv state around admin tests
    oath_path = os.path.join(app.root_path, '..', 'oath_overview.csv')
    _oath_backup = None
    if os.path.exists(oath_path):
        with open(oath_path, 'r') as f:
            _oath_backup = f.read()
        os.remove(oath_path)
    yield app
    # Restore original oath_overview.csv after tests
    if os.path.exists(oath_path):
        os.remove(oath_path)
    if _oath_backup is not None:
        with open(oath_path, 'w') as f:
            f.write(_oath_backup)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_data(app):
    """Seed: org, group, SU admin, regular professional, patient."""
    with app.app_context():
        session = get_session()

        org = Organisation(guid=str(uuid.uuid4()), name='Test Hospital')
        session.add(org)
        session.flush()

        group = Group(guid=str(uuid.uuid4()), name='Planning Alpha', group_type='planning')
        session.add(group)
        session.flush()

        # SU admin
        su_user = User(
            guid=str(uuid.uuid4()), email='su@test.com',
            password_hash=hash_password('supass123'),
            user_type='professional', is_su_admin=True,
        )
        session.add(su_user)
        session.flush()
        su_prof = Professional(
            guid=str(uuid.uuid4()), user_id=su_user.id,
            professional_role='doctor', first_name='SU', last_name='Admin',
        )
        session.add(su_prof)

        # Regular professional with membership
        reg_user = User(
            guid=str(uuid.uuid4()), email='reg@test.com',
            password_hash=hash_password('regpass12'),
            user_type='professional', is_su_admin=False,
        )
        session.add(reg_user)
        session.flush()
        reg_prof = Professional(
            guid=str(uuid.uuid4()), user_id=reg_user.id,
            professional_role='nurse', first_name='Reg', last_name='Pro',
        )
        session.add(reg_prof)
        uo = UserOrganisation(user_guid=reg_user.guid, organisation_guid=org.guid)
        session.add(uo)
        mem = Membership(
            guid=str(uuid.uuid4()), user_guid=reg_user.guid,
            group_guid=group.guid, status='approved', is_admin=False,
        )
        session.add(mem)

        # Patient
        pat_user = User(
            guid=str(uuid.uuid4()), email='patient@test.com',
            password_hash=hash_password('patpass12'),
            user_type='patient', is_su_admin=False,
        )
        session.add(pat_user)
        session.flush()
        patient = Patient(
            guid=str(uuid.uuid4()), user_id=pat_user.id,
            personnummer='199001011234', organisation_guid=org.guid,
        )
        session.add(patient)

        # Group proposal
        proposal = GroupProposal(
            guid=str(uuid.uuid4()), proposed_name='New Research',
            group_type='analysis', requested_by_guid=reg_user.guid,
            status='pending',
        )
        session.add(proposal)

        # Leader request
        lr = LeaderRequest(
            guid=str(uuid.uuid4()), user_guid=reg_user.guid,
            group_guid=group.guid, status='pending',
        )
        session.add(lr)

        # Access request
        ar = AccessRequest(
            guid=str(uuid.uuid4()), email='newpro@test.com',
            password_hash=hash_password('newpass12'),
            first_name='New', last_name='Pro',
            professional_role='doctor', organisation_guid=org.guid,
            requested_phases=['planning'], chosen_leader_guid=su_user.guid,
            status='pending',
        )
        session.add(ar)

        session.commit()

        result = {
            'org_guid': org.guid,
            'group_guid': group.guid,
            'su_guid': su_user.guid,
            'su_email': su_user.email,
            'reg_guid': reg_user.guid,
            'reg_email': reg_user.email,
            'pat_guid': pat_user.guid,
            'pat_email': pat_user.email,
            'proposal_guid': proposal.guid,
            'lr_guid': lr.guid,
            'ar_guid': ar.guid,
            'mem_guid': mem.guid,
        }
        session.close()
        return result


def _auth_header(token):
    return {'Authorization': f'Bearer {token}'}


def _get_token(client, email, password):
    resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    return resp.get_json()['token']


# --- List Users ---

class TestListUsers:
    def test_list_users_su_only(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/users', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 3  # SU, reg, patient
        emails = [u['email'] for u in data]
        assert 'su@test.com' in emails
        assert 'reg@test.com' in emails

    def test_list_users_includes_memberships(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/users', headers=_auth_header(token))
        data = resp.get_json()
        reg = next(u for u in data if u['email'] == 'reg@test.com')
        assert len(reg['memberships']) == 1
        assert reg['memberships'][0]['group_guid'] == seed_data['group_guid']

    def test_list_users_non_su_forbidden(self, client, seed_data):
        token = _get_token(client, 'reg@test.com', 'regpass12')
        resp = client.get('/api/admin/users', headers=_auth_header(token))
        assert resp.status_code == 403


# --- Promote SU ---

class TestPromoteSU:
    def test_promote_su_success(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/promote-su', headers=_auth_header(token),
                           json={'user_guid': seed_data['reg_guid'], 'password': 'supass123'})
        assert resp.status_code == 200
        assert resp.get_json()['is_su_admin'] is True

    def test_promote_su_wrong_password(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/promote-su', headers=_auth_header(token),
                           json={'user_guid': seed_data['reg_guid'], 'password': 'wrong'})
        assert resp.status_code == 401

    def test_promote_su_patient_rejected(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/promote-su', headers=_auth_header(token),
                           json={'user_guid': seed_data['pat_guid'], 'password': 'supass123'})
        assert resp.status_code == 400

    def test_promote_su_already_su(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/promote-su', headers=_auth_header(token),
                           json={'user_guid': seed_data['su_guid'], 'password': 'supass123'})
        assert resp.status_code == 409


# --- Delete User ---

class TestDeleteUser:
    def test_delete_user_success(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.delete(f"/api/admin/users/{seed_data['pat_guid']}",
                             headers=_auth_header(token))
        assert resp.status_code == 200

    def test_delete_user_cannot_delete_self(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.delete(f"/api/admin/users/{seed_data['su_guid']}",
                             headers=_auth_header(token))
        assert resp.status_code == 400

    def test_delete_user_not_found(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.delete(f"/api/admin/users/{str(uuid.uuid4())}",
                             headers=_auth_header(token))
        assert resp.status_code == 404


# --- Delete Group ---

class TestDeleteGroup:
    def test_delete_group_success(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.delete(f"/api/admin/groups/{seed_data['group_guid']}",
                             headers=_auth_header(token))
        assert resp.status_code == 200

    def test_delete_group_not_found(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.delete(f"/api/admin/groups/{str(uuid.uuid4())}",
                             headers=_auth_header(token))
        assert resp.status_code == 404


# --- Assign Group Admin ---

class TestAssignGroupAdmin:
    def test_assign_group_admin(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/assign-group-admin', headers=_auth_header(token),
                           json={'user_guid': seed_data['reg_guid'],
                                 'group_guid': seed_data['group_guid']})
        assert resp.status_code == 200
        assert resp.get_json()['is_admin'] is True

    def test_assign_group_admin_not_member(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/assign-group-admin', headers=_auth_header(token),
                           json={'user_guid': seed_data['su_guid'],
                                 'group_guid': seed_data['group_guid']})
        assert resp.status_code == 404


# --- Group Proposals ---

class TestGroupProposals:
    def test_list_group_proposals(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/group-proposals', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1
        assert data[0]['proposed_name'] == 'New Research'

    def test_approve_group_proposal_creates_group(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/group-proposals', headers=_auth_header(token),
                           json={'proposal_guid': seed_data['proposal_guid'],
                                 'decision': 'approved'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'approved'
        assert data['group_guid'] is not None

    def test_reject_group_proposal(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/group-proposals', headers=_auth_header(token),
                           json={'proposal_guid': seed_data['proposal_guid'],
                                 'decision': 'rejected'})
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'rejected'


# --- Leader Requests ---

class TestLeaderRequests:
    def test_list_leader_requests(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/leader-requests', headers=_auth_header(token))
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1

    def test_approve_leader_request(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/leader-requests', headers=_auth_header(token),
                           json={'leader_request_guid': seed_data['lr_guid'],
                                 'decision': 'approved'})
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'approved'


# --- Access Requests ---

class TestAccessRequests:
    def test_list_access_requests(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/access-requests', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1
        assert data[0]['email'] == 'newpro@test.com'

    def test_approve_access_request_creates_user(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/access-requests', headers=_auth_header(token),
                           json={'access_request_guid': seed_data['ar_guid'],
                                 'decision': 'approved'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'approved'
        assert data['user_guid'] is not None

    def test_reject_access_request(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/access-requests', headers=_auth_header(token),
                           json={'access_request_guid': seed_data['ar_guid'],
                                 'decision': 'rejected'})
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'rejected'


# --- Organisations ---

class TestOrganisations:
    def test_list_organisations(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/organisations', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1
        assert data[0]['resourceType'] == 'Organization'

    def test_create_organisation(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/organisations', headers=_auth_header(token),
                           json={'name': 'New Hospital'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'New Hospital'
        assert data['resourceType'] == 'Organization'

    def test_create_duplicate_organisation(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.post('/api/admin/organisations', headers=_auth_header(token),
                           json={'name': 'Test Hospital'})
        assert resp.status_code == 409


# --- Export/Import ---

class TestExportImport:
    def test_export_users_csv(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/export-users', headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.content_type == 'text/csv; charset=utf-8'
        content = resp.data.decode('utf-8')
        assert 'su@test.com' in content
        assert 'reg@test.com' in content

    def test_import_users_csv(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')

        csv_content = (
            "email,user_type,is_su_admin,first_name,last_name,professional_role\n"
            "imported@test.com,professional,False,Import,User,nurse\n"
        )
        data = {'file': (io.BytesIO(csv_content.encode()), 'users.csv')}
        resp = client.post('/api/admin/import-users', headers=_auth_header(token),
                           data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['created'] == 1

    def test_import_users_skip_existing(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')

        csv_content = (
            "email,user_type,is_su_admin,first_name,last_name,professional_role\n"
            "su@test.com,professional,True,SU,Admin,doctor\n"
        )
        data = {'file': (io.BytesIO(csv_content.encode()), 'users.csv')}
        resp = client.post('/api/admin/import-users', headers=_auth_header(token),
                           data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        assert resp.get_json()['skipped'] == 1


# --- Oath Overview ---

class TestOathOverview:
    def test_oath_overview_read_empty(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')
        resp = client.get('/api/admin/oath-overview', headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_oath_overview_write_and_read(self, client, seed_data):
        token = _get_token(client, 'su@test.com', 'supass123')

        rows = [
            {"service": "auth", "url": "http://localhost:9000", "status": "active"},
            {"service": "fhir", "url": "http://localhost:9001", "status": "planned"},
        ]
        resp = client.put('/api/admin/oath-overview', headers=_auth_header(token),
                          json=rows)
        assert resp.status_code == 200
        assert resp.get_json()['rows'] == 2

        resp2 = client.get('/api/admin/oath-overview', headers=_auth_header(token))
        assert resp2.status_code == 200
        data = resp2.get_json()
        assert len(data) == 2
        assert data[0]['service'] == 'auth'


# --- Non-SU Forbidden ---

class TestNonSUForbidden:
    def test_all_admin_endpoints_require_su(self, client, seed_data):
        token = _get_token(client, 'reg@test.com', 'regpass12')
        h = _auth_header(token)

        endpoints = [
            ('GET', '/api/admin/users'),
            ('POST', '/api/admin/promote-su'),
            ('DELETE', f"/api/admin/users/{seed_data['pat_guid']}"),
            ('DELETE', f"/api/admin/groups/{seed_data['group_guid']}"),
            ('POST', '/api/admin/assign-group-admin'),
            ('GET', '/api/admin/group-proposals'),
            ('POST', '/api/admin/group-proposals'),
            ('GET', '/api/admin/leader-requests'),
            ('POST', '/api/admin/leader-requests'),
            ('GET', '/api/admin/access-requests'),
            ('POST', '/api/admin/access-requests'),
            ('GET', '/api/admin/organisations'),
            ('POST', '/api/admin/organisations'),
            ('GET', '/api/admin/export-users'),
            ('GET', '/api/admin/oath-overview'),
            ('PUT', '/api/admin/oath-overview'),
        ]

        for method, url in endpoints:
            if method == 'GET':
                resp = client.get(url, headers=h)
            elif method == 'POST':
                resp = client.post(url, headers=h, json={})
            elif method == 'PUT':
                resp = client.put(url, headers=h, json=[])
            elif method == 'DELETE':
                resp = client.delete(url, headers=h)
            assert resp.status_code == 403, f"{method} {url} returned {resp.status_code}, expected 403"
