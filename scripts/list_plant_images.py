import sqlite3, os

db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.sqlite3')
if not os.path.exists(db):
    db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'online_nursery', 'db.sqlite3')
if not os.path.exists(db):
    print('DB_NOT_FOUND')
    raise SystemExit(0)
conn = sqlite3.connect(db)
cur = conn.cursor()
try:
    cur.execute('SELECT id, image FROM nursery_app_plant')
    rows = cur.fetchall()
    for r in rows:
        print(f"{r[0]}||{r[1]}")
except Exception as e:
    print('ERROR', e)
finally:
    conn.close()
