import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
connection_pool = pool.SimpleConnectionPool(1, 10, DATABASE_URL)

def get_connection():
    return connection_pool.getconn()

def release_connection(conn):
    connection_pool.putconn(conn)


def get_property(property):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM properties WHERE properties.id = %s", (property,))
    rows = cur.fetchone()
    cur.close()
    release_connection(conn)
    return rows

def get_properties():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM properties")
    rows = cur.fetchall()
    cur.close()
    release_connection(conn)
    return rows

def get_lease(property):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT leases.id, properties.name, leases.tenant_name, leases.monthly_rent FROM leases JOIN properties ON properties.id = leases.property_id WHERE properties.id = %s", (property,))
    rows = cur.fetchall()
    cur.close()
    release_connection(conn)
    return rows

def create_property(prop):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("INSERT INTO properties(name,address,city,square_ft,floors,market_value)"
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",(prop.name,prop.address,prop.city,prop.square_ft,prop.floors,prop.market_value,))
    rows = cur.fetchone()
    conn.commit()
    cur.close()
    release_connection(conn)
    return rows

def create_leases(property_id,lease):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("INSERT INTO leases(property_id,tenant_name,start_date,end_date,monthly_rent,leased_sqft) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING *", (property_id, lease.tenant_name,lease.start_date,lease.end_date,lease.monthly_rent,lease.leased_sqft,))
    rows = cur.fetchone()
    conn.commit()
    cur.close()
    release_connection(conn)
    return rows 


def delete_property(property_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM properties WHERE properties.id = %s RETURNING *",(property_id,))
    rows = cur.fetchone()
    conn.commit()
    cur.close()
    release_connection(conn)
    return rows

def calculate_monthly_revenue(property_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT COALESCE(SUM(monthly_rent), 0) AS total_revenue FROM leases WHERE property_id = %s",(property_id,))
    row = cur.fetchone()
    cur.close()
    release_connection(conn)
    return row

def expiring_leases(days):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM leases "
                        "WHERE end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + (%s * INTERVAL '1 day') "
                        "ORDER BY end_date",(days,))
    row = cur.fetchall()
    cur.close()
    release_connection(conn)
    return row

def delete_lease(lease_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM leases WHERE id = %s RETURNING *", (lease_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_connection(conn)
    return row

def get_all_leases():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM leases")
    rows = cur.fetchall()
    cur.close()
    release_connection(conn)
    return rows

def occupancy():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT properties.id, properties.name, properties.square_ft, "
        "COALESCE(SUM(leases.leased_sqft), 0) AS leased_sqft, "
        "properties.square_ft - COALESCE(SUM(leases.leased_sqft), 0) AS remaining_sqft, "
        "ROUND(COALESCE(SUM(leases.leased_sqft), 0) * 100.0 / NULLIF(properties.square_ft, 0), 2) AS occupancy_pct "
        "FROM properties LEFT JOIN leases ON properties.id = leases.property_id "
        "GROUP BY properties.id, properties.name, properties.square_ft"
    )
    rows = cur.fetchall()
    cur.close()
    release_connection(conn)
    return rows

def create_user(username, password_hash):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO users(username, password_hash) VALUES (%s, %s) RETURNING id, username",
        (username, password_hash))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_connection(conn)
    return row

def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    release_connection(conn)
    return row

def get_property_by_city(city):
    conn = get_connection()
    cur = conn.cursor(cursor_factory= RealDictCursor)
    cur.execute("SELECT * FROM properties WHERE city ILIKE %s",(city,))
    row = cur.fetchall()
    cur.close()
    release_connection(conn)
    return row