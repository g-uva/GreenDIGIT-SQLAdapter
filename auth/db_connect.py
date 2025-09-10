import os
import psycopg2
from dotenv import load_dotenv

load_dotenv() # necessary to get the password from the .env file.

DB_PASSWORD = os.environ["CNR_POSTEGRESQL_PASSWORD"]

conn = psycopg2.connect(
     database="greendigit-db",
     user="greendigit-u",
     host="greendigit-postgresql.cloud.d4science.org",
     password=DB_PASSWORD,
     port=5432
)

cur = conn.cursor()
cur.execute("SELECT schema_name FROM information_schema.schemata;")

schemas = cur.fetchall()
for schema in schemas:
    print(schema[0])

cur.close()
conn.close()

print("Evertyhing done. :)")