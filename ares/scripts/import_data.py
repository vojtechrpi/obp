import csv
from datetime import datetime

import sys 
import os 
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db import AresData, DatabaseConnection

def clean_value(value):
    """Odstraní všechny uvozovky a rovnítka z hodnoty"""
    if value is None:
        return value
    return value.replace('"', '').replace("'", '').replace('=', '')

def import_from_csv(csv_path):
    """Import dat z CSV souboru do databáze"""
    db_conn = DatabaseConnection()
    session = db_conn.get_session()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                # Vyčištění všech hodnot v řádku
                cleaned_row = {key: clean_value(value) for key, value in row.items()}
                
                ares_data = AresData(
                    ico=cleaned_row.get('IČO'),
                    obchodni_jmeno=cleaned_row.get('Obchodní jméno/název'),
                    datum_platnosti=parse_date(cleaned_row.get('Datum platnosti')),
                    statisticka_pravni_forma_kod=parse_int(cleaned_row.get('Statistická právní forma (kód)')),
                    statisticka_pravni_forma_nazev=cleaned_row.get('Statistická právní forma (název)'),
                    velikostni_kategorie_kod=parse_int(cleaned_row.get('Velikostní kategorie dle počtu zaměstnanců (kód)')),
                    velikostni_kategorie_nazev=cleaned_row.get('Velikostní kategorie dle počtu zaměstnanců (název)'),
                    institucionalni_sektor_kod=parse_int(cleaned_row.get('Institucionální sektor (ESA 2010) (kód)')),
                    institucionalni_sektor_nazev=cleaned_row.get('Institucionální sektor (ESA 2010) (název)'),
                    kraj_kod=cleaned_row.get('Kraj (kód)'),
                    kraj_nazev=cleaned_row.get('Kraj (název)'),
                    okres_kod=cleaned_row.get('Okres (CZ-NUTS) (kód)'),
                    okres_nazev=cleaned_row.get('Okres (CZ-NUTS) (název)'),
                    obec_kod=parse_int(cleaned_row.get('Obec (kód)')),
                    obec_nazev=cleaned_row.get('Obec (název)'),
                    adresa_sidla=cleaned_row.get('Adresa sídla'),
                    datum_vzniku=parse_date(cleaned_row.get('Datum vzniku')),
                    datum_zaniku=parse_date(cleaned_row.get('Datum zániku')),
                    zpusob_zaniku_kod=parse_int(cleaned_row.get('Způsob zániku (kód)')),
                    zpusob_zaniku_nazev=cleaned_row.get('Způsob zániku (název)'),
                    priznak=cleaned_row.get('Příznak'),
                    hlavni_nace_kod=cleaned_row.get('Hlavní ekonomická činnost (CZ NACE) (kód)'),
                    hlavni_nace_nazev=cleaned_row.get('Hlavní ekonomická činnost (CZ NACE) (název)')
                )
                
                existing = session.query(AresData).filter(AresData.ico == ares_data.ico).first()
                if existing:
                    for key, value in cleaned_row.items():
                        mapped_key = map_csv_to_column(key)
                        if hasattr(existing, mapped_key) and value:
                            setattr(existing, mapped_key, parse_value(mapped_key, value))
                else:
                    session.add(ares_data)
                
                count += 1
                if count % 1000 == 0:
                    session.commit()
                    print(f"Zpracováno {count} záznamů")
            
            session.commit()
            print(f"Import dokončen, celkem zpracováno {count} záznamů")
    
    except Exception as e:
        session.rollback()
        print(f"Chyba při importu dat: {e}")
    finally:
        session.close()

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            return datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            return None

def parse_int(int_str):
    if not int_str:
        return None
    try:
        return int(int_str)
    except ValueError:
        return None

def map_csv_to_column(csv_header):
    mapping = {
        'IČO': 'ico',
        'Obchodní jméno/název': 'obchodni_jmeno',
        'Datum platnosti': 'datum_platnosti',
        'Statistická právní forma (kód)': 'statisticka_pravni_forma_kod',
        'Statistická právní forma (název)': 'statisticka_pravni_forma_nazev',
        'Velikostní kategorie dle počtu zaměstnanců (kód)': 'velikostni_kategorie_kod',
        'Velikostní kategorie dle počtu zaměstnanců (název)': 'velikostni_kategorie_nazev',
        'Institucionální sektor (ESA 2010) (kód)': 'institucionalni_sektor_kod',
        'Institucionální sektor (ESA 2010) (název)': 'institucionalni_sektor_nazev',
        'Kraj (kód)': 'kraj_kod',
        'Kraj (název)': 'kraj_nazev',
        'Okres (CZ-NUTS) (kód)': 'okres_kod',
        'Okres (CZ-NUTS) (název)': 'okres_nazev',
        'Obec (kód)': 'obec_kod',
        'Obec (název)': 'obec_nazev',
        'Adresa sídla': 'adresa_sidla',
        'Datum vzniku': 'datum_vzniku',
        'Datum zániku': 'datum_zaniku',
        'Způsob zániku (kód)': 'zpusob_zaniku_kod',
        'Způsob zániku (název)': 'zpusob_zaniku_nazev',
        'Příznak': 'priznak',
        'Hlavní ekonomická činnost (CZ NACE) (kód)': 'hlavni_nace_kod',
        'Hlavní ekonomická činnost (CZ NACE) (název)': 'hlavni_nace_nazev'
    }
    return mapping.get(csv_header, '')

def parse_value(column_name, value):
    if 'datum' in column_name:
        return parse_date(value)
    elif 'kod' in column_name and column_name != 'hlavni_nace_kod':
        return parse_int(value)
    return value

if __name__ == "__main__":
    # Cesta k CSV souboru relativně ke kořenovému adresáři
    import_from_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'res_export_2025-03-15-184623.csv'))