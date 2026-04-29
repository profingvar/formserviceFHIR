# Deploy: External Partners feature → miserver (sso.pdhc)

**Tarball**: `sso_pdhc_deploy_20260429T130419Z.tar.gz` (260 KB) at the repo root.

**Risk profile**: low. Two new tables (`external_partner`, `external_partner_audit`) added via idempotent `create_all()`. No existing data touched. New code paths gated behind SU-only routes; nothing breaks for existing users if you don't open the page. Worst case rollback: `git revert d8629e8 && server_deploy.sh <previous-tarball> update`.

---

## 1) Operator pre-flight checks

Before running anything:

```bash
# 1.a — SSH in
ssh miserver@192.168.1.154

# 1.b — confirm sso.pdhc DB is reachable (you'll need it for init_db.py)
docker ps --format '{{.Names}}|{{.Status}}' | grep sso_db

# 1.c — confirm safe_restart.sh exists at the expected path
ls /opt/sso_pdhc/safe_restart.sh
# (or wherever your sso.pdhc lives — adjust paths in step 3 if different)
```

If any of these fail, stop and tell me; I'll adjust.

---

## 2) Transfer the tarball

From the dev Mac (this machine):

```bash
scp /Users/martiningvar/T7_sidewinder/sso.pdhc/sso_pdhc_deploy_20260429T130419Z.tar.gz \
    miserver@192.168.1.154:~
```

---

## 3) Apply on miserver

SSH in, then:

```bash
cd /opt/sso_pdhc          # or your sso.pdhc deployment root
./server_deploy.sh ~/sso_pdhc_deploy_20260429T130419Z.tar.gz update
```

`server_deploy.sh` already exists in the repo; it backs up the previous deploy, extracts the new tarball, and lays out files. **It does not run migrations or restart on its own** — those are the next steps so you can pause and inspect.

---

## 4) Materialise the two new tables

The new tables are added to `Base.metadata` and `init_db.py` runs `create_all()` (idempotent — won't touch existing tables, only adds missing ones).

```bash
cd /opt/sso_pdhc/app
source venv/bin/activate
python scripts/init_db.py
deactivate
```

Expected output: log lines about connecting to the DB, then "Tables created" or similar with `external_partner` and `external_partner_audit` listed (or implied — `init_db.py` doesn't always print individual names; check by hand if needed):

```bash
docker exec sso_db psql -U <user> -d <db> -c "\dt" | grep external_partner
```

You should see two new tables. If you see them already from a prior run, that's fine — the migration is idempotent.

---

## 5) Restart sso.pdhc

```bash
cd /opt/sso_pdhc
./safe_restart.sh
```

Then verify:

```bash
curl -sS https://sso.pdhc.se/api/health | head
# expected: 200 with {"status":"ok"} (or your existing health-shape)
```

---

## 6) Smoke-test the new feature

### 6.a — load the admin page

In a browser, signed in as an SU:

`https://sso.pdhc.se/su/admin`

Scroll to the **External Partners** card. It should show "No external partners registered yet." with a `+ Register partner` button. The old "Service Key Management" section should be gone.

### 6.b — register a test partner

Click `+ Register partner`. Fill:

- Display name: `TEST — delete me`
- Country: `SE`
- Contact email: your own email
- Auth kind: `api_key`
- Allowed services: pick `cdr.pdhc`
- Allowed scopes: pick `fhir.observation.read`

Click Register. A yellow banner should show with a 43-character secret. **Copy it** — you'll use it to verify validation, then delete the test partner.

### 6.c — validate the credential

From the dev Mac (or from anywhere with the SSO internal service key):

```bash
curl -sS -X POST \
  -H "X-Service-Key: <your INTERNAL_SERVICE_KEY>" \
  -H "Content-Type: application/json" \
  "https://sso.pdhc.se/api/internal/partner/<partner_guid>/validate" \
  -d '{"secret":"<the secret you copied>"}'
```

Expected: 200 with an `access_blob` containing `user_type: "partner"`, your scopes, your services.

### 6.d — clean up the test partner

Click the **Revoke** button on the TEST row in the admin page. Confirm with reason "smoke test cleanup". The row's status badge turns red.

(Revoked partners stay in the table for audit visibility — that's by design. The table will get a "Hide revoked" filter in a future change if it gets noisy.)

---

## 7) Roll back if anything goes wrong

The simplest path is a previous-release rollback via `server_deploy.sh`:

```bash
cd /opt/sso_pdhc_backups
ls -t | head            # most recent backup is at the top
cd /opt/sso_pdhc
./server_deploy.sh /opt/sso_pdhc_backups/<prev-tarball-or-dir> update
./safe_restart.sh
```

The new tables will still exist (they're additive — rollback doesn't drop them automatically) but nothing will reference them. To drop them explicitly if you really want a clean slate:

```sql
DROP TABLE IF EXISTS external_partner_audit;
DROP TABLE IF EXISTS external_partner;
```

Run that against the sso.pdhc DB only after confirming rollback. Skipping this step is safe — empty tables are harmless.

---

## 8) When to do step 4–6 of the plan (the rest of the feature)

This deploy only ships the **SSO-side** feature: schema + admin page + API. Three follow-up changes are still gated, per `external_partners_plan.md` §8:

- **Step 4** — extend the request loader on each PDHC service to recognise `partner:<guid>` in `X-Source-Service`. 13 services touched. **Don't ship until at least one production partner exists** — otherwise we're shipping unused code paths to every service.
- **Step 5** — `contract.pdhc` reference validation + inline display. Self-contained change in contract.pdhc. Same gate: ship when the first Contract referencing a real partner is being drafted.
- **Step 6** — delete the legacy `KEYAUTH_SERVICE_*` config block in `src/config.py` and the unused frontend routes that fed the old UI. Before shipping, grep the prod env on miserver:

  ```bash
  grep -rE 'KEYAUTH_SERVICE_' /opt/sso_pdhc/app/.env
  ```

  If empty, safe to remove. If anything is set, find out what's using it (probably nothing — the UI was broken — but verify) before deleting.

Tell me when you want any of these and I'll prep them.

---

## 9) Contact

If anything in this deploy looks wrong, stop at the failing step and ping back with the error. I'll diagnose against the local code (which I just pushed to `profingvar/formserviceFHIR`).
