# To activate the environment.
python -m venv . && source bin/activate
pip install -r app/requirements.txt

# To start the app locally (for prod, do it through Docker).
uvicorn app.main:app --reload --host 0.0.0.0 --port 8033

# Submit the three examples
curl -s localhost:8033/submit-metrics -H 'content-type: application/json' --data @app/mock_data/payload_cloud.json | jq
curl -s localhost:8033/submit-metrics -H 'content-type: application/json' --data @app/mock_data/payload_network.json | jq
curl -s localhost:8033/submit-metrics -H 'content-type: application/json' --data @app/mock_data/payload_grid.json | jq

# Fetch one back
curl -s localhost:8033/get-cnr-entry/123 | jq

# Delete it
curl -s -X DELETE localhost:8033/delete-cnr-entry/123 | jq


curl -s localhost:8033/cnr-sql-adapter -H 'content-type: application/json' \
     --data "{
  "site_type": "network",
  "site_description": "GARR backbone Milan link",
  "fact": {
    "event_start_timestamp": "2025-09-18 12:00:00",
    "event_end_timestamp": "2025-09-18 12:30:00",
    "job_finished": true,
    "CI_g": 38,
    "CFP_g": 42,
    "PUE": 1.50,
    "site": "GARR backbone Milan link",
    "energy_wh": 85.4,
    "work": 0.0,
    "startexectime": "2025-09-18 12:00:02",
    "stopexectime": "2025-09-18 12:29:58",
    "status": "success",
    "owner": "CNR",
    "execunitid": "exec-net-101",
    "execunitfinished": true
  },
  "detail": {
    "amountofdatatransferred": 9876543210,
    "networktype": "WAN",
    "measurementtype": "InterfaceCounter",
    "destinationexecunitid": "exec-cloud-001"
  }
}" | jq


curl -s localhost:8033/cnr-sql-adapter -H 'content-type: application/json' \
     --data "{
  "site": "AEGIS01-IPB-SCL",
  "duration_s": 3590,
  "sites": { "site_type": "cloud" },
  "fact_site_event": {
    "site": "AEGIS01-IPB-SCL",
    "event_start_timestamp": "2025-01-01T12:00:00Z",
    "event_end_timestamp": "2025-01-01T13:00:00Z",
    "execunitfinished": true,
		"job_finished": true,
    "startexectime": "2025-01-01T12:00:05Z",
    "stopexectime": "2025-01-01T12:59:55Z",
    "execunitid": "compute-12345"
  },
  "detail_cloud": {
    "execunitid": "compute-12345"
  }
}" | jq


