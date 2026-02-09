from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import traceback, logging

from cnr_db import (
    init_pool, get_conn, put_conn, ensure_site_type_mapping,
    get_or_create_site, insert_fact_event, insert_detail,
    delete_event, find_detail_table_for_event
)
from schemas import CloudDetail, NetworkDetail, GridDetail, Envelope

app = FastAPI(title="CNR Metrics Submission API", version="0.1.0")

logger = logging.getLogger("adapter")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print("[adapter] Exception:", e, flush=True)
        traceback.print_exc()
        raise

@app.on_event("startup")
def _startup():
    init_pool()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/cnr-sql-adapter")
def submit_metrics(payload: Envelope):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                site_type = payload.sites.site_type
                detail_table = ensure_site_type_mapping(cur, site_type)
                # site_id = get_or_create_site(cur, site_type, payload.fact_site_event.get("site"))
                site_id = get_or_create_site(cur, payload.sites.site_type, payload.fact_site_event.get("site"))
                
                print(f"Site type: {site_type} --> Site ID: {site_id}")

                if site_type == "cloud":
                    detail = payload.detail_cloud; CloudDetail(**detail)
                elif site_type == "network":
                    detail = payload.detail_network; NetworkDetail(**detail)
                elif site_type == "grid":
                    detail = payload.detail_grid; GridDetail(**detail)
                else:
                    raise HTTPException(status_code=400, detail="Unsupported site_type")
                
                f = payload.fact_site_event
                f["site_id"] = site_id
                event_id = insert_fact_event(cur, site_id, f)

                cur.execute("SELECT site_id FROM monitoring.fact_site_event WHERE event_id=%s", (event_id,))
                site_id_db = cur.fetchone()[0]

                # Use the DB-authoritative site_id for the detail insert (once)
                insert_detail(cur, site_type, event_id, event_id, f["execunitid"], detail)


        return JSONResponse({"ok": True, "event_id": event_id, "detail_table": detail_table, "site_id": site_id})
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=ve.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)

@app.get("/get-cnr-entry/{event_id}")
def get_cnr_entry(event_id: int):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                site_type, detail_table = find_detail_table_for_event(cur, event_id)

                cur.execute(
                    "SELECT f.*, s.site_type::text AS site_type, s.description AS site_description "
                    "FROM monitoring.fact_site_event f "
                    "JOIN monitoring.sites s ON s.site_id = f.site_id "
                    "WHERE f.event_id = %s",
                    (event_id,),
                )
                fact = cur.fetchone()
                if not fact:
                    raise HTTPException(status_code=404, detail="Event not found")

                cur.execute(f"SELECT * FROM monitoring.{detail_table} WHERE event_id = %s", (event_id,))
                detail = cur.fetchone()

                return {
                    "event_id": event_id,
                    "site_type": site_type,
                    "detail_table": detail_table,
                    "fact": fact,
                    "detail": detail,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)

@app.delete("/delete-cnr-entry/{event_id}")
def delete_cnr_entry(event_id: int):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                site_type = delete_event(cur, event_id)
        return {"ok": True, "deleted_event_id": event_id, "site_type": site_type}
    except ValueError:
        raise HTTPException(status_code=404, detail="Event not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)

@app.get("/entries/by-site/{site_id}")
def list_entries_by_site(site_id: int):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT f.*, s.site_type::text AS site_type, s.description AS site_description
                    FROM monitoring.fact_site_event f
                    JOIN monitoring.sites s ON s.site_id = f.site_id
                    WHERE f.site_id = %s
                    ORDER BY f.event_id DESC
                    """,
                    (site_id,),
                )
                # rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                return {"site_id": site_id, "count": len(rows), "events": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)

@app.delete("/entries/by-site/{site_id}")
def delete_entries_by_site(site_id: int):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # collect event_ids for that site
                cur.execute("SELECT event_id FROM monitoring.fact_site_event WHERE site_id = %s", (site_id,))
                ids = [r[0] for r in cur.fetchall()]
                if not ids:
                    return {"ok": True, "site_id": site_id, "deleted": 0, "event_ids": []}

                deleted = 0
                for eid in ids:
                    delete_event(cur, eid)  # your helper handles detail + fact (and site_type resolution)
                    deleted += 1

                return {"ok": True, "site_id": site_id, "deleted": deleted, "event_ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)

@app.delete("/reset-all")
def reset_all():
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # clear detail tables first because of FKs
                cur.execute("TRUNCATE monitoring.detail_cloud CASCADE")
                cur.execute("TRUNCATE monitoring.detail_network CASCADE")
                cur.execute("TRUNCATE monitoring.detail_grid CASCADE")
                # then clear fact + sites
                cur.execute("TRUNCATE monitoring.fact_site_event CASCADE")
                cur.execute("TRUNCATE monitoring.sites CASCADE")
        return {"ok": True, "message": "All monitoring tables have been reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)
