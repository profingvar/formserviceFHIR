# Architecture Overview

## System Context

```mermaid
graph TB
    subgraph External
        Browser[Browser / Mobile]
        DS1[Downstream Service A]
        DS2[Downstream Service B]
    end

    subgraph SSO Service
        App[Flask App :9000]
        DB[(PostgreSQL :9003)]
        Logs[Audit Logs]
    end

    subgraph Infrastructure
        RP[nginx Reverse Proxy]
        DNS[sso.pdhc.se]
    end

    Browser -->|HTTPS| DNS
    DNS --> RP
    RP -->|:9000| App
    App --> DB
    App --> Logs

    DS1 -->|/api/auth/me/service| App
    DS2 -->|/api/auth/me/service| App
    Browser -->|Bearer JWT| DS1
    Browser -->|Bearer JWT| DS2
```

## Data Model

All tables use integer primary keys internally and UUID4 GUIDs for external references (Rule 18).

```mermaid
erDiagram
    User ||--o| Patient : "has"
    User ||--o| Professional : "has"
    User ||--o{ UserPhase : "direct phase grants"
    User }o--o{ Organisation : "UserOrganisation"
    User }o--o{ Group : "Membership"
    Group ||--o{ Membership : "has"
    Group ||--o{ Invite : "has"
    User ||--o{ GroupProposal : "requests"
    User ||--o{ LeaderRequest : "requests"
    AccessRequest ||--o| User : "creates on approve"

    User {
        int id PK
        uuid guid UK
        string email UK
        string password_hash
        enum user_type "patient|professional"
        bool is_su_admin
        bool force_change_on_next_login "#43"
        datetime token_revocation_epoch "#44 nullable"
        datetime created_at
    }

    UserPhase {
        int id PK
        uuid guid UK
        uuid user_guid FK "#46 direct phase grant"
        enum phase "planning|request|provider|analysis"
        uuid granted_by_guid
        datetime granted_at
    }

    Patient {
        int id PK
        uuid guid UK
        int user_id FK
        string personnummer "12 digits"
        uuid organisation_guid FK
        bool in_registry
        json registries
    }

    Professional {
        int id PK
        uuid guid UK
        int user_id FK
        enum professional_role "doctor|nurse|other"
        string first_name
        string last_name
    }

    Organisation {
        int id PK
        uuid guid UK
        string name UK
        datetime created_at
    }

    UserOrganisation {
        int id PK
        uuid user_guid FK
        uuid organisation_guid FK
    }

    Group {
        int id PK
        uuid guid UK
        string name
        string category "free-form category label (#60) — does NOT confer phase access after #57"
        datetime created_at
    }

    Membership {
        int id PK
        uuid guid UK
        uuid user_guid FK
        uuid group_guid FK
        enum status "pending|approved|rejected"
        bool is_admin
        uuid decided_by_guid
        datetime created_at
    }

    GroupProposal {
        int id PK
        uuid guid UK
        string proposed_name
        string category
        uuid requested_by_guid FK
        enum status "pending|approved|rejected"
        uuid decided_by_guid
    }

    LeaderRequest {
        int id PK
        uuid guid UK
        uuid user_guid FK
        uuid group_guid FK
        enum status "pending|approved|rejected"
        uuid decided_by_guid
    }

    AccessRequest {
        int id PK
        uuid guid UK
        string email
        string password_hash
        string first_name
        string last_name
        enum professional_role
        uuid organisation_guid FK
        json requested_phases
        uuid chosen_leader_guid FK
        enum status "pending|endorsed|approved|rejected"
        uuid decided_by_guid
    }

    Invite {
        int id PK
        uuid guid UK
        uuid group_guid FK
        string token UK
        datetime expires_at
        uuid created_by_guid FK
    }

    RevokedToken {
        int id PK
        string token_guid UK
        datetime expires_at
    }
```

### FHIR Resource Mapping

| Table | FHIR Resource Type |
|-------|-------------------|
| Patient | Patient |
| Professional | Practitioner |
| Organisation | Organization |
| Group | Group |

## Authentication Flow

### Standard Login

```mermaid
sequenceDiagram
    participant C as Client
    participant S as SSO Service
    participant DB as Database

    C->>S: POST /api/auth/login {email, password}
    S->>DB: Query user by email
    DB-->>S: User record
    S->>S: bcrypt.checkpw(password, hash)
    S->>S: issue_token(user.guid, secret)
    S-->>C: {token, user_guid}
    Note over C: Store JWT for subsequent requests
    C->>S: GET /api/auth/me (Bearer token)
    S->>S: decode_token + check revoked
    S->>DB: Build access blob
    S-->>C: Access blob (user, orgs, groups, phases)
```

### SSO Handshake (H1–H4)

Used by downstream services to authenticate users through the central SSO.

```mermaid
sequenceDiagram
    participant U as User Browser
    participant DS as Downstream Service
    participant SSO as SSO Service

    U->>DS: Access protected resource
    DS->>U: H1: Redirect to SSO /login?next=callback&state=xyz
    U->>SSO: H2: Login form (or auto-redirect if session exists)
    SSO->>SSO: Authenticate user, issue JWT
    SSO->>U: H3: Redirect to callback?token=JWT&state=xyz
    U->>DS: H4: Arrive at callback with token
    DS->>SSO: GET /api/auth/me/service (Bearer + client creds)
    SSO-->>DS: Access blob
    DS->>U: Render protected resource
```

**Security controls:**

- `next` URL validated against `ALLOWED_CALLBACK_URLS` allowlist
- `state` parameter passed through for CSRF protection
- Auto-redirect skips login form if user has valid session
- Service-to-service calls require `X-SSO-Client-Id` and `X-SSO-Client-Secret` headers

