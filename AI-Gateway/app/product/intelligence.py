"""Immutable AI analysis and human review ledger."""

from dataclasses import dataclass
from hashlib import sha256
import psycopg


@dataclass(slots=True)
class IntelligenceLedger:
    database_url: str

    def record(self, *, object_id, project_id, action, actor_id, provider, model, prompt, output):
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("""INSERT INTO ai_analysis_runs(
                object_id,project_id,action,actor_id,provider,model,prompt_hash,output_text,output_hash)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING run_id,created_at""",
                (object_id,project_id,action,actor_id,provider,model,
                 sha256(prompt.encode()).hexdigest(),output,sha256(output.encode()).hexdigest()))
            row=cursor.fetchone()
        return str(row[0]),row[1].isoformat()

    def list(self, object_id):
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("""SELECT r.run_id,r.action,r.actor_id,r.provider,r.model,r.output_text,
                r.output_hash,r.created_at,v.decision,v.reviewer_id,v.rationale,v.occurred_at
                FROM ai_analysis_runs r LEFT JOIN LATERAL (
                  SELECT decision,reviewer_id,rationale,occurred_at FROM ai_analysis_review_events
                  WHERE run_id=r.run_id ORDER BY occurred_at DESC,review_id DESC LIMIT 1
                ) v ON true WHERE r.object_id=%s ORDER BY r.created_at DESC LIMIT 50""",(object_id,))
            rows=cursor.fetchall()
        return [{"run_id":str(r[0]),"action":r[1],"actor_id":r[2],"provider":r[3],"model":r[4],
                 "answer":r[5],"output_hash":r[6],"created_at":r[7].isoformat(),"status":"advisory",
                 "review":({"decision":r[8],"reviewer_id":r[9],"rationale":r[10],"occurred_at":r[11].isoformat()} if r[8] else None)} for r in rows]

    def review(self, run_id, decision, reviewer_id, rationale):
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT object_id FROM ai_analysis_runs WHERE run_id=%s",(run_id,))
            if not cursor.fetchone(): raise LookupError("AI analysis run not found")
            cursor.execute("""INSERT INTO ai_analysis_review_events(run_id,decision,reviewer_id,rationale)
                VALUES (%s,%s,%s,%s) RETURNING review_id,occurred_at""",(run_id,decision,reviewer_id,rationale))
            row=cursor.fetchone()
        return {"review_id":str(row[0]),"run_id":run_id,"decision":decision,"reviewer_id":reviewer_id,"rationale":rationale,"occurred_at":row[1].isoformat()}
