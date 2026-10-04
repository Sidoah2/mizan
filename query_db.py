"""
SYNCRA Enterprise SaaS - Interactive Database Inspector & Query Utility
Author: SYNCRA AI Engine
Database: syncra_saas.db (SQLite 3)
"""

import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "syncra_saas.db")

def print_banner():
    print("=" * 75)
    print(" 🚀 SYNCRA SaaS Enterprise - أداة فحص واستعلام قاعدة البيانات (SQLite)")
    print(f" 📁 المسار: {DB_PATH}")
    print("=" * 75)

def list_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [r[0] for r in cursor.fetchall()]
    print("\n📋 الجداول المتوفرة في قاعدة البيانات (Tables in Database):")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        count = cursor.fetchone()[0]
        print(f"  • {t.ljust(20)} -> {count} سجلات (records)")
    conn.close()

def show_tenants_and_employees():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("\n🏢 العزل السحابي للشركات والأجراء (Multi-Tenant Isolation):")
    cursor.execute("SELECT id, name, legal_form, rc FROM tenants")
    tenants = cursor.fetchall()
    for t in tenants:
        tid, tname, tform, trc = t
        print(f"\n  🏢 [{tid}] {tname} ({tform}) - سجل تجاري: {trc}")
        cursor.execute("SELECT id, name, job_title, base_salary, contract_type FROM employees WHERE tenant_id = ? AND is_active = 1", (tid,))
        emps = cursor.fetchall()
        if not emps:
            print("     (لا يوجد أجراء مسجلون لهذه المؤسسة)")
        for e in emps:
            print(f"     👤 {e[0]}: {e[1]} | {e[2]} | الراتب الأساسي: {e[3]:,.2f} دج | العقد: {e[4]}")
    conn.close()

def run_custom_query(sql):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        if sql.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            print(f"\n🔍 نتائج الاستعلام ({len(rows)} صفوف):")
            for r in rows:
                print(" ", dict(r))
        else:
            conn.commit()
            print(f"✅ تم تنفيذ الاستعلام بنجاح. تم تعديل {cursor.rowcount} صفوف.")
    except Exception as e:
        print(f"❌ خطأ في الاستعلام: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print_banner()
    list_tables()
    show_tenants_and_employees()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\n⚡ تشغيل استعلام مخصص: {query}")
        run_custom_query(query)
    else:
        print("\n💡 نصيحة: يمكنك تشغيل أي استعلام SQL مخصص بتمريره كمدخل، مثال:")
        print('   python query_db.py "SELECT id, name, base_salary FROM employees"')
