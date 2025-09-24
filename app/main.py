from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .cnr_db import (
    init_pool, get_conn, put_conn, ensure_site_type_mapping,
    get_or_create_site, insert_fact_event, insert_detail,
    delete_event, find_detail_table_for_event
)
from .schemas import MetricsPayload, CloudDetail, NetworkDetail, GridDetail

app = FastAPI(title="CNR Metrics Submission API", version="0.1.0")

@app.on_event("startup")
def _startup():
    init_pool()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/cnr-sql-adapter")
def submit_metrics(payload: MetricsPayload):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                detail_table = ensure_site_type_mapping(cur, payload.site_type)
                site_id = get_or_create_site(cur, payload.site_type, payload.site_description)

                # Validate the detail block per type
                if payload.sites.site_type == "cloud":
                    CloudDetail(**payload.detail)
                elif payload.sites.site_type == "network":
                    NetworkDetail(**payload.detail)
                elif payload.sites.site_type == "grid":
                    GridDetail(**payload.detail)
                else:
                    raise HTTPException(status_code=400, detail="Unsupported site_type")

                event_id = insert_fact_event(cur, site_id, payload.fact.dict())
                insert_detail(cur, payload.site_type, site_id, event_id, payload.fact.execunitid, payload.detail)

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
