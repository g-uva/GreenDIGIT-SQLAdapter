# To activate the environment.
python -m venv . && source bin/activate
pip install -r requirements.txt

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
