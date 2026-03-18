# Changed Files Tracking

All edited files listed with full path (Rule 17).

---

| Date       | File                          | Action  |
|------------|-------------------------------|---------|
| 2026-03-18 | claude1/CLAUDE.md             | Created |
| 2026-03-18 | claude1/readme.md             | Updated — fixed folder structure, references, missing models, start.sh location |
| 2026-03-18 | claude1/progress.md           | Created |
| 2026-03-18 | claude1/changed_files.md      | Created |
| 2026-03-18 | claude1/open_questions.md     | Created — CTO review questions, answered by operator |
| 2026-03-18 | claude1/readme.md             | Rewritten — incorporated all 14 CTO review decisions |
| 2026-03-18 | claude1/progress.md           | Updated — new step numbering to match revised plan |
| 2026-03-18 | claude1/readme.md             | Updated — added docs/ folder, Phase 12 documentation (7 docs), Phase 13 hardening |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 12/13 steps added |
| 2026-03-18 | claude1/.gitignore            | Created |
| 2026-03-18 | claude1/app/requirements.txt  | Created |
| 2026-03-18 | claude1/app/.env.example      | Created |
| 2026-03-18 | claude1/app/.env              | Created (not committed) |
| 2026-03-18 | claude1/app/Dockerfile        | Created |
| 2026-03-18 | claude1/app/docker-compose.yml | Created |
| 2026-03-18 | claude1/start.sh              | Created |
| 2026-03-18 | claude1/app/safe_restart.sh   | Created |
| 2026-03-18 | claude1/app/src/__init__.py   | Created |
| 2026-03-18 | claude1/app/src/app.py        | Created (stub for Phase 1) |
| 2026-03-18 | claude1/app/src/models/__init__.py | Created |
| 2026-03-18 | claude1/app/src/routes/__init__.py | Created |
| 2026-03-18 | claude1/app/src/services/__init__.py | Created |
| 2026-03-18 | claude1/app/src/fhir/__init__.py | Created |
| 2026-03-18 | claude1/app/src/middleware/__init__.py | Created |
| 2026-03-18 | claude1/app/tests/__init__.py | Created |
| 2026-03-18 | claude1/app/tests/conftest.py | Created |
| 2026-03-18 | claude1/app/tests/test_foundation.py | Created |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 1 complete |
| 2026-03-18 | claude1/initial_sql_design.txt | Created |
| 2026-03-18 | claude1/app/src/db.py         | Updated — session management, request scope, context manager |
| 2026-03-18 | claude1/app/src/models/user.py | Created |
| 2026-03-18 | claude1/app/src/models/patient.py | Created |
| 2026-03-18 | claude1/app/src/models/professional.py | Created |
| 2026-03-18 | claude1/app/src/models/organisation.py | Created |
| 2026-03-18 | claude1/app/src/models/user_organisation.py | Created |
| 2026-03-18 | claude1/app/src/models/group.py | Created |
| 2026-03-18 | claude1/app/src/models/membership.py | Created |
| 2026-03-18 | claude1/app/src/models/group_proposal.py | Created |
| 2026-03-18 | claude1/app/src/models/leader_request.py | Created |
| 2026-03-18 | claude1/app/src/models/access_request.py | Created |
| 2026-03-18 | claude1/app/src/models/invite.py | Created |
| 2026-03-18 | claude1/app/src/models/revoked_token.py | Created |
| 2026-03-18 | claude1/app/src/models/__init__.py | Updated — register all models |
| 2026-03-18 | claude1/app/scripts/init_db.py | Created |
| 2026-03-18 | claude1/app/scripts/create_su.py | Created |
| 2026-03-18 | claude1/app/tests/test_models.py | Created |
| 2026-03-18 | claude1/app/src/config.py      | Created |
| 2026-03-18 | claude1/app/src/app.py         | Updated — full factory with config, DB, middleware |
| 2026-03-18 | claude1/app/src/services/jwt_service.py | Created |
| 2026-03-18 | claude1/app/src/services/audit_log.py | Created |
| 2026-03-18 | claude1/app/src/middleware/auth_middleware.py | Created |
| 2026-03-18 | claude1/app/src/middleware/csrf.py | Created |
| 2026-03-18 | claude1/app/src/middleware/cors.py | Created |
| 2026-03-18 | claude1/app/src/middleware/rate_limit.py | Created |
| 2026-03-18 | claude1/app/tests/test_core.py | Created |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 2+3 complete |
| 2026-03-18 | claude1/app/src/services/auth_service.py | Created — authenticate_user, build_access_blob, hash/verify password |
| 2026-03-18 | claude1/app/src/routes/auth.py | Created — login, me, me/service, logout, change-password |
| 2026-03-18 | claude1/app/src/app.py         | Updated — registered auth blueprint |
| 2026-03-18 | claude1/app/src/middleware/auth_middleware.py | Updated — per-request cache fix for _get_current_user |
| 2026-03-18 | claude1/app/tests/test_auth.py | Created — 20 tests for auth API |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 4 complete |
| 2026-03-18 | claude1/app/src/routes/patient.py | Created — register, registry-status |
| 2026-03-18 | claude1/app/src/app.py         | Updated — registered patient blueprint |
| 2026-03-18 | claude1/app/tests/test_patient.py | Created — 13 tests for patient API |
| 2026-03-18 | claude1/app/tests/test_auth.py | Updated — rate limit reset in fixture |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 5 complete |
| 2026-03-18 | claude1/app/src/routes/groups.py | Created — groups, membership, admin, invites (8 endpoints) |
| 2026-03-18 | claude1/app/src/app.py         | Updated — registered groups blueprint |
| 2026-03-18 | claude1/app/tests/test_groups.py | Created — 22 tests for group API |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 6 complete |
| 2026-03-18 | claude1/app/src/routes/admin.py | Created — 16 SU admin endpoints |
| 2026-03-18 | claude1/app/src/app.py         | Updated — registered admin blueprint |
| 2026-03-18 | claude1/app/tests/test_admin.py | Created — 31 tests for admin API |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 7 complete |
| 2026-03-18 | claude1/app/src/routes/public.py | Created — public/catalog API (4 endpoints) |
| 2026-03-18 | claude1/app/src/app.py         | Updated — registered public blueprint |
| 2026-03-18 | claude1/app/tests/test_public.py | Created — 12 tests for public API |
| 2026-03-18 | claude1/progress.md           | Updated — Phase 8 complete |
| 2026-03-18 | claude1_sso/app/src/routes/frontend.py | Created — frontend blueprint (landing, login/logout, dashboard, SU admin, group admin, onboarding, docs) |
| 2026-03-18 | claude1_sso/app/src/templates/base.html | Created — PDHC Layout Standard base template |
| 2026-03-18 | claude1_sso/app/src/templates/login.html | Created — login page with SSO handshake |
| 2026-03-18 | claude1_sso/app/src/templates/dashboard.html | Created — dashboard per role |
| 2026-03-18 | claude1_sso/app/src/templates/su_admin.html | Created — SU admin panel |
| 2026-03-18 | claude1_sso/app/src/templates/group_admin.html | Created — group admin panel |
| 2026-03-18 | claude1_sso/app/src/templates/register_patient.html | Created — patient registration |
| 2026-03-18 | claude1_sso/app/src/templates/request_access.html | Created — professional access request |
| 2026-03-18 | claude1_sso/app/src/templates/request_join.html | Created — request group membership |
| 2026-03-18 | claude1_sso/app/src/templates/suggest_group.html | Created — suggest new group |
| 2026-03-18 | claude1_sso/app/src/templates/join.html | Created — join by invite |
| 2026-03-18 | claude1_sso/app/src/templates/change_password.html | Created — change password |
| 2026-03-18 | claude1_sso/app/src/templates/docs.html | Created — docs download page |
| 2026-03-18 | claude1_sso/app/src/templates/landing.html | Created — landing/service list |
| 2026-03-18 | claude1_sso/app/src/app.py     | Updated — registered frontend blueprint |
| 2026-03-18 | claude1_sso/app/tests/test_frontend.py | Created — 32 frontend tests |
| 2026-03-18 | claude1_sso/app/requirements.txt | Updated — removed pytest-flask (caused session cache interference) |
| 2026-03-18 | claude1_sso/progress.md        | Updated — Phase 9 complete |
| 2026-03-18 | claude1_sso/app/src/fhir/capability_statement.py | Created — CapabilityStatement endpoint + FHIR blueprint |
| 2026-03-18 | claude1_sso/app/src/fhir/schemas.py | Created — FHIR R5 schema helpers (patient, practitioner, organization, group) |
| 2026-03-18 | claude1_sso/app/src/services/fhir_validator.py | Created — FHIR R5 validator using fhir.resources |
| 2026-03-18 | claude1_sso/app/src/app.py     | Updated — registered FHIR blueprint |
| 2026-03-18 | claude1_sso/app/oath_overview.csv | Created — service registry CSV with schema header |
| 2026-03-18 | claude1_sso/app/tests/test_fhir.py | Created — 20 FHIR compliance tests |
| 2026-03-18 | claude1_sso/app/tests/test_admin.py | Updated — oath_overview.csv backup/restore in fixture |
| 2026-03-18 | claude1_sso/progress.md        | Updated — Phase 10 complete |
| 2026-03-18 | claude1_sso/app/tests/conftest.py | Updated — comprehensive shared fixtures for all roles |
| 2026-03-18 | claude1_sso/app/scripts/test_endpoints.sh | Created — endpoint test script against capability statement |
| 2026-03-18 | claude1_sso/progress.md        | Updated — Phase 11 complete |
| 2026-03-18 | claude1_sso/app/docs/mkdocs.yml | Created — MkDocs Material config |
| 2026-03-18 | claude1_sso/app/docs/docs/index.md | Created — documentation landing page |
| 2026-03-18 | claude1_sso/app/docs/docs/architecture.md | Created — system context, data model, auth flows, decision tree |
| 2026-03-18 | claude1_sso/app/docs/docs/api-reference.md | Created — all API endpoints with examples |
| 2026-03-18 | claude1_sso/app/docs/docs/integration-guide.md | Created — downstream service integration guide |
| 2026-03-18 | claude1_sso/app/docs/docs/admin-manual.md | Created — SU and group admin operations |
| 2026-03-18 | claude1_sso/app/docs/docs/deployment-guide.md | Created — local dev and server deployment |
| 2026-03-18 | claude1_sso/app/docs/docs/user-guide.md | Created — professional and patient workflows |
| 2026-03-18 | claude1_sso/progress.md        | Updated — Phase 12 complete |
| 2026-03-18 | claude1_sso/changed_files.md   | Updated — Phase 12 files tracked |
| 2026-03-18 | claude1_sso/app/src/app.py      | Updated — security headers, cookie security, MAX_CONTENT_LENGTH |
| 2026-03-18 | claude1_sso/progress.md        | Updated — Phase 13 complete, all phases done |
| 2026-03-18 | claude1_sso/changed_files.md   | Updated — Phase 13 files tracked |
