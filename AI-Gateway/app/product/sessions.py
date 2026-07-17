"""Password and cookie sessions for human workspace users."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
import base64
import os
from pathlib import Path
import secrets

import psycopg
from psycopg.types.json import Jsonb

from app.knowledge.authentication import KnowledgePrincipal, KnowledgeRole
from app.product.restore_attestation import (
    RestoreAttestationError,
    verify_signed_report,
)


def _hash_secret(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _password_hash(password: str, salt: bytes, iterations: int) -> str:
    digest = pbkdf2_hmac("sha256", password.encode(), salt, iterations, dklen=32)
    return base64.b64encode(digest).decode()


@dataclass(slots=True)
class WorkspaceSessionManager:
    database_url: str
    restore_trust_root: str | None = None
    session_hours: int = 12
    password_iterations: int = 310_000
    max_failed_attempts: int = 5
    lock_minutes: int = 15

    def _connect(self):
        return psycopg.connect(self.database_url)

    def create_user(self, username: str, password: str, display_name: str, roles: list[str]):
        username = username.strip().lower()
        if len(username) < 3 or len(password) < 12:
            raise ValueError("Username or password does not meet security requirements")
        normalized_roles = [KnowledgeRole(role).value for role in roles]
        salt = os.urandom(16)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO workspace_users(
                    username,display_name,password_hash,password_salt,password_iterations,roles
                ) VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username) DO NOTHING RETURNING user_id
            """, (username, display_name.strip(), _password_hash(password, salt, self.password_iterations),
                  base64.b64encode(salt).decode(), self.password_iterations, normalized_roles))
            row = cursor.fetchone()
            if row:
                cursor.execute("INSERT INTO authentication_events(username,event_type) VALUES (%s,'user_created')", (username,))
        return bool(row)

    def login(self, username: str, password: str, user_agent: str | None):
        username = username.strip().lower()
        now = datetime.now(timezone.utc)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT user_id,display_name,password_hash,password_salt,password_iterations,
                       roles,status,failed_attempts,locked_until
                FROM workspace_users WHERE username=%s FOR UPDATE
            """, (username,))
            row = cursor.fetchone()
            valid = False
            if row and row[6] == "active" and (row[8] is None or row[8] <= now):
                candidate = _password_hash(password, base64.b64decode(row[3]), row[4])
                valid = compare_digest(candidate, row[2])
            if not valid:
                if row:
                    attempts = row[7] + 1
                    locked = now + timedelta(minutes=self.lock_minutes) if attempts >= self.max_failed_attempts else None
                    cursor.execute("UPDATE workspace_users SET failed_attempts=%s,locked_until=%s,updated_at=now() WHERE user_id=%s", (attempts, locked, row[0]))
                cursor.execute("INSERT INTO authentication_events(username,event_type,details) VALUES (%s,'login_failed',%s)", (username, '{"reason":"invalid_credentials"}'))
                raise PermissionError("Invalid username or password")
            cursor.execute("UPDATE workspace_users SET failed_attempts=0,locked_until=NULL,updated_at=now() WHERE user_id=%s", (row[0],))
            session_token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            expires_at = now + timedelta(hours=self.session_hours)
            cursor.execute("""
                INSERT INTO workspace_sessions(user_id,token_hash,csrf_hash,expires_at,user_agent_hash)
                VALUES (%s,%s,%s,%s,%s)
            """, (row[0], _hash_secret(session_token), _hash_secret(csrf_token), expires_at,
                  _hash_secret(user_agent or "unknown")))
            cursor.execute("INSERT INTO authentication_events(username,event_type) VALUES (%s,'login_succeeded')", (username,))
        return session_token, csrf_token, expires_at, {
            "username": username, "display_name": row[1], "roles": list(row[5]),
        }

    def authenticate(self, session_token: str | None, csrf_token: str | None = None, *, require_csrf=False):
        if not session_token:
            raise PermissionError("A workspace session or Bearer token is required")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.username,u.roles,s.csrf_hash,s.expires_at
                FROM workspace_sessions s JOIN workspace_users u ON u.user_id=s.user_id
                WHERE s.token_hash=%s AND s.revoked_at IS NULL AND u.status='active'
            """, (_hash_secret(session_token),))
            row = cursor.fetchone()
            if row is None or row[3] <= datetime.now(timezone.utc):
                raise PermissionError("Workspace session is invalid or expired")
            if require_csrf and (not csrf_token or not compare_digest(_hash_secret(csrf_token), row[2])):
                raise PermissionError("CSRF validation failed")
            cursor.execute("UPDATE workspace_sessions SET last_seen_at=now() WHERE token_hash=%s", (_hash_secret(session_token),))
        return KnowledgePrincipal(row[0], frozenset(KnowledgeRole(role) for role in row[1])), row[3]

    def logout(self, session_token: str | None):
        if not session_token:
            return
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                UPDATE workspace_sessions SET revoked_at=now()
                WHERE token_hash=%s AND revoked_at IS NULL RETURNING user_id
            """, (_hash_secret(session_token),))
            row = cursor.fetchone()
            if row:
                cursor.execute("INSERT INTO authentication_events(username,event_type) SELECT username,'logout' FROM workspace_users WHERE user_id=%s", (row[0],))

    def refresh_csrf(self, session_token: str | None):
        principal, expires_at = self.authenticate(session_token)
        csrf_token = secrets.token_urlsafe(32)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE workspace_sessions SET csrf_hash=%s WHERE token_hash=%s AND revoked_at IS NULL",
                (_hash_secret(csrf_token), _hash_secret(session_token)),
            )
        return principal, expires_at, csrf_token

    def administration_overview(self):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT count(*) FILTER (WHERE status='active'),
                       count(*) FILTER (WHERE status='disabled') FROM workspace_users
            """)
            active_users, disabled_users = cursor.fetchone()
            cursor.execute("""
                SELECT count(*) FROM workspace_sessions
                WHERE revoked_at IS NULL AND expires_at > now()
            """)
            active_sessions = cursor.fetchone()[0]
            cursor.execute("""
                SELECT count(*) FROM authentication_events
                WHERE event_type='login_failed' AND occurred_at > now() - interval '24 hours'
            """)
            failed_logins = cursor.fetchone()[0]
        return {"active_users": active_users, "disabled_users": disabled_users,
                "active_sessions": active_sessions, "failed_logins_24h": failed_logins}

    def administration_users(self):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.user_id,u.username,u.display_name,u.roles,u.status,u.locked_until,
                       u.created_at,count(s.session_id) FILTER (
                           WHERE s.revoked_at IS NULL AND s.expires_at > now())
                FROM workspace_users u LEFT JOIN workspace_sessions s ON s.user_id=u.user_id
                GROUP BY u.user_id ORDER BY u.username
            """)
            rows = cursor.fetchall()
        return [{"user_id": str(r[0]), "username": r[1], "display_name": r[2],
                 "roles": list(r[3]), "status": r[4],
                 "locked_until": r[5].isoformat() if r[5] else None,
                 "created_at": r[6].isoformat(), "active_sessions": r[7]} for r in rows]

    def set_user_status(self, user_id: str, status: str, actor: str):
        if status not in {"active", "disabled"}:
            raise ValueError("Invalid user status")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT username FROM workspace_users WHERE user_id=%s FOR UPDATE", (user_id,))
            row = cursor.fetchone()
            if not row:
                raise LookupError("User not found")
            if row[0] == actor and status == "disabled":
                raise ValueError("An administrator cannot disable their own account")
            cursor.execute("UPDATE workspace_users SET status=%s,updated_at=now() WHERE user_id=%s", (status, user_id))
            if status == "disabled":
                cursor.execute("UPDATE workspace_sessions SET revoked_at=now() WHERE user_id=%s AND revoked_at IS NULL", (user_id,))
            cursor.execute("INSERT INTO authentication_events(username,event_type,details) VALUES (%s,%s,%s)",
                           (row[0], f"user_{status}", Jsonb({"actor": actor})))
        return {"user_id": user_id, "username": row[0], "status": status}

    def revoke_user_sessions(self, user_id: str, actor: str):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT username FROM workspace_users WHERE user_id=%s", (user_id,))
            row = cursor.fetchone()
            if not row:
                raise LookupError("User not found")
            cursor.execute("UPDATE workspace_sessions SET revoked_at=now() WHERE user_id=%s AND revoked_at IS NULL", (user_id,))
            count = cursor.rowcount
            cursor.execute("INSERT INTO authentication_events(username,event_type,details) VALUES (%s,'sessions_revoked',%s)",
                           (row[0], Jsonb({"actor": actor})))
        return {"user_id": user_id, "revoked_sessions": count}

    def administration_audit(self, limit: int = 50):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT event_id,username,event_type,occurred_at,details
                FROM authentication_events ORDER BY occurred_at DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
        return [{"event_id": str(r[0]), "username": r[1], "event_type": r[2],
                 "occurred_at": r[3].isoformat(), "details": r[4]} for r in rows]

    def recovery_status(self):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT backup_id,backup_stamp,status,database_verified,minio_verified,
                       knowledge_verified,completed_at,error,backup_set_id,
                       backup_set_hash,manifest_path,integrity_verified
                FROM backup_runs ORDER BY started_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            restore = None
            if row and row[9]:
                cursor.execute("""
                    SELECT verification_id,target_kind,target_identifier,components,
                           outcome,checks,actor,started_at,completed_at,content_hash,
                           report,attestation_algorithm,attestation_key_id,
                           attestation_signature
                    FROM backup_restore_verifications
                    WHERE backup_id=%s AND backup_set_hash=%s
                    ORDER BY completed_at DESC LIMIT 1
                """, (row[0], row[9]))
                restore = cursor.fetchone()
        if not row:
            return {
                "ready": False,
                "ready_semantics": "deprecated_backup_integrity_alias",
                "backup_integrity_ready": False,
                "restore_verified": False,
                "recovery_ready": False,
                "latest_backup": None,
                "latest_restore": None,
                "message": "No verified backup has been recorded",
            }
        legacy_ready = row[2] == "completed" and all(row[3:6])
        backup_integrity_ready = legacy_ready and bool(row[11]) and all(row[8:11])
        restore_trust_valid = False
        if restore and restore[4] == "verified" and self.restore_trust_root:
            try:
                verify_signed_report(restore[10], Path(self.restore_trust_root))
                restore_trust_valid = (
                    restore[11] == restore[10]["attestation"]["algorithm"]
                    and restore[12] == restore[10]["attestation"]["key_id"]
                    and restore[13] == restore[10]["attestation"]["signature"]
                    and restore[9] == restore[10]["content_hash"]
                )
            except (KeyError, TypeError, RestoreAttestationError):
                restore_trust_valid = False
        restore_verified = bool(restore and restore[4] == "verified" and restore_trust_valid)
        recovery_ready = backup_integrity_ready and restore_verified
        if recovery_ready:
            message = "Backup integrity and isolated restore are verified"
        elif backup_integrity_ready:
            message = "Backup integrity is verified; isolated restore is not verified"
        elif legacy_ready:
            message = "Legacy backup checks passed; portable backup-set integrity is not verified"
        else:
            message = "Backup verification is incomplete"
        latest_restore = None if not restore else {
            "verification_id": str(restore[0]),
            "target_kind": restore[1],
            "target_identifier": restore[2],
            "components": list(restore[3]),
            "outcome": restore[4],
            "checks": restore[5],
            "actor": restore[6],
            "started_at": restore[7].isoformat(),
            "completed_at": restore[8].isoformat(),
            "content_hash": restore[9],
            "trust_valid": restore_trust_valid,
        }
        return {
            # Compatibility alias for existing API consumers; it must not be used
            # as a claim that an isolated restore has succeeded.
            "ready": legacy_ready,
            "ready_semantics": "deprecated_backup_integrity_alias",
            "backup_integrity_ready": backup_integrity_ready,
            "restore_verified": restore_verified,
            "recovery_ready": recovery_ready,
            "latest_backup": {
                "backup_id": str(row[0]),
                "stamp": row[1],
                "status": row[2],
                "database_verified": row[3],
                "minio_verified": row[4],
                "knowledge_verified": row[5],
                "completed_at": row[6].isoformat() if row[6] else None,
                "error": row[7],
                "backup_set_id": row[8],
                "backup_set_hash": row[9],
                "manifest_path": row[10],
                "integrity_verified": row[11],
            },
            "latest_restore": latest_restore,
            "message": message,
        }
