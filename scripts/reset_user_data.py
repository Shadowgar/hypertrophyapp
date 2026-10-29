#!/usr/bin/env python3
"""Explicit, snapshot-bound account reset. Never obtains a target from the environment.

Production execution is a separate operator-authorized operation after deployment.
The CLI's prepare/verify-restore commands cannot delete production records.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PRESERVE = {"alembic_version", "customized_candidate_schema"}
DELETE = {
    "authored_initial_calibrations", "authored_load_states", "body_measurement_entries",
    "coaching_recommendations", "customized_candidate_commands", "customized_candidate_events",
    "customized_candidate_heads", "customized_candidate_sessions", "customized_equipment_profiles",
    "exercise_states", "password_reset_tokens", "soreness_entries", "user_interface_preferences",
    "users", "weekly_checkins", "weekly_review_cycles", "workout_log_commands",
    "workout_occurrences", "workout_plans", "workout_session_states", "workout_set_logs",
}
ALL_TABLES = sorted(PRESERVE | DELETE)


class ResetRefused(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ResetRefused(message)


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def sha_sql(expression):
    return "encode(sha256(convert_to((" + expression + ")::text,'UTF8')),'hex')"


# Include user relations, columns/defaults, constraints, indexes and executable
# delete hooks. Unknown relations or hooks are refused, not silently cascaded.
CATALOG = """SELECT jsonb_build_object(
 'tables', COALESCE((SELECT jsonb_agg(jsonb_build_object('schema',n.nspname,'name',c.relname,'kind',c.relkind) ORDER BY n.nspname,c.relname)
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE c.relkind IN ('r','p','f','m') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'),'[]'::jsonb),
 'columns', COALESCE((SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid)) ORDER BY n.nspname,c.relname,a.attnum)
   FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
   WHERE a.attnum>0 AND NOT a.attisdropped AND c.relkind IN ('r','p') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'),'[]'::jsonb),
 'foreign_keys', COALESCE((SELECT jsonb_agg(jsonb_build_object('child_schema',cn.nspname,'child',c.relname,'parent_schema',pn.nspname,'parent',p.relname,'definition',pg_get_constraintdef(f.oid)) ORDER BY cn.nspname,c.relname,f.conname)
   FROM pg_constraint f JOIN pg_class c ON c.oid=f.conrelid JOIN pg_namespace cn ON cn.oid=c.relnamespace
   JOIN pg_class p ON p.oid=f.confrelid JOIN pg_namespace pn ON pn.oid=p.relnamespace WHERE f.contype='f'),'[]'::jsonb),
 'constraints', COALESCE((SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,f.conname,pg_get_constraintdef(f.oid)) ORDER BY n.nspname,c.relname,f.conname)
   FROM pg_constraint f JOIN pg_class c ON c.oid=f.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema'),'[]'::jsonb),
 'indexes', COALESCE((SELECT jsonb_agg(jsonb_build_array(schemaname,tablename,indexname,indexdef) ORDER BY schemaname,tablename,indexname)
   FROM pg_indexes WHERE schemaname !~ '^pg_' AND schemaname<>'information_schema'),'[]'::jsonb),
 'triggers', COALESCE((SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid)) ORDER BY n.nspname,c.relname,t.tgname)
   FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE NOT t.tgisinternal AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'),'[]'::jsonb),
 'rules', COALESCE((SELECT jsonb_agg(jsonb_build_array(schemaname,tablename,rulename,definition) ORDER BY schemaname,tablename,rulename)
   FROM pg_rules WHERE schemaname !~ '^pg_' AND schemaname<>'information_schema'),'[]'::jsonb)
)"""


def validate_catalog(catalog):
    tables = catalog["tables"]
    require(len(tables) == len(ALL_TABLES) and
            {(t["schema"], t["name"], t["kind"]) for t in tables} ==
            {("public", n, "r") for n in ALL_TABLES}, "Unreviewed table/schema scope")
    require(not catalog["triggers"] and not catalog["rules"], "Unreviewed trigger or rule")
    parents = {n: set() for n in DELETE}
    for fk in catalog["foreign_keys"]:
        child, parent = fk["child"], fk["parent"]
        require(fk["child_schema"] == fk["parent_schema"] == "public" and
                child in DELETE and parent in DELETE, "Unreviewed foreign-key boundary")
        if child != parent:
            parents[child].add(parent)
    owned = {"users"}
    while True:
        expanded = owned | {c for c, ps in parents.items() if ps & owned}
        if expanded == owned:
            break
        owned = expanded
    require(owned == DELETE, "Table has no reviewed account-ownership path")
    remaining, order = set(DELETE), []
    while remaining:
        referenced = set().union(*(parents[c] for c in remaining))
        leaves = sorted(remaining - referenced)
        require(bool(leaves), "Unreviewed cross-table foreign-key cycle")
        order.extend(leaves)
        remaining.difference_update(leaves)
    return order


def write_private(path, data):
    path = Path(path)
    require(path.parent.is_dir() and path.parent.stat().st_mode & 0o077 == 0,
            "Artifact parent must be a private directory (0700)")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise ResetRefused("Refusing existing or unsafe artifact path") from exc
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_private(path):
    p = Path(path)
    require(not p.is_symlink() and p.is_file() and p.stat().st_mode & 0o077 == 0,
            "Private regular artifact required (0600)")
    return json.loads(p.read_text())


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def command(args, data=None, stdout=None):
    try:
        r = subprocess.run(args, input=data, stdout=stdout or subprocess.PIPE,
                           stderr=subprocess.PIPE, check=True, timeout=180)
        return r.stdout or b""
    except (subprocess.SubprocessError, OSError) as exc:
        # PostgreSQL errors can contain personal row values; never echo them.
        raise ResetRefused("External command failed; transaction completion is not confirmed") from exc


def sql(target, query, readonly=True):
    if readonly:
        query = "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL statement_timeout='15s'; " + query + "; COMMIT;"
    return command(["docker", "exec", "-i", target["container"], "psql", "-X", "-q", "-At",
                    "-v", "ON_ERROR_STOP=1", "-U", target["role"], "-d", target["database"]],
                   query.encode()).decode().strip()


def verify_target(target):
    require(re.fullmatch(r"[0-9a-f]{64}", target["container"]), "Full immutable container ID required")
    require(all(re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", target[k]) for k in ("database", "role")),
            "Explicit simple database/role names required")
    require(re.fullmatch(r"[0-9]+", target["system_identifier"]), "Cluster identity required")
    c = json.loads(command(["docker", "inspect", target["container"]]))[0]
    require(c["Id"] == target["container"] and c["State"]["Running"] and
            c["Image"] == target["image"], "Container/image/state mismatch")
    labels = c["Config"].get("Labels") or {}
    if target["kind"] == "production":
        require(labels.get("com.docker.compose.project") == "hypertrophyapp" and
                labels.get("com.docker.compose.service") == "postgres", "Wrong application container")
        require(target.get("volume") and len(c["Mounts"]) == 1 and
                c["Mounts"][0].get("Name") == target["volume"] and
                c["Mounts"][0]["Type"] == "volume" and
                c["Mounts"][0]["Destination"] == "/var/lib/postgresql/data", "Volume mismatch")
        require(re.fullmatch(r"[0-9a-f]{40}", target.get("app_revision") or ""), "Deployed revision required")
        for name in ("hypertrophy-api", "hypertrophy-web"):
            app = json.loads(command(["docker", "inspect", name]))[0]
            require(app["State"]["Running"] and app["Config"]["Labels"].get("org.opencontainers.image.revision") ==
                    target["app_revision"], "Application revision mismatch")
    else:
        require(target["kind"] == "disposable" and labels.get("ferravis.disposable") == "true" and
                c["Mounts"] and all(m["Type"] == "tmpfs" for m in c["Mounts"]), "Not a verified disposable target")
    identity = json.loads(sql(target, "SELECT json_build_array(current_database(),current_user,(SELECT system_identifier::text FROM pg_control_system()))"))
    require(identity == [target["database"], target["role"], target["system_identifier"]], "Database/role/cluster mismatch")


def table_state(name):
    # Only names from the fixed scope reach SQL. Sort row digests for stable restore comparison.
    require(name in ALL_TABLES, "Unreviewed table")
    digest = sha_sql("COALESCE(string_agg(" + sha_sql("row_to_json(t)::text") + ",'' ORDER BY row_to_json(t)::text),'')")
    return f"SELECT json_build_object('table',{quote(name)},'count',count(*),'sha256',{digest}) FROM public.\"{name}\" t"


def capture(target):
    verify_target(target)
    catalog = json.loads(sql(target, CATALOG))
    order = validate_catalog(catalog)
    queries = ["SELECT " + sha_sql("(" + CATALOG + ")")]
    queries += [table_state(n) for n in ALL_TABLES]
    lines = sql(target, ";".join(queries)).splitlines()
    return {"catalog": catalog, "schema_sha256": lines[0], "tables": [json.loads(x) for x in lines[1:]], "delete_order": order}


def snapshot_check(manifest):
    p = Path(manifest["snapshot"]["path"])
    require(not p.is_symlink() and p.is_file() and p.stat().st_mode & 0o077 == 0,
            "Protected recovery snapshot is missing")
    require(file_hash(p) == manifest["snapshot"]["sha256"], "Snapshot digest mismatch")


def prepare(target, snapshot, manifest_path):
    before = capture(target)
    p = Path(snapshot).absolute()
    require(p.parent.stat().st_mode & 0o077 == 0, "Snapshot directory must be private")
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise ResetRefused("Refusing existing snapshot path") from exc
    with os.fdopen(fd, "wb") as stream:
        command(["docker", "exec", target["container"], "pg_dump", "-U", target["role"],
                 "-d", target["database"], "-Fc", "-Z", "9", "--no-owner", "--no-privileges"], stdout=stream)
        stream.flush()
        os.fsync(stream.fileno())
    require(capture(target) == before, "Data changed during snapshot; no reset manifest issued")
    manifest = {"format": 1, "created_utc": datetime.now(timezone.utc).isoformat(), "target": target,
                "inventory": before, "snapshot": {"path": str(p), "sha256": file_hash(p), "bytes": p.stat().st_size}}
    write_private(manifest_path, manifest)
    return {"status": "prepared_only", "manifest_sha256": file_hash(manifest_path),
            "snapshot_bytes": p.stat().st_size, "account_tables": len(DELETE)}


def restoration_matches(source, restored):
    """Accept only observed pg_dump/restore CHECK array-cast normalization.

    Production pre-delete comparisons remain byte-exact. PostgreSQL reparses these
    three existing CHECK expressions from a whole-array cast into element casts.
    Every other catalog field and every table's content digest must match exactly.
    """
    def normalized(inventory):
        result = copy.deepcopy(inventory)
        result.pop("schema_sha256", None)
        allowed = {
            "ck_ui_preference_appearance": ("appearance", ["light", "dark", "system"]),
            "ck_ui_preference_theme": ("theme_family", ["graphite", "charcoal", "classic"]),
            "ck_ui_preference_unit": ("weight_unit", ["kg", "lb"]),
        }
        for row in result["catalog"].get("constraints", []):
            if row[:2] != ["public", "user_interface_preferences"] or row[2] not in allowed:
                continue
            column, values = allowed[row[2]]
            whole = "CHECK ((("+column+")::text = ANY ((ARRAY[" + ", ".join(quote(v)+"::character varying" for v in values) + "])::text[])))"
            elements = "CHECK ((("+column+")::text = ANY (ARRAY[" + ", ".join("("+quote(v)+"::character varying)::text" for v in values) + "])))"
            if row[3] == whole:
                row[3] = elements
        return result
    return normalized(source) == normalized(restored)


def verify_restore(manifest_path, target, receipt_path, verify_existing=False):
    manifest = read_private(manifest_path)
    snapshot_check(manifest)
    require(target["kind"] == "disposable", "Restore is permitted only in disposable PostgreSQL")
    verify_target(target)
    if not verify_existing:
        require(json.loads(sql(target, CATALOG))["tables"] == [], "Restore target is not empty")
    if not verify_existing:
        # Archive input is streamed, never emitted or copied into source artifacts.
        with Path(manifest["snapshot"]["path"]).open("rb") as stream:
            try:
                subprocess.run(["docker", "exec", "-i", target["container"], "pg_restore", "--exit-on-error",
                                "--no-owner", "--no-privileges", "-U", target["role"], "-d", target["database"]],
                               stdin=stream, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=180)
            except subprocess.SubprocessError as exc:
                raise ResetRefused("Isolated restoration failed; no verification receipt issued") from exc
    restored = capture(target)
    require(restoration_matches(manifest["inventory"], restored), "Restored schema/content differs from snapshot inventory")
    receipt = {"status": "restore_verified", "manifest_sha256": file_hash(manifest_path),
               "snapshot_sha256": manifest["snapshot"]["sha256"], "target": target, "restored_inventory": restored,
               "verified_utc": datetime.now(timezone.utc).isoformat()}
    write_private(receipt_path, receipt)
    return {"status": receipt["status"], "tables_verified": len(ALL_TABLES)}


def require_approval(target, actual_hash, confirmation, receipt, production_approval):
    require(actual_hash == confirmation, "Exact manifest digest confirmation required")
    require(receipt and receipt.get("status") == "restore_verified" and
            receipt.get("manifest_sha256") == actual_hash, "Matching successful restore receipt required")
    if target["kind"] == "production":
        require(production_approval == "RESET ALL FERRAVIS USERS AFTER DEPLOY " + target["app_revision"],
                "Separate exact-revision production reset approval required")


def deletion_sql(target, inventory):
    order = validate_catalog(inventory["catalog"])
    statements = ["BEGIN", "SET LOCAL lock_timeout='5s'", "SET LOCAL statement_timeout='30s'",
                  "SELECT pg_advisory_xact_lock(810291027)",
                  'LOCK TABLE ' + ','.join('public."'+n+'"' for n in ALL_TABLES) + ' IN ACCESS EXCLUSIVE MODE']
    checks = [f"IF current_database()<>{quote(target['database'])} OR current_user<>{quote(target['role'])} OR (SELECT system_identifier::text FROM pg_control_system())<>{quote(target['system_identifier'])} THEN RAISE EXCEPTION 'Target identity changed'; END IF;",
              "IF " + sha_sql("(" + CATALOG + ")") + "<>" + quote(inventory["schema_sha256"]) + " THEN RAISE EXCEPTION 'Schema changed'; END IF;"]
    for state in inventory["tables"]:
        expression = "(" + table_state(state["table"]) + ")::jsonb"
        checks.append("IF " + expression + "<>" + quote(json.dumps(state)) + "::jsonb THEN RAISE EXCEPTION 'Table inventory changed'; END IF;")
    statements.append("DO $guard$ BEGIN " + " ".join(checks) + " END $guard$")
    statements += ['DELETE FROM public."'+n+'"' for n in order]
    post = ["IF EXISTS(SELECT 1 FROM public.\""+n+"\") THEN RAISE EXCEPTION 'Account data remains'; END IF;" for n in order]
    for state in inventory["tables"]:
        if state["table"] in PRESERVE:
            post.append("IF ("+table_state(state["table"])+")::jsonb<>"+quote(json.dumps(state))+"::jsonb THEN RAISE EXCEPTION 'Schema-state data changed'; END IF;")
    post.append("IF " + sha_sql("(" + CATALOG + ")") + "<>" + quote(inventory["schema_sha256"]) + " THEN RAISE EXCEPTION 'Schema changed'; END IF;")
    statements += ["DO $guard$ BEGIN " + " ".join(post) + " END $guard$", "COMMIT"]
    return ";\n".join(statements) + ";\n"


def apply_reset(manifest_path, confirmation, receipt_path, production_approval, audit_path,
                execute=False, rehearsal_container=None):
    manifest, receipt = read_private(manifest_path), read_private(receipt_path)
    snapshot_check(manifest)
    digest = file_hash(manifest_path)
    target = manifest["target"]
    inventory = manifest["inventory"]
    if rehearsal_container is not None:
        require(receipt["target"]["kind"] == "disposable" and
                receipt["target"]["container"] == rehearsal_container, "Rehearsal target mismatch")
        target = receipt["target"]
        inventory = receipt["restored_inventory"]
        require(restoration_matches(manifest["inventory"], inventory), "Restore inventory mismatch")
    require_approval(target, digest, confirmation, receipt, production_approval)
    require(receipt.get("snapshot_sha256") == manifest["snapshot"]["sha256"], "Restore snapshot mismatch")
    require(capture(target) == inventory, "Target inventory changed; prepare and approve a fresh snapshot")
    if not execute:
        return {"status": "dry_run_only", "tables_to_empty": manifest["inventory"]["delete_order"], "preserve": sorted(PRESERVE)}
    audit = {"status": "pending", "manifest_sha256": digest, "target": target,
             "started_utc": datetime.now(timezone.utc).isoformat(), "production_approval": production_approval}
    # Reserve an auditable private file before the transaction. Failure never
    # falls through to commit; an uncertain transport outcome remains explicit.
    write_private(audit_path, audit)
    try:
        sql(target, deletion_sql(target, inventory), readonly=False)
        after = capture(target)
        require(after["schema_sha256"] == inventory["schema_sha256"] and
                all(t["count"] == 0 for t in after["tables"] if t["table"] in DELETE),
                "Post-commit verification differs; investigate concurrent registration")
        audit.update(status="reset_verified", after=after, completed_utc=datetime.now(timezone.utc).isoformat())
    except ResetRefused:
        audit["status"] = "not_confirmed_inspect_before_retry"
        raise
    finally:
        with Path(audit_path).open("w") as stream:
            json.dump(audit, stream, indent=2, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    return {"status": audit["status"], "account_tables_empty": len(DELETE), "preserved_tables": sorted(PRESERVE)}


def target_options(parser):
    for flag in ("container", "database", "role", "system-identifier", "image"):
        parser.add_argument("--"+flag, required=True)
    parser.add_argument("--kind", required=True, choices=["production", "disposable"])
    parser.add_argument("--volume")
    parser.add_argument("--app-revision")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="operation", required=True)
    prep = subs.add_parser("prepare"); target_options(prep)
    prep.add_argument("--snapshot", required=True); prep.add_argument("--manifest", required=True)
    restore = subs.add_parser("verify-restore"); target_options(restore)
    restore.add_argument("--manifest", required=True); restore.add_argument("--receipt", required=True)
    restore.add_argument("--verify-existing", action="store_true", help="Verify a previously restored disposable target without writing it")
    apply = subs.add_parser("apply")
    for name in ("manifest", "confirm-manifest", "restore-receipt", "audit"):
        apply.add_argument("--"+name, required=True)
    apply.add_argument("--production-approval")
    apply.add_argument("--rehearsal-container")
    apply.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation in ("prepare", "verify-restore"):
            target = {key: getattr(args, key) for key in ("container", "database", "role", "system_identifier", "image", "kind", "volume", "app_revision")}
            result = (prepare(target, args.snapshot, args.manifest) if args.operation == "prepare" else
                      verify_restore(args.manifest, target, args.receipt, args.verify_existing))
        else:
            result = apply_reset(args.manifest, args.confirm_manifest, args.restore_receipt,
                                 args.production_approval, args.audit, args.execute, args.rehearsal_container)
        print(json.dumps(result, sort_keys=True))
    except (ResetRefused, KeyError, ValueError) as exc:
        print("Reset refused: " + (str(exc) if isinstance(exc, ResetRefused) else "Malformed artifact or target"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
