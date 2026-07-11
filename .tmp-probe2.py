import sqlite3

c = sqlite3.connect("lyrics.db")
print("exact", c.execute("SELECT char,jyutping,finals FROM words WHERE char=?", ("困潦倒",)).fetchall())
print("suffix", c.execute("SELECT char,jyutping FROM words WHERE char LIKE ? LIMIT 3", ("%困潦倒",)).fetchall())
print("len4", c.execute("SELECT COUNT(*) FROM words WHERE length=4").fetchone())
print("sample finals", c.execute("SELECT finals,jyutping FROM words WHERE length=4 LIMIT 2").fetchall())
c.close()
