from __future__ import annotations
import hashlib,secrets,sqlite3,time
from contextlib import contextmanager
from .settings import settings
DB_PATH=settings.data_dir/"hub.db"
SCHEMA="""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,is_admin INTEGER NOT NULL DEFAULT 0,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,csrf_token TEXT NOT NULL,expires_at REAL NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,base_url TEXT NOT NULL UNIQUE,enabled INTEGER NOT NULL DEFAULT 1,verified INTEGER NOT NULL DEFAULT 0,accelerator_id TEXT,max_parallel INTEGER NOT NULL DEFAULT 1,last_status TEXT,last_seen REAL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL DEFAULT '',created_at REAL NOT NULL,updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,title TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'open',due_at REAL,created_at REAL NOT NULL,updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,title TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',starts_at REAL NOT NULL,ends_at REAL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,mode TEXT NOT NULL DEFAULT 'auto',payload TEXT NOT NULL,requirements TEXT NOT NULL DEFAULT '{}',status TEXT NOT NULL DEFAULT 'queued',service_id INTEGER,worker_id TEXT,priority INTEGER NOT NULL DEFAULT 0,result_summary TEXT,error TEXT,created_at REAL NOT NULL,started_at REAL,finished_at REAL,lease_until REAL);
CREATE TABLE IF NOT EXISTS workers(id TEXT PRIMARY KEY,name TEXT NOT NULL,platform TEXT NOT NULL,capabilities TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'online',last_seen REAL NOT NULL);
"""
@contextmanager
def connect():
    conn=sqlite3.connect(DB_PATH,timeout=30);conn.row_factory=sqlite3.Row;conn.execute("PRAGMA foreign_keys=ON")
    try: yield conn;conn.commit()
    finally: conn.close()
def password_hash(password:str,salt:bytes|None=None)->str:
    salt=salt or secrets.token_bytes(16);digest=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1)
    return "scrypt$16384$"+salt.hex()+"$"+digest.hex()
def password_ok(password:str,encoded:str)->bool:
    try:
        _,_,salt_hex,expected=encoded.split("$",3);actual=password_hash(password,bytes.fromhex(salt_hex)).split("$",3)[3]
        return secrets.compare_digest(actual,expected)
    except (ValueError,TypeError): return False
def initialize()->str|None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        columns={row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        if "worker_id" not in columns: conn.execute("ALTER TABLE jobs ADD COLUMN worker_id TEXT")
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone(): return None
        password=settings.admin_password or secrets.token_urlsafe(15)
        conn.execute("INSERT INTO users(username,password_hash,is_admin,created_at) VALUES(?,?,1,?)",(settings.admin_user,password_hash(password),time.time()))
        return password
def rows(sql:str,params:tuple=())->list[dict]:
    with connect() as conn:return [dict(row) for row in conn.execute(sql,params).fetchall()]
