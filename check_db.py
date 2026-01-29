import sqlite3

conn = sqlite3.connect('data/database.db')
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print("=== TABLES ===")
print(tables)

# Check applications table for test data
print("\n=== ALL APPLICATIONS ===")
try:
    cur.execute("SELECT * FROM applications")
    apps = cur.fetchall()
    for app in apps:
        print(app)
    print(f"\nTotal: {len(apps)} applications")
except Exception as e:
    print(f"Error: {e}")

# Check for suspicious entries (DiagnoseTest from CSRF tests)  
print("\n=== SUSPICIOUS ENTRIES (Test/Diagnose) ===")
try:
    cur.execute("SELECT * FROM applications WHERE roblox_user LIKE '%Diagnose%' OR roblox_user LIKE '%Test%' OR discord_name LIKE '%Test%'")
    suspicious = cur.fetchall()
    for s in suspicious:
        print(s)
    print(f"\nFound: {len(suspicious)} suspicious entries")
except Exception as e:
    print(f"Error: {e}")

# Check forum posts
print("\n=== FORUM POSTS ===")
try:
    cur.execute("SELECT * FROM forum_posts")
    posts = cur.fetchall()
    for p in posts:
        print(p)
    print(f"\nTotal: {len(posts)} posts")
except Exception as e:
    print(f"Error: {e}")

# Check blacklist
print("\n=== BLACKLIST ===")
try:
    cur.execute("SELECT * FROM blacklist")
    bans = cur.fetchall()
    for b in bans:
        print(b)
    print(f"\nTotal: {len(bans)} bans")
except Exception as e:
    print(f"Error: {e}")

# Check IP warnings
print("\n=== IP WARNINGS ===")
try:
    cur.execute("SELECT * FROM ip_warnings")
    warnings = cur.fetchall()
    for w in warnings:
        print(w)
    print(f"\nTotal: {len(warnings)} IP warnings")
except Exception as e:
    print(f"Error: {e}")

conn.close()
