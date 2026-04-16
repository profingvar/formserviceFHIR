"""Phase 10 tests — FHIR 5 Compliance.

Tests: CapabilityStatement valid FHIR R5, API responses pass FHIR validation,
oath_overview.csv schema correct, FHIR validator catches invalid resources.
"""
import csv
import io
import json
import uuid

import pytest

from src.app import create_app
from src.db import get_session
from src.services.auth_service import hash_password
from src.services.fhir_validator import (
    validate_fhir_resource, validate_capability_statement, FHIRValidationError,
)
from src.fhir.schemas import (
    patient_to_fhir, practitioner_to_fhir, organization_to_fhir, group_to_fhir,
)
from src.models.user import User
from src.models.patient import Patient
from src.models.professional import Professional
from src.models.organisation import Organisation
from src.models.group import Group


SECRET = 'test-secret-key-not-for-production'


@pytest.fixture
def app():
    from src.middleware.rate_limit import reset_rate_limits
    reset_rate_limits()
    application = create_app({
        'TESTING': True,
        'SECRET_KEY': SECRET,
        'WTF_CSRF_ENABLED': False,
        'SESSION_EXPIRY_HOURS': 1,
        'ALLOWED_ORIGINS': ['http://localhost:9000'],
        'ALLOWED_CALLBACK_URLS': ['http://localhost:9000/callback'],
        'SERVICE_CREDENTIALS': {'test-client': 'test-secret'},
    })
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_data(app):
    """Seed org, professional, patient, group."""
    with app.app_context():
        s = get_session()
        org = Organisation(name='FHIR Test Hospital')
        s.add(org)
        s.flush()

        pro_user = User(email='fhirpro@test.com', password_hash=hash_password('password123'),
                        user_type='professional', is_su_admin=False)
        s.add(pro_user)
        s.flush()
        prof = Professional(user_id=pro_user.id, professional_role='doctor',
                            first_name='FHIR', last_name='Doctor')
        s.add(prof)

        pat_user = User(email='fhirpat@test.com', password_hash=hash_password('password123'),
                        user_type='patient', is_su_admin=False)
        s.add(pat_user)
        s.flush()
        patient = Patient(user_id=pat_user.id, personnummer='200001011234',
                          organisation_guid=org.guid)
        s.add(patient)

        grp = Group(name='FHIR Test Group', category='planning')
        s.add(grp)

        s.commit()

        result = {
            'org_guid': org.guid, 'pro_guid': prof.guid,
            'pat_guid': patient.guid, 'grp_guid': grp.guid,
            'pro_user': pro_user, 'pat_user': pat_user,
            'prof': prof, 'patient': patient, 'org': org, 'grp': grp,
        }
        # Copy values before closing session
        ret = {
            'org_guid': org.guid, 'org_name': org.name,
            'pro_guid': prof.guid, 'pro_first': prof.first_name,
            'pro_last': prof.last_name, 'pro_role': prof.professional_role,
            'pat_guid': patient.guid, 'pat_personnummer': patient.personnummer,
            'pat_org_guid': patient.organisation_guid,
            'grp_guid': grp.guid, 'grp_name': grp.name,
            'grp_category': grp.category,
            'pro_email': pro_user.email, 'pat_email': pat_user.email,
        }
        s.close()
        return ret


# ============================================================
# 10.a — CapabilityStatement endpoint
# ============================================================

class TestCapabilityStatement:
    def test_metadata_endpoint_returns_200(self, client, app):
        resp = client.get('/fhir/metadata')
        assert resp.status_code == 200

    def test_metadata_content_type(self, client, app):
        resp = client.get('/fhir/metadata')
        assert 'application/fhir+json' in resp.content_type

    def test_metadata_has_resource_type(self, client, app):
        resp = client.get('/fhir/metadata')
        data = resp.get_json()
        assert data['resourceType'] == 'CapabilityStatement'

    def test_metadata_fhir_version(self, client, app):
        resp = client.get('/fhir/metadata')
        data = resp.get_json()
        assert data['fhirVersion'] == '5.0.0'

    def test_metadata_has_rest_resources(self, client, app):
        resp = client.get('/fhir/metadata')
        data = resp.get_json()
        rest = data['rest']
        assert len(rest) == 1
        resources = rest[0]['resource']
        resource_types = [r['type'] for r in resources]
        assert 'Patient' in resource_types
        assert 'Practitioner' in resource_types
        assert 'Organization' in resource_types
        assert 'Group' in resource_types

    def test_metadata_has_security(self, client, app):
        resp = client.get('/fhir/metadata')
        data = resp.get_json()
        security = data['rest'][0]['security']
        assert 'OAuth' in json.dumps(security)

    def test_metadata_validates_as_fhir(self, client, app):
        """CapabilityStatement validates against fhir.resources R5 model."""
        resp = client.get('/fhir/metadata')
        data = resp.get_json()
        resource = validate_capability_statement(data)
        assert resource.get_resource_type() == 'CapabilityStatement'


