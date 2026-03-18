# Integration Guide

How to connect a downstream service to the formserviceFHIR SSO.

## Overview

Downstream services authenticate users through the SSO service. The flow is:

1. User arrives at your service without a valid session
2. Your service redirects to SSO for login (SSO handshake)
3. SSO authenticates and redirects back with a JWT
4. Your service validates the JWT via `/api/auth/me/service`
5. Your service uses the **access blob** to make authorization decisions

## Step 1: Register Your Service

Before integrating, register your service with the SSO administrator:

1. Request service credentials (`X-SSO-Client-Id` / `X-SSO-Client-Secret`)
2. Provide your callback URL(s) to be added to `ALLOWED_CALLBACK_URLS`
3. Provide your origin(s) to be added to `ALLOWED_ORIGINS`
4. Your service will be added to `oath_overview.csv`

The SSO admin configures these in the `.env` file:

```bash
SSO_CLIENT_ID_YOURSERVICE=your-client-id
SSO_CLIENT_SECRET_YOURSERVICE=your-client-secret
ALLOWED_CALLBACK_URLS=...,https://yourservice.pdhc.se/callback
ALLOWED_ORIGINS=...,https://yourservice.pdhc.se
```

## Step 2: Implement the SSO Handshake

### H1 — Redirect to SSO

When a user hits a protected route without a valid session, redirect them:

```
https://sso.pdhc.se/login?next=https://yourservice.pdhc.se/callback&state=RANDOM_STRING
```

- `next` — your callback URL (must be in allowlist)
- `state` — random CSRF token you generate and store in session

### H2 — User Authenticates

The SSO login page handles authentication. If the user already has a valid SSO session, they are auto-redirected without seeing the login form.

### H3 — SSO Redirects Back

On success, SSO redirects to:

```
https://yourservice.pdhc.se/callback?token=JWT_TOKEN&state=RANDOM_STRING
```

On failure:

```
https://yourservice.pdhc.se/callback?error=authentication_failed&error_description=...&state=RANDOM_STRING
```

### H4 — Validate Token

At your callback endpoint:

1. Verify `state` matches what you stored
2. Extract the `token` parameter
3. Call `/api/auth/me/service` to validate and get the access blob

```python
import requests

def sso_callback(token, state):
    # Verify state matches session
    if state != session.get('sso_state'):
        abort(403, "CSRF state mismatch")

    # Validate token with SSO
    resp = requests.get(
        "https://sso.pdhc.se/api/auth/me/service",
        headers={
            "Authorization": f"Bearer {token}",
            "X-SSO-Client-Id": "your-client-id",
            "X-SSO-Client-Secret": "your-client-secret",
        },
    )

    if resp.status_code != 200:
        abort(401, "Token validation failed")

    access_blob = resp.json()
    # Store in session and proceed
    session['user'] = access_blob
```

## Step 3: Use the Access Blob

The access blob contains everything needed for authorization decisions.

### Patient Flow

```python
def authorize_patient_action(blob, resource_owner_guid, requires_registry=False):
    """Authorize a patient action."""
    if blob['user_type'] != 'patient':
        return False, "Not a patient"

    # Ownership check
    if blob['patient_guid'] != resource_owner_guid:
        return False, "Not the resource owner"

    # Registry check
    if requires_registry and not blob.get('in_registry', False):
        return False, "Not enrolled in registry"

    return True, "Authorized"
```

### Professional Flow

```python
def authorize_professional_action(blob, required_phase=None, require_admin=False, group_guid=None):
    """Authorize a professional action."""
    if blob['user_type'] != 'professional':
        return False, "Not a professional"

    # SU admins bypass all checks
    if blob.get('is_su_admin'):
        return True, "SU admin"

    # Phase check
    if required_phase and required_phase not in blob.get('effective_phases', []):
        return False, f"No access to phase: {required_phase}"

    # Group admin check
    if require_admin and group_guid:
        for group in blob.get('groups', []):
            if group['group_guid'] == group_guid and group['is_admin']:
                return True, "Group admin"
        return False, "Not group admin"

    return True, "Authorized"
```

### `map_action_to_phase()` Reference

Map your service's actions to SSO group types (phases):

```python
ACTION_PHASE_MAP = {
    "view_treatment_plan": "planning",
    "create_treatment_plan": "planning",
    "submit_data_request": "request",
    "view_provider_network": "provider",
    "run_analysis": "analysis",
    "view_analysis_results": "analysis",
}

def map_action_to_phase(action):
    """Map a service action to its required SSO phase."""
    return ACTION_PHASE_MAP.get(action)
```

## Organisation as Single Source of Truth

The SSO service maintains the canonical list of organisations. All services should use:

```
GET https://sso.pdhc.se/api/public/organisations
```

This is a public, rate-limited endpoint. Use it to populate dropdowns, validate organisation references, and sync your local organisation data.

Do **not** maintain a separate organisation registry. Always defer to the SSO.

## Service Registry (`oath_overview.csv`)

The `oath_overview.csv` file tracks all services under the SSO umbrella:

| Field | Description |
|-------|-------------|
| `service_name` | Human-readable service name |
| `service_url` | Base URL of the service |
| `api_health_url` | Health check endpoint |
| `capability_statement_url` | FHIR CapabilityStatement URL |
| `endpoints_url` | Endpoint documentation URL |
| `privilege_level` | `public`, `authenticated`, `admin` |
| `notes` | Free-text notes |

SU admins manage this via `GET/PUT /api/admin/oath-overview`.

## Error Handling

Handle these SSO error scenarios in your service:

| Scenario | SSO Response | Your Action |
|----------|-------------|-------------|
| Token expired | `401` from `/me/service` | Redirect to SSO login |
| Token revoked | `401` from `/me/service` | Redirect to SSO login |
| Invalid service creds | `403` from `/me/service` | Log error, return 500 |
| SSO unreachable | Connection error | Return 503, retry with backoff |
| User lacks phase | `effective_phases` missing phase | Return 403 to user |

## Adding a New Service: Checklist

1. Request service credentials from SU admin
2. Get callback URL added to SSO allowlist
3. Implement SSO handshake (H1–H4)
4. Implement token validation via `/api/auth/me/service`
5. Map your actions to phases using `map_action_to_phase()`
6. Use the access blob for all authorization decisions
7. Use `/api/public/organisations` for organisation data
8. Register in `oath_overview.csv` via SU admin
9. Test: login flow, token validation, authorization, token expiry handling
