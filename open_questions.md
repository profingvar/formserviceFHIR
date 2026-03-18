# Open Questions — CTO Review

Please respond to each question inline (after the → arrow). Delete or modify as you see fit. When done, I will update the plan accordingly.

---

## Q1 — Database port: 9003 or 9020?

Rule 16 says "If practical, use the database on localhost:9020" but also says "Assume ownership of ports 9000–9003 only." Port 9020 is outside that range.

→ Use port: 9003

---

## Q2 — Multi-organisation membership

The access blob in the spec returns `organization_ids: [...]` (plural). A professional can belong to multiple organisations. This requires a `user_organisation` junction table (many-to-many). Currently the plan has no such model.

→ Add user_organisation model? (yes/no): yes

---

## Q3 — Patient → organisation link

Spec says a patient belongs to one organisation responsible for their data. The patient model needs an `organisation_guid` FK.

→ Add organisation_guid to patient model? (yes/no): yes. Also the organisation registry should be single point of truth for the organisations. (And expose and endpoint for other services to consume)

---

## Q4 — Professional role enum

Spec defines subtypes: Läkare (doctor), SSK (nurse), Övrig (other). Should the professional model enforce these as an enum, or keep it as a free-text field?

→ Enum or free-text: enforce and use dropdowns

---

## Q5 — Password hashing library

Login requires verifying against stored hash. Which library?
- **bcrypt** — battle-tested, widely used
- **argon2** — newer, memory-hard, recommended by OWASP

→ Preferred library: bcrypt

---

## Q6 — Tests per phase vs. Phase 11

Rule 4 says don't advance before tests pass. Current plan defers all tests to Phase 11. Proposal: write tests alongside each phase (2–8), keep Phase 11 only for the integration endpoint script.

→ Tests alongside each phase? (yes/no):yes

---

## Q7 — FHIR from the start vs. Phase 10 retrofit

Rule 15 enforces FHIR on DB model, API schema, and validation. Current plan retrofits FHIR in Phase 10. Proposal: bake FHIR resource type annotations into models (Phase 2) and FHIR-shaped API responses into routes (Phase 4–8). Phase 10 becomes only CapabilityStatement + validator.

→ FHIR from start? (yes/no): yes

---

## Q8 — CSRF timing

Phase 9 builds HTML forms. Phase 12 reviews for CSRF. Proposal: implement CSRF protection in Phase 3 (middleware) so it's active before any form is built.

→ CSRF in Phase 3? (yes/no):yes

---

## Q9 — oath_overview.csv management

Spec says SU can view/edit the service registry. Phase 10.d defines the CSV schema. Phase 9.d mentions the UI. But there is no API endpoint for it. Proposal: add `GET/PUT /api/admin/oath-overview` to Phase 7.

→ Add API endpoint for oath_overview? (yes/no): yes accessible only for SU

---

## Q10 — Auto-redirect for existing sessions

Spec says: when a user visits another service and gets sent to SSO login with `next` param, if they already have a valid session, SSO should skip the login form and redirect back immediately with a token.

→ Include auto-redirect logic in Phase 4.a? (yes/no):yes

---

## Q11 — Health endpoint

Docker compose references health-checks but no step implements `GET /api/health`.

→ Add health endpoint to Phase 3? (yes/no): yes

---

## Q12 — Reverse proxy config

Rule 22 warns about fragile server with other services behind a reverse proxy. The plan has no step for producing a safe nginx/caddy config snippet.

→ Add reverse proxy config step to Phase 12? (yes/no): yes. The reverse proxy will be set manually on the server. The DNS sso.pdhc.se will be set before we get there. 

---

## Q13 — Audit logging

SSO handles health data access. No logging strategy is in the plan. Proposal: add structured audit logging for login attempts, admin actions, and access decisions.

→ Add audit logging? (yes/no, and if yes — file-based or DB table): yes , file based

---

## Q14 — Consulting _obs_gateway_repo

Rule 6 says a previous prototype exists in `_obs_gateway_repo`. The plan never references it. Should we review it for reusable patterns/code before starting Phase 1?

→ Review old repo first? (yes/no): No, the file SSO_Service_Functions_SV.md is a result of a review of the old proj. There were multiple errors in that so use it carefully and not as a master truth.
