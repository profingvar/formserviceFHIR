"""FHIR R5 CapabilityStatement for the SSO service.

GET /fhir/metadata returns a valid CapabilityStatement describing
all supported FHIR interactions.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify

fhir_bp = Blueprint('fhir', __name__, url_prefix='/fhir')


def _build_capability_statement():
    """Build the CapabilityStatement resource dict."""
    return {
        "resourceType": "CapabilityStatement",
        "id": "formservicefhir-sso",
        "url": "https://sso.pdhc.se/fhir/metadata",
        "version": "1.0.0",
        "name": "FormServiceFHIR_SSO",
        "title": "formserviceFHIR SSO Capability Statement",
        "status": "active",
        "experimental": False,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "publisher": "PDHC",
        "description": (
            "Central SSO/OAuth server. Issues JWT tokens, manages users "
            "(patients & professionals), groups, memberships, organisations. "
            "Delivers an access blob to downstream FHIR-compliant microservices."
        ),
        "kind": "instance",
        "fhirVersion": "5.0.0",
        "format": ["json"],
        "software": {
            "name": "formserviceFHIR",
            "version": "1.0.0",
        },
        "implementation": {
            "description": "formserviceFHIR SSO Service",
            "url": "https://sso.pdhc.se",
        },
        "rest": [
            {
                "mode": "server",
                "security": {
                    "service": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                                    "code": "OAuth",
                                    "display": "OAuth",
                                }
                            ],
                            "text": "JWT Bearer token via OAuth-style login endpoint",
                        }
                    ],
                    "description": (
                        "Authentication via POST /api/auth/login returns a JWT. "
                        "Bearer token required for protected endpoints. "
                        "Service-to-service auth uses X-SSO-Client-Id/Secret headers."
                    ),
                },
                "resource": [
                    {
                        "type": "Patient",
                        "profile": "http://hl7.org/fhir/StructureDefinition/Patient",
                        "interaction": [
                            {"code": "read"},
                            {"code": "create"},
                        ],
                        "searchParam": [
                            {"name": "identifier", "type": "token",
                             "documentation": "Search by personnummer"},
                        ],
                    },
                    {
                        "type": "Practitioner",
                        "profile": "http://hl7.org/fhir/StructureDefinition/Practitioner",
                        "interaction": [
                            {"code": "read"},
                            {"code": "create"},
                        ],
                    },
                    {
                        "type": "Organization",
                        "profile": "http://hl7.org/fhir/StructureDefinition/Organization",
                        "interaction": [
                            {"code": "read"},
                            {"code": "create"},
                            {"code": "search-type"},
                        ],
                    },
                    {
                        "type": "Group",
                        "profile": "http://hl7.org/fhir/StructureDefinition/Group",
                        "interaction": [
                            {"code": "read"},
                            {"code": "create"},
                            {"code": "search-type"},
                        ],
                    },
                ],
                "operation": [
                    {
                        "name": "login",
                        "definition": "POST /api/auth/login — authenticate and receive JWT",
                    },
                    {
                        "name": "me",
                        "definition": "GET /api/auth/me — retrieve access blob",
                    },
                    {
                        "name": "me-service",
                        "definition": "GET /api/auth/me/service — service-to-service access blob",
                    },
                    {
                        "name": "logout",
                        "definition": "POST /api/auth/logout — revoke token",
                    },
                ],
            }
        ],
    }


@fhir_bp.route('/metadata', methods=['GET'])
def capability_statement():
    """GET /fhir/metadata — FHIR R5 CapabilityStatement."""
    cs = _build_capability_statement()
    response = jsonify(cs)
    response.headers['Content-Type'] = 'application/fhir+json'
    return response, 200
