# Admin Manual

Operations guide for SU (Super User) administrators and group administrators.

## Roles Overview

| Role | Scope | Key Actions |
|------|-------|-------------|
| **SU Admin** | System-wide | All admin operations, user management, org management |
| **Group Admin** | Per-group | Membership approvals, invites for own groups |

## SU Admin Operations

### Accessing the Admin Panel

1. Log in at `/login` with an SU admin account
2. Navigate to the dashboard — the **SU Admin** section is visible only to SU admins
3. Or go directly to `/su-admin`

### User Management

#### View All Users

The user table shows all registered users with:

- Email, user type (patient/professional), SU status
- Professional details: name, role (doctor/nurse/other)
- Group memberships and admin status
- Organisation affiliations

**API:** `GET /api/admin/users`

#### Promote to SU Admin

Elevates a professional to system-wide admin. Requires your password for confirmation.

1. Click **Promote** next to the target user
2. Enter your password
3. Confirm

**API:** `POST /api/admin/promote-su` with `{user_guid, password}`

!!! warning
    Only professionals can be SU admins. This action cannot be undone via the UI — demote by directly updating the database.

#### Delete User

Removes a user and their associated data. The system:

- Nullifies all `decided_by_guid` references (preserving decision history)
- Deletes all memberships
- Cascades to patient/professional records

**API:** `DELETE /api/admin/users/<user_guid>`

!!! warning
    You cannot delete yourself. User deletion is irreversible.

#### CSV Export

Downloads all users as a CSV file with columns: `user_guid`, `email`, `user_type`, `is_su_admin`, `first_name`, `last_name`, `professional_role`, `created_at`.

**API:** `GET /api/admin/export-users`

#### CSV Import

Upload a CSV file to bulk-create users. Requirements:

- CSV must have headers matching the export format
- Existing emails are skipped (not overwritten)
- New users get temporary password `changeme01`
- Users should change their password on first login

**API:** `POST /api/admin/import-users` (multipart form, `file` field)

---

### Organisation Management

Organisations are the **single source of truth** across all PDHC services.

#### View Organisations

Lists all registered organisations with GUID and creation date.

**API:** `GET /api/admin/organisations`

#### Create Organisation

Add a new organisation. Name must be unique.

**API:** `POST /api/admin/organisations` with `{name}`

!!! note
    Downstream services pull organisation lists from `GET /api/public/organisations`. New organisations are immediately available system-wide.

---

### Group Lifecycle

#### Group Proposals

Professionals can suggest new groups via the UI. Proposals appear in the admin panel.

**Workflow:**

1. Professional submits group proposal (name + type)
2. SU reviews proposal in admin panel
3. **Approve** — creates the group immediately
4. **Reject** — proposal archived

**API:** `GET /api/admin/group-proposals` and `POST /api/admin/group-proposals` with `{proposal_guid, decision}`

Group types: `planning`, `request`, `provider`, `analysis`

#### Delete Group

Removes a group and all associated memberships and invites.

**API:** `DELETE /api/admin/groups/<group_guid>`

#### Assign Group Admin

Set any existing group member as an admin of that group.

**API:** `POST /api/admin/assign-group-admin` with `{user_guid, group_guid}`

---

### Leader Requests

Professionals can request to become group admins. These requests appear in the SU admin panel.

**Workflow:**

1. Professional requests admin role for a specific group
2. SU reviews in admin panel
3. **Approve** — sets `is_admin=True` on their membership
4. **Reject** — request archived

**API:** `GET /api/admin/leader-requests` and `POST /api/admin/leader-requests` with `{leader_request_guid, decision}`

---

### Access Request Workflow

New professionals request access through the public onboarding form. The workflow has three stages:

```
pending → endorsed → approved (creates account)
              ↘ rejected
```

1. **Pending** — new request submitted. SU can endorse or reject.
2. **Endorsed** — leader endorsement recorded. SU can approve or reject.
3. **Approved** — system creates:
   - User account (professional type)
   - Professional record (with role, name)
   - Organisation link
   - Memberships for all requested phases (auto-approved)

**API:** `GET /api/admin/access-requests` and `POST /api/admin/access-requests` with `{access_request_guid, decision}`

`decision` values: `endorsed`, `approved`, `rejected`

---

### Service Registry (Oath Overview)

The `oath_overview.csv` tracks all services under SSO management.

**View:** `GET /api/admin/oath-overview`

**Update:** `PUT /api/admin/oath-overview` — send the full CSV as a JSON array of row objects.

Fields: `service_name`, `service_url`, `api_health_url`, `capability_statement_url`, `endpoints_url`, `privilege_level`, `notes`

---

## Group Admin Operations

### Accessing the Group Admin Panel

1. Log in with a professional account that has `is_admin=True` in at least one group
2. Navigate to `/group-admin`

### Pending Membership Requests

View all pending membership requests for groups you administer.

Each request shows: applicant email, group name, submission date.

**Actions:**

- **Approve** — member gains access to the group
- **Reject** — membership denied

**API:** `GET /api/groups/admin/pending` and `POST /api/groups/admin/decide` with `{membership_guid, decision}`

### Creating Invite Links

Generate time-limited invite tokens for a group:

1. Select the group
2. Set validity period (default 48 hours)
3. Share the generated token/link with the invitee

The invitee redeems the token at `/join` or via `POST /api/groups/join-by-invite`.

**API:** `POST /api/groups/admin/invite` with `{group_guid, hours_valid}`

!!! note
    Invite tokens create **pending** memberships. The group admin must still approve the membership after the invite is redeemed.

---

## Audit Trail

All admin actions are logged to structured audit files in `LOG_DIR`:

- Login attempts (success/fail)
- User creation, deletion, promotion
- Group creation, deletion
- Membership decisions
- Access request decisions
- Organisation changes
- Oath overview updates

Logs include: timestamp, action type, actor GUID, target GUID, IP address, and action-specific details.
