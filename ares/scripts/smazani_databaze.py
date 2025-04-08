from sqlalchemy import text
import sys
import os
import importlib

# Přidáme kořenový adresář do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importujeme z kořenového adresáře
from db import DatabaseConnection

def clear_database():
    db_conn = DatabaseConnection()
    session = db_conn.get_session()
    engine = db_conn._engine
    
    try:
        print("Mažu existující tabulky...")
        # Tady explicitně smažeme tabulky (DROP TABLE) místo jejich vyprázdnění (TRUNCATE)
        # Pořadí je důležité kvůli cizím klíčům
        session.execute(text("DROP TABLE IF EXISTS accounting_data CASCADE"))
        #session.execute(text("DROP TABLE IF EXISTS ares_data CASCADE"))
        #session.execute(text("DROP TABLE IF EXISTS web_data CASCADE"))
        session.commit()
        print("Tabulky byly úspěšně smazány")
        
        # Znovu načteme modul db.py, aby se načetly případné změny v definici modelů
        print("Znovu načítám definice tabulek...")
        import db
        importlib.reload(db)
        
        # Vytvoříme schéma znovu
        print("Vytvářím nové schéma databáze...")
        # Načteme Base znovu po reloadu modulu db
        from db import Base as ReloadedBase
        ReloadedBase.metadata.create_all(engine)
        print("Schéma databáze bylo úspěšně znovu vytvořeno")
        
    except Exception as e:
        session.rollback()
        print(f"Chyba při resetování databáze: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    clear_database()