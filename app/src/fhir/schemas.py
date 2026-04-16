"""FHIR R5 schema helpers — maps internal models to FHIR resource shapes."""


def patient_to_fhir(patient, user):
    """Convert internal Patient + User to FHIR Patient resource shape."""
    return {
        "resourceType": "Patient",
        "id": patient.guid,
        "identifier": [
            {
                "system": "urn:oid:1.2.752.129.2.1.3.1",
                "value": patient.personnummer,
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "text": user.email,
            }
        ],
        "managingOrganization": {
            "reference": f"Organization/{patient.organisation_guid}",
        },
    }


def practitioner_to_fhir(professional, user):
    """Convert internal Professional + User to FHIR Practitioner resource shape."""
    return {
        "resourceType": "Practitioner",
        "id": professional.guid,
        "active": True,
        "name": [
            {
                "use": "official",
                "family": professional.last_name or "",
                "given": [professional.first_name or ""],
            }
        ],
        "qualification": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "urn:pdhc:professional-role",
                            "code": professional.professional_role,
                            "display": professional.professional_role.title(),
                        }
                    ]
                }
            }
        ],
    }


def organization_to_fhir(organisation):
    """Convert internal Organisation to FHIR Organization resource shape."""
    return {
        "resourceType": "Organization",
        "id": organisation.guid,
        "active": True,
        "name": organisation.name,
    }


def group_to_fhir(group):
    """Convert internal Group to FHIR Group resource shape."""
    return {
        "resourceType": "Group",
        "id": group.guid,
        "active": True,
        "type": "person",
        "membership": "definitional",
        "name": group.name,
        "code": {
            "coding": [
                {
                    "system": "urn:pdhc:group-category",
                    "code": group.category,
                    "display": group.category.title(),
                }
            ]
        },
    }
