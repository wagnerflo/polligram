SCHEMA = """
  CREATE TABLE IF NOT EXISTS job_hashes (
    id     INTEGER PRIMARY KEY,
    jobid  TEXT,
    hash   TEXT
  );
"""

GET_HASHES = """
  SELECT hash
    FROM job_hashes
   WHERE jobid = ?
"""

DELETE_HASHES = """
  DELETE FROM job_hashes
        WHERE jobid = ?
"""

INSERT_HASH = """
  INSERT INTO job_hashes
              ( jobid, hash )
       VALUES ( ?,     ?    )
"""

class Database:
    def __init__(self, conn):
        self.conn = conn
        with self.conn:
            self.conn.executescript(SCHEMA)

    def get_hashes(self, jobid):
        for row in self.conn.execute(GET_HASHES, (jobid,)):
            yield row[0]

    def set_hashes(self, jobid, hashes):
        with self.conn:
            self.conn.execute(DELETE_HASHES, (jobid,))
            self.conn.executemany(INSERT_HASH, ((jobid, h) for h in hashes))
