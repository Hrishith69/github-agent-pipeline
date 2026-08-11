import sqlite3

conn = sqlite3.connect("issues.db")
cursor = conn.cursor()

cursor.execute("SELECT issue_number, title, status, created_at FROM issues")
rows = cursor.fetchall()

print("\n" + "=" * 70)
print(f"{'ISSUE #':<10} | {'STATUS':<12} | {'TITLE'}")
print("=" * 70)

for row in rows:
    print(f"#{row[0]:<9} | {row[2]:<12} | {row[1]}")

print("=" * 70 + "\n")
conn.close()