# ============================================================
# 10.b — FHIR Validator
# ============================================================

class TestFHIRValidator:
    def test_validate_patient_resource(self, app):
        data = _seed_data(app)
        patient_fhir = {
            "resourceType": "Patient",
            "id": data['pat_guid'],
            "identifier": [{"system": "urn:oid:1.2.752.129.2.1.3.1",
                            "value": data['pat_personnummer']}],
            "active": True,
            "name": [{"use": "official", "text": data['pat_email']}],
            "managingOrganization": {"reference": f"Organization/{data['pat_org_guid']}"},
        }
        resource = validate_fhir_resource(patient_fhir)
        assert resource.get_resource_type() == 'Patient'

    def test_validate_practitioner_resource(self, app):
        data = _seed_data(app)
        practitioner_fhir = {
            "resourceType": "Practitioner",
            "id": data['pro_guid'],
            "active": True,
            "name": [{"use": "official", "family": data['pro_last'],
                      "given": [data['pro_first']]}],
        }
        resource = validate_fhir_resource(practitioner_fhir)
        assert resource.get_resource_type() == 'Practitioner'

    def test_validate_organization_resource(self, app):
        data = _seed_data(app)
        org_fhir = {
            "resourceType": "Organization",
            "id": data['org_guid'],
            "active": True,
            "name": data['org_name'],
        }
        resource = validate_fhir_resource(org_fhir)
        assert resource.get_resource_type() == 'Organization'

    def test_validate_group_resource(self, app):
        data = _seed_data(app)
        group_fhir = {
            "resourceType": "Group",
            "id": data['grp_guid'],
            "active": True,
            "type": "person",
            "membership": "definitional",
            "name": data['grp_name'],
        }
        resource = validate_fhir_resource(group_fhir)
        assert resource.get_resource_type() == 'Group'

    def test_validate_missing_resource_type(self):
        with pytest.raises(ValueError, match="Missing 'resourceType'"):
            validate_fhir_resource({})

    def test_validate_unsupported_resource_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            validate_fhir_resource({"resourceType": "MedicationRequest"})

    def test_validate_invalid_resource_raises_error(self):
        """Group requires 'type' and 'membership' fields in R5."""
        with pytest.raises(FHIRValidationError):
            validate_fhir_resource({
                "resourceType": "Group",
                # missing required 'type' and 'membership' fields
            })


# ============================================================
# 10.b — FHIR schema helpers
# ============================================================

class TestFHIRSchemas:
    def test_patient_to_fhir_validates(self, app):
        data = _seed_data(app)
        with app.app_context():
            s = get_session()
            patient = s.query(Patient).first()
            user = s.query(User).filter_by(id=patient.user_id).first()
            fhir_data = patient_to_fhir(patient, user)
            resource = validate_fhir_resource(fhir_data)
            assert resource.get_resource_type() == 'Patient'
            s.close()

    def test_practitioner_to_fhir_validates(self, app):
        data = _seed_data(app)
        with app.app_context():
            s = get_session()
            prof = s.query(Professional).first()
            user = s.query(User).filter_by(id=prof.user_id).first()
            fhir_data = practitioner_to_fhir(prof, user)
            resource = validate_fhir_resource(fhir_data)
            assert resource.get_resource_type() == 'Practitioner'
            s.close()

    def test_organization_to_fhir_validates(self, app):
        data = _seed_data(app)
        with app.app_context():
            s = get_session()
            org = s.query(Organisation).first()
            fhir_data = organization_to_fhir(org)
            resource = validate_fhir_resource(fhir_data)
            assert resource.get_resource_type() == 'Organization'
            s.close()

    def test_group_to_fhir_validates(self, app):
        data = _seed_data(app)
        with app.app_context():
            s = get_session()
            grp = s.query(Group).first()
            fhir_data = group_to_fhir(grp)
            resource = validate_fhir_resource(fhir_data)
            assert resource.get_resource_type() == 'Group'
            s.close()


# ============================================================
# 10.c — oath_overview.csv schema
# ============================================================

class TestOathOverviewSchema:
    def test_oath_overview_csv_exists(self):
        import os
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'oath_overview.csv')
        assert os.path.exists(csv_path)

    def test_oath_overview_csv_has_correct_columns(self):
        import os
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'oath_overview.csv')
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            expected = {
                'service_name', 'service_url', 'api_health_url',
                'capability_statement_url', 'endpoints_url',
                'privilege_level', 'notes',
            }
            assert set(reader.fieldnames) == expected
