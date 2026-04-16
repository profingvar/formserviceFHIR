"""Phase 8 tests — Public / Catalog API: organisations, groups, leaders, access-request."""
import uuid

import pytest

from src.app import create_app
from src.db import get_session
from src.services.auth_service import hash_password
from src.models.user import User
from src.models.professional import Professional
from src.models.organisation import Organisation
from src.models.group import Group
from src.models.membership import Membership


SECRET = 'test-secret-key-not-for-production'


@pytest.fixture
def app():
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
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_data(app):
    """Seed: org, group, SU admin (leader), regular professional."""
    with app.app_context():
        session = get_session()

        org = Organisation(guid=str(uuid.uuid4()), name='Test Hospital')
        org2 = Organisation(guid=str(uuid.uuid4()), name='Research Center')
        session.add_all([org, org2])
        session.flush()

        group = Group(guid=str(uuid.uuid4()), name='Planning Alpha', category='planning')
        group2 = Group(guid=str(uuid.uuid4()), name='Analysis Beta', category='analysis')
        session.add_all([group, group2])
        session.flush()

        # SU admin (is a leader)
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

        # Group admin (also a leader)
        admin_user = User(
            guid=str(uuid.uuid4()), email='admin@test.com',
            password_hash=hash_password('adminpass1'),
            user_type='professional', is_su_admin=False,
        )
        session.add(admin_user)
        session.flush()
        admin_prof = Professional(
            guid=str(uuid.uuid4()), user_id=admin_user.id,
            professional_role='nurse', first_name='Group', last_name='Admin',
        )
        session.add(admin_prof)
        admin_mem = Membership(
            guid=str(uuid.uuid4()), user_guid=admin_user.guid,
            group_guid=group.guid, status='approved', is_admin=True,
        )
        session.add(admin_mem)

        session.commit()

        result = {
            'org_guid': org.guid,
            'org2_guid': org2.guid,
            'group_guid': group.guid,
            'group2_guid': group2.guid,
            'su_guid': su_user.guid,
            'admin_guid': admin_user.guid,
        }
        session.close()
        return result


# --- Public Organisations ---

class TestPublicOrganisations:
    def test_list_organisations_no_auth(self, client, seed_data):
        resp = client.get('/api/public/organisations')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        names = [o['name'] for o in data]
        assert 'Test Hospital' in names
        assert 'Research Center' in names

    def test_list_organisations_has_guids(self, client, seed_data):
        resp = client.get('/api/public/organisations')
        data = resp.get_json()
        assert all('organisation_guid' in o for o in data)


# --- Public Groups ---

class TestPublicGroups:
    def test_list_groups_no_auth(self, client, seed_data):
        resp = client.get('/api/public/groups')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        categories = [g['category'] for g in data]
        assert 'planning' in categories
        assert 'analysis' in categories

    def test_list_groups_has_guids(self, client, seed_data):
        resp = client.get('/api/public/groups')
        data = resp.get_json()
        assert all('group_guid' in g for g in data)


# --- Public Group Leaders ---

class TestPublicGroupLeaders:
    def test_list_leaders_includes_su_and_group_admin(self, client, seed_data):
        resp = client.get('/api/public/group-leaders')
        assert resp.status_code == 200
        data = resp.get_json()
        guids = [l['user_guid'] for l in data]
        assert seed_data['su_guid'] in guids
        assert seed_data['admin_guid'] in guids

    def test_leaders_have_names(self, client, seed_data):
        resp = client.get('/api/public/group-leaders')
        data = resp.get_json()
        for leader in data:
            assert 'first_name' in leader
            assert 'last_name' in leader


# --- Access Request ---

class TestAccessRequest:
    def test_submit_access_request_success(self, client, seed_data):
        resp = client.post('/api/public/access-request', json={
            'email': 'newpro@test.com',
            'password': 'securepass1',
            'first_name': 'New',
            'last_name': 'Professional',
            'professional_role': 'doctor',
            'organisation_guid': seed_data['org_guid'],
            'requested_phases': ['planning'],
            'chosen_leader_guid': seed_data['su_guid'],
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['status'] == 'pending'
        assert 'access_request_guid' in data

    def test_submit_access_request_missing_fields(self, client, seed_data):
        resp = client.post('/api/public/access-request', json={
            'email': 'incomplete@test.com',
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert len(data['messages']) >= 3

    def test_submit_access_request_invalid_role(self, client, seed_data):
        resp = client.post('/api/public/access-request', json={
            'email': 'bad@test.com',
            'password': 'securepass1',
            'first_name': 'Bad',
            'last_name': 'Role',
            'professional_role': 'invalid',
            'organisation_guid': seed_data['org_guid'],
            'requested_phases': ['planning'],
            'chosen_leader_guid': seed_data['su_guid'],
        })
        assert resp.status_code == 400

    def test_submit_access_request_nonexistent_org(self, client, seed_data):
        resp = client.post('/api/public/access-request', json={
            'email': 'newpro2@test.com',
            'password': 'securepass1',
            'first_name': 'New',
            'last_name': 'Pro',
            'professional_role': 'nurse',
            'organisation_guid': str(uuid.uuid4()),
            'requested_phases': [],
            'chosen_leader_guid': seed_data['su_guid'],
        })
        assert resp.status_code == 404

    def test_submit_access_request_duplicate_email(self, client, seed_data):
        resp = client.post('/api/public/access-request', json={
            'email': 'su@test.com',  # Already exists
            'password': 'securepass1',
            'first_name': 'Dup',
            'last_name': 'Email',
            'professional_role': 'other',
            'organisation_guid': seed_data['org_guid'],
            'requested_phases': [],
            'chosen_leader_guid': seed_data['su_guid'],
        })
        assert resp.status_code == 409

    def test_submit_access_request_short_password(self, client, seed_data):
        resp = client.post('/api/public/access-request', json={
            'email': 'short@test.com',
            'password': 'short',
            'first_name': 'Short',
            'last_name': 'Pass',
            'professional_role': 'doctor',
            'organisation_guid': seed_data['org_guid'],
            'requested_phases': [],
            'chosen_leader_guid': seed_data['su_guid'],
        })
        assert resp.status_code == 400