### Forced Password Reset (#43)

```mermaid
sequenceDiagram
    participant SU as SU Admin
    participant SSO as SSO Service
    participant DS as Downstream Service
    participant U as User Browser

    SU->>SSO: POST /api/admin/users/<guid>/reset-password
    SSO->>SSO: user.force_change_on_next_login = True
    SSO-->>SU: 200 OK (+ temp password)

    U->>DS: GET /protected (existing Bearer)
    DS->>SSO: GET /api/auth/me/service
    SSO-->>DS: blob { must_change_password: true, ... }
    DS->>U: 302/403 → SSO /change-password

    U->>SSO: POST /api/auth/change-password (new pw)
    SSO->>SSO: user.force_change_on_next_login = False
    SSO-->>U: 200 OK
    Note over U,DS: Next /me/service call returns must_change_password=false → user unblocked
```

### Bulk Session Flush (#44)

```mermaid
sequenceDiagram
    participant SU as SU Admin
    participant SSO as SSO Service
    participant DS as Downstream Service
    participant U as User Browser

    SU->>SSO: POST /api/admin/users/<guid>/flush-sessions
    SSO->>SSO: user.token_revocation_epoch = now()
    SSO-->>SU: 200 OK

    U->>DS: GET /protected (existing Bearer, iat < epoch)
    DS->>SSO: GET /api/auth/me/service
    SSO->>SSO: token_iat_dt < user.token_revocation_epoch → 401
    SSO-->>DS: 401 Unauthorized
    DS->>DS: Clear local session
    DS->>U: Redirect to SSO /login
```

Cheaper than inserting N revoked-token rows when the set of active `jti`s is unknown (e.g. after a credential compromise across multiple devices).

## Access Blob Schema

The access blob is the core data structure returned by `/api/auth/me`. Downstream services use it to make authorization decisions.

### Patient Access Blob

```json
{
  "user_guid": "a1b2c3d4-...",
  "email": "patient@example.com",
  "user_type": "patient",
  "is_su_admin": false,
  "must_change_password": false,
  "patient_guid": "e5f6g7h8-...",
  "organisation_guid": "i9j0k1l2-...",
  "in_registry": true,
  "registries": ["INCA"],
  "fhir_resource_type": "Patient"
}
```

### Professional Access Blob

```json
{
  "user_guid": "m3n4o5p6-...",
  "email": "doctor@hospital.se",
  "user_type": "professional",
  "is_su_admin": false,
  "must_change_password": false,
  "professional_guid": "q7r8s9t0-...",
  "professional_role": "doctor",
  "fhir_resource_type": "Practitioner",
  "organization_ids": ["i9j0k1l2-..."],
  "groups": [
    {
      "group_guid": "u1v2w3x4-...",
      "group_name": "Oncology Planning",
      "category": "planning",
      "status": "approved",
      "is_admin": false
    }
  ],
  "effective_phases": ["planning", "analysis"]
}
```

`effective_phases` is sourced **exclusively** from direct `UserPhase` grants (#46 + #57), populated by SU via `POST /api/admin/users/<guid>/phases`.

**Groups and phases are orthogonal access criteria (#57).** `Group.category` (renamed from `group_type` in #60) is a free-form organisational label — approved membership in a group with `category = "planning"` does **not** confer the `planning` phase. Each downstream service composes its own access policy from independent inputs (membership, phase, org scope); the SSO merely supplies the raw facts.

Downstream services should continue to check `phase in blob["effective_phases"]` — the field name and shape are unchanged; only the source of truth narrowed.

## Decision Tree

Downstream services use the access blob to authorize actions:

```mermaid
flowchart TD
    Start[Incoming Request] --> CheckToken{Valid JWT?}
    CheckToken -->|No| Deny[401 Unauthorized]
    CheckToken -->|Yes| GetBlob[GET /api/auth/me]
    GetBlob --> CheckType{user_type?}

    CheckType -->|patient| PatientFlow
    CheckType -->|professional| ProfFlow

    subgraph PatientFlow[Patient Authorization]
        P1{Owns resource?} -->|No| Deny2[403 Forbidden]
        P1 -->|Yes| P2{Action requires registry?}
        P2 -->|No| Allow1[Allow]
        P2 -->|Yes| P3{in_registry?}
        P3 -->|Yes| Allow2[Allow]
        P3 -->|No| Deny3[403 Not in registry]
    end

    subgraph ProfFlow[Professional Authorization]
        R1{is_su_admin?} -->|Yes| AllowAll[Allow all]
        R1 -->|No| R2{Action phase?}
        R2 --> R3{phase in effective_phases?}
        R3 -->|No| Deny4[403 No phase access]
        R3 -->|Yes| R4{Org scope OK?}
        R4 -->|No| Deny5[403 Wrong org]
        R4 -->|Yes| R5{Group admin required?}
        R5 -->|No| Allow3[Allow]
        R5 -->|Yes| R6{is_admin in group?}
        R6 -->|Yes| Allow4[Allow]
        R6 -->|No| Deny6[403 Not group admin]
    end
```

## Middleware Stack

Each request passes through these layers in order:

1. **CORS** — validates `Origin` header against `ALLOWED_ORIGINS`
2. **Rate Limiter** — in-memory per-IP limits (configurable per endpoint)
3. **CSRF** — Flask-WTF token validation on form POST (API routes exempt)
4. **Auth Middleware** — JWT decode, `jti` revocation check, `iat < user.token_revocation_epoch` check (#44), user loading into `g.current_user`
5. **Route Handler** — blueprint endpoint logic
6. **Audit Logger** — structured log entry for sensitive operations

## Port Allocation

| Port | Service |
|------|---------|
| 9000 | Flask application (Gunicorn) |
| 9003 | PostgreSQL database |
