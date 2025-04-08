from sqlalchemy import text
import sys
import os
import importlib

# Přidáme kořenový adresář do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importujeme z kořenového adresáře
from db import DatabaseConnection, EmployeeCountMapping

def create_employee_count_mapping_table():
    db_conn = DatabaseConnection()
    session = db_conn.get_session()
    engine = db_conn._engine
    
    try:
        print("Kontroluji existenci tabulky employee_count_mapping...")
        # Pokud tabulka existuje, smažeme ji (kvůli čistému vytvoření)
        session.execute(text("DROP TABLE IF EXISTS employee_count_mapping CASCADE"))
        session.commit()
        print("Tabulka employee_count_mapping byla smazána (pokud existovala).")
        
        # Znovu načteme modul db.py, aby se načetly případné změny v definici modelů
        print("Znovu načítám definice tabulek...")
        import db
        importlib.reload(db)
        
        # Kontrola, zda je tabulka employee_count_mapping zaregistrována
        from db import Base as ReloadedBase
        if 'employee_count_mapping' not in ReloadedBase.metadata.tables:
            raise ValueError("Tabulka 'employee_count_mapping' není zaregistrována v Base.metadata. Zkontroluj definici v db.py.")
        print("Tabulka employee_count_mapping je zaregistrována v Base.metadata.")
        
        # Vytvoříme schéma pro tabulku employee_count_mapping
        print("Vytvářím tabulku employee_count_mapping...")
        ReloadedBase.metadata.create_all(engine, tables=[ReloadedBase.metadata.tables['employee_count_mapping']])
        print("Tabulka employee_count_mapping byla úspěšně vytvořena.")
        
    except Exception as e:
        session.rollback()
        print(f"Chyba při vytváření tabulky employee_count_mapping: {e}")
    finally:
        session.close()

def populate_employee_count_mapping():
    db_conn = DatabaseConnection()
    session = db_conn.get_session()
    
    # Seznam intervalů a jejich maximálních hodnot
    intervals = [
        ("1 – 5 zaměstnanců", 5),
        ("10 – 19 zaměstnanců", 19),
        ("100 – 199 zaměstnanců", 199),
        ("20 – 24 zaměstnanců", 24),
        ("200 – 249 zaměstnanců", 249),
        ("25 – 49 zaměstnanců", 49),
        ("250 – 499 zaměstnanců", 499),
        ("50 – 99 zaměstnanců", 99),
        ("500 – 999 zaměstnanců", 999),
        ("6 – 9 zaměstnanců", 9),
        ("Bez zaměstnanců", 0),
        ("Neuvedeno", None),  # NULL hodnota pro "Neuvedeno"
    ]
    
    try:
        print("Kontroluji, zda je tabulka employee_count_mapping prázdná...")
        # Zjistíme, zda už tabulka obsahuje nějaké záznamy
        existing_records = session.query(EmployeeCountMapping).count()
        if existing_records > 0:
            print(f"Tabulka employee_count_mapping již obsahuje {existing_records} záznamů. Mažu existující data...")
            session.query(EmployeeCountMapping).delete()
            session.commit()
        
        print("Vkládám předem nastavené hodnoty do tabulky employee_count_mapping...")
        # Vložení dat do tabulky
        for interval, max_count in intervals:
            record = EmployeeCountMapping(
                interval_zamestnancu=interval,
                max_pocet_zamestnancu=max_count
            )
            session.add(record)
        
        # Potvrzení změn
        session.commit()
        print(f"Úspěšně vloženo {len(intervals)} záznamů do tabulky employee_count_mapping.")
        
    except Exception as e:
        session.rollback()
        print(f"Chyba při vkládání dat do tabulky employee_count_mapping: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Nejprve vytvoříme tabulku
    create_employee_count_mapping_table()
    # Poté ji naplníme daty
    populate_employee_count_mapping()