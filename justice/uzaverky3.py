import re
from datetime import datetime
import pdfplumber
import os
import sys
import traceback

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from db import DatabaseConnection, AccountingData

# Expanded mapping for more detailed financial statement extraction
mapa_aktiv = {
    # Existing mappings
    "": "aktiva_celkem",
    "B.": "stálá_aktiva",
    "C.": "oběžná_aktiva",
    
    # Detailed assets mappings
    "B.1.": "dlouhodobý_nehmotný_majetek",
    "B.1.2.": "software",
    "B.2.": "dlouhodobý_hmotný_majetek",
    "B.2.1.": "pozemky",
    "B.2.2.": "stavby",
    "B.3.": "dlouhodobý_finanční_majetek",
    "C.1.": "zásoby",
    "C.1.5.": "zboží",
    "C.2.": "pohledávky",
    "C.2.1.": "pohledávky_z_obchodních_vztahů",
    "C.4.": "krátkodobý_finanční_majetek",
    "C.4.1.": "peněžní_prostředky_v_pokladně",
    "C.4.2.": "peněžní_prostředky_na_účtech",
}

mapa_pasiv = {
    # Existing mappings
    "": "pasiva_celkem",
    "A.": "vlastní_kapitál",
    "A.1.": "základní_kapitál",
    "A.2.": "kapitálové_fondy",
    "A.3.": "fondy_ze_zisku",
    "A.4.": "výsledek_hospodaření_minulých_let",
    "B.+C.": "cizí_zdroje",
    
    # Detailed liabilities mappings
    "B.": "dlouhodobé_závazky",
    "B.2.": "dlouhodobé_závazky_k_úvěrovým_institucím",
    "B.3.": "dlouhodobé_závazky_z_obchodních_vztahů",
    "C.": "krátkodobé_závazky",
    "C.1.": "krátkodobé_závazky_z_obchodních_vztahů",
    "C.2.": "krátkodobé_závazky_k_zaměstnancům",
    "C.3.": "krátkodobé_závazky_sociální_zabezpečení",
    "C.4.": "krátkodobé_daňové_závazky",
}

mapa_vzz = {
    # Revenues
    "I.": "tržby_výrobky_služby",
    "II.": "tržby_za_prodej_zboží",
    
    # Performance Consumption
    "A.": "výkonová_spotřeba",
    "A.1": "náklady_vynaložené_na_prodané_zboží",
    "A.2": "spotřeba_materiálu_a_energie",
    "A.3": "služby",
    
    # Inventory Changes
    "B.": "změna_stavu_zásob_vlastní_činnosti",
    
    # Capitalization
    "C.": "aktivace",
    
    # Personnel Costs
    "D.": "osobní_náklady",
    "D.1.": "mzdové_náklady",
    "D.2.": "náklady_na_sociální_zabezpečení_a_zdravotní_pojištění",
    "D.3.": "ostatní_náklady",
    
    # Operational Value Adjustments
    "E.": "úpravy_hodnot_v_provozní_oblasti",
    "E.1.": "úpravy_dlouhodobého_nehmotného_a_hmotného_majetku",
    "E.1.1.": "úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_trvalé",
    "E.1.2.": "úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_dočasné",
    "E.2.": "úpravy_zásob",
    "E.3.": "úpravy_pohledávek",
    
    # Other Operating Revenues
    "III.": "ostatní_provozní_výnosy",
    "III.1.": "tržby_z_prodaného_dlouhodobého_majetku",
    "III.2.": "tržby_z_prodaného_materiálu",
    "III.3.": "jiné_provozní_výnosy",
    
    # Other Operating Expenses
    "F.": "ostatní_provozní_náklady",
    "F.1.": "zůstatková_cena_prodaného_dlouhodobého_majetku",
    "F.2.": "prodaný_materiál",
    "F.3.": "daně_a_poplatky",
    "F.4.": "rezervy_v_provozní_oblasti",
    "F.5.": "jiné_provozní_náklady",
    
    # Operating Profit/Loss
    "*": "čistý_obrat",
    
    # Financial Revenues and Expenses
    "VI.": "výnosy_z_dlouhodobého_finančního_majetku",
    "VI.1.": "výnosy_z_podílů",
    "VI.1.1.": "výnosy_z_podílů_ovládaná_nebo_ovládající_osoba",
    "VI.1.2.": "ostatní_výnosy_z_podílů",
    "J.1.": "náklady_vynaložené_na_prodané_podíly",
    
    "VII.": "výnosy_z_ostatního_dlouhodobého_finančního_majetku",
    "VII.1.": "výnosy_z_ostatního_dlouhodobého_finančního_majetku_ovládaná_nebo_ovládající_osoba",
    "VII.2.": "ostatní_výnosy_z_ostatního_dlouhodobého_finančního_majetku",
    "J.2.": "náklady_související_s_ostatním_dlouhodobým_finančním_majetkem",
    
    "VIII.": "výnosové_úroky_a_podobné_výnosy",
    "VIII.1.": "výnosové_úroky_a_podobné_výnosy_ovládaná_nebo_ovládající_osoba",
    "VIII.2.": "ostatní_výnosové_úroky_a_podobné_výnosy",
    
    "K.": "úpravy_hodnot_a_rezervy_ve_finanční_oblasti",
    
    "L.": "nákladové_úroky_a_podobné_náklady",
    "L.1.": "nákladové_úroky_a_podobné_náklady_ovládaná_nebo_ovládající_osoba",
    "L.2.": "ostatní_nákladové_úroky_a_podobné_náklady",
    
    "X.": "ostatní_finanční_výnosy",
    "O.": "ostatní_finanční_náklady",
    
    # Financial Profit/Loss
    "* ": "finanční_výsledek_hospodaření",
    
    # Profit/Loss Before Taxation
    "**": "výsledek_hospodaření_před_zdaněním",
    
    # Income Tax
    "Q.": "daň_z_příjmů",
    "Q.1.": "daň_z_příjmů_splatná",
    "Q.2.": "daň_z_příjmů_odložená",
    
    # Profit/Loss After Taxation
    "** ": "výsledek_hospodaření_po_zdanění",
    "Q.3.": "převod_podílu_na_výsledku_hospodaření",
    "***": "výsledek_hospodaření_za_účetní_období",
    
    # Net Turnover, mám to tam 2x
    #"* ": "čistý_obrat_za_účetní_období",
}

def extract_text_from_pdf(pdf_filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "uzaverky", pdf_filename)
    
    with pdfplumber.open(pdf_path) as pdf:
        text_data = [page.extract_text() for page in pdf.pages if page.extract_text()]
        return "\n".join(text_data)

def extrahuj_ico(text):
    for line in text.split('\n'):
        if line.startswith("IČ:"):
            # Extract the ICO as a string, preserving leading zeros
            parts = line.split()
            if len(parts) > 1:
                return parts[1].strip()
    return None

def extrahuj_datum(text):
    for line in text.split('\n'):
        if "ke dni" in line:
            match = re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', line)
            if match:
                return match.group()
    return None

def detekuj_typ_rozvahy(text):
    if "ve zkráceném rozsahu" in text:
        return "zkrácená"
    elif "v plném rozsahu" in text:
        return "plná"
    return "zkrácená"

def extrahuj_data_řádku(radek, pocet_cisel):
    slova = radek.split()
    # Modified to preserve negative signs
    cisla = []
    for s in slova:
        try:
            # Convert string to integer while preserving negative signs
            cislo = int(s.replace(" ", ""))
            cisla.append(cislo)
        except ValueError:
            continue
            
    if len(cisla) < pocet_cisel:
        return None
        
    index_prvniho_cisla = next((i for i, s in enumerate(slova) if s.replace(" ", "").replace("-", "").isdigit()), -1)
    if index_prvniho_cisla == -1:
        return None
        
    kod_a_nazev = ' '.join(slova[:index_prvniho_cisla])
    match = re.match(r'([A-Z]+\.[IVX]*\.?|\*{1,3})', kod_a_nazev)
    if match:
        kod = match.group(1)
        return kod, cisla
    return None

def zpracuj_sekci(lines, mapa, pocet_cisel):
    data = {}
    for radek in lines:
        if not radek.strip():
            continue
        if "CELKEM" in radek:
            # Modified to preserve negative signs
            cisla = []
            for s in radek.split():
                try:
                    # Preserve negative signs when converting to int
                    cislo = int(s.replace(" ", ""))
                    cisla.append(cislo)
                except ValueError:
                    continue
            cisla = [c for c in cisla if c is not None]
            if pocet_cisel == 4:
                data["aktiva_celkem"] = {"brutto": cisla[0], "korekce": cisla[1], "netto": cisla[2], "netto_minulé": cisla[3]}
            elif pocet_cisel == 2:
                data["pasiva_celkem"] = {"běžné": cisla[0], "minulé": cisla[1]}
     
        else:
            extrahovane = extrahuj_data_řádku(radek, pocet_cisel)
            if extrahovane:
                kod, cisla = extrahovane
                if kod in mapa:
                    if pocet_cisel == 4:
                        data[mapa[kod]] = {"brutto": cisla[0], "korekce": cisla[1], "netto": cisla[2], "netto_minulé": cisla[3]}
                    elif pocet_cisel == 2:
                        data[mapa[kod]] = {"běžné": cisla[0], "minulé": cisla[1]}
            
        if "obrat" in radek.lower():
                print(radek)
                cisla = []
                for s in radek.split():
                    try:
                        # Convert string to integer while preserving negative signs
                        cislo = int(s.replace(" ", ""))
                        cisla.append(cislo)
                    except ValueError:
                        continue
                if len(cisla) >= 2:
                    data["obrat"] = {"běžné": cisla[0], "minulé": cisla[1]}
            
    return data

def zpracuj_uzaverku(pdf_filename):
    text = extract_text_from_pdf(pdf_filename)
    if not text:
        print("Nepodařilo se extrahovat text, pravděpodobně se jedná o obrázek")
        return

    # Extracting company details
    ico = extrahuj_ico(text)
    datum_str = extrahuj_datum(text)
    
    # Error handling for missing data
    if not ico:
        print("Nepodařilo se najít IČO, použije se výchozí hodnota.")
        ico = "NEURČENO"
    
    if not datum_str:
        print("Nepodařilo se najít datum, použije se aktuální datum.")
        datum_str = datetime.now().strftime("%d.%m.%Y")
    
    datum = datetime.strptime(datum_str, "%d.%m.%Y").date()

    # Detecting balance sheet type
    typ_rozvahy = detekuj_typ_rozvahy(text)
    lines = text.split('\n')

    # Dynamically finding sections with fallback mechanism
    index_aktiv = next((i for i, line in enumerate(lines) if "AKTIVA" in line), -1)
    index_pasiv = next((i for i, line in enumerate(lines) if "PASIVA" in line), -1)
    index_vzz = next((i for i, line in enumerate(lines) if any(klíč in line for klíč in ["Výkaz zisku", "Hospodaření", "Výnosy", "Náklady"])), -1)

    # Preparing variables for data
    data_aktiv = {}
    data_pasiv = {}
    data_vzz = {}

    # Processing sections based on availability
    try:
        if index_aktiv != -1 and index_pasiv != -1:
            data_aktiv_lines = lines[index_aktiv:index_pasiv]
            data_aktiv = zpracuj_sekci(data_aktiv_lines, mapa_aktiv, 4)
        else:
            print("Sekce AKTIV nenalezena.")

        if index_pasiv != -1 and (index_vzz == -1 or index_vzz > index_pasiv):
            data_pasiv_lines = lines[index_pasiv:index_vzz] if index_vzz != -1 else lines[index_pasiv:]
            data_pasiv = zpracuj_sekci(data_pasiv_lines, mapa_pasiv, 2)
        else:
            print("Sekce PASIV nenalezena.")

        if index_vzz != -1:
            data_vzz_lines = lines[index_vzz:]
            
            # Odstranit speciální zpracování čistého obratu
            for klíč, hodnota in mapa_vzz.items():
                matching_lines = [line for line in data_vzz_lines if klíč in line]
                if matching_lines:
                    try:
                        cisla = []
                        for s in matching_lines[0].split():
                            try:
                                cislo = int(s.replace(" ", ""))
                                cisla.append(cislo)
                            except ValueError:
                                continue
                        if len(cisla) >= 2:
                            data_vzz[hodnota] = {"běžné": cisla[0], "minulé": cisla[1]}
                    except Exception as e:
                        print(f"Chyba při zpracování {klíč}: {e}")
        else:
            print("Sekce Výkazu zisku a ztráty nenalezena.")

    except Exception as e:
        print(f"Obecná chyba při zpracování: {e}")
        print(traceback.format_exc())

    # Create AccountingData with safety checks
    accounting_data = AccountingData(
        ico=ico,
        běžné_účetní_období=datum,
        
        aktiva_celkem=data_aktiv.get("aktiva_celkem", {}).get("běžné"),
        stálá_aktiva=data_aktiv.get("stálá_aktiva", {}).get("běžné"),
        oběžná_aktiva=data_aktiv.get("oběžná_aktiva", {}).get("běžné"),
        dlouhodobý_nehmotný_majetek=data_aktiv.get("dlouhodobý_nehmotný_majetek", {}).get("běžné"),
        souftware=data_aktiv.get("software", {}).get("běžné"),
        dlouhodobý_hmotný_majetek=data_aktiv.get("dlouhodobý_hmotný_majetek", {}).get("běžné"),
        pozemky=data_aktiv.get("pozemky", {}).get("běžné"),
        stavby=data_aktiv.get("stavby", {}).get("běžné"),
        dlouhodobý_finanční_majetek=data_aktiv.get("dlouhodobý_finanční_majetek", {}).get("běžné"),
        zásoby=data_aktiv.get("zásoby", {}).get("běžné"),
        zboží=data_aktiv.get("zboží", {}).get("běžné"),
        pohledávky=data_aktiv.get("pohledávky", {}).get("běžné"),
        pohledávky_z_obchodních_vztahů=data_aktiv.get("pohledávky_z_obchodních_vztahů", {}).get("běžné"),
        krátkodobý_finanční_majetek=data_aktiv.get("krátkodobý_finanční_majetek", {}).get("běžné"),
        peněžní_prostředky_v_pokladně=data_aktiv.get("peněžní_prostředky_v_pokladně", {}).get("běžné"),
        peněžní_prostředky_na_účtech=data_aktiv.get("peněžní_prostředky_na_účtech", {}).get("běžné"),
        
        pasiva_celkem=data_pasiv.get("pasiva_celkem", {}).get("běžné"),
        vlastní_kapitál=data_pasiv.get("vlastní_kapitál", {}).get("běžné"),
        základní_kapitál= data_pasiv.get("základní_kapitál", {}).get("běžné"),
        kapitálové_fondy=data_pasiv.get("kapitálové_fondy", {}).get("běžné"),
        fondy_ze_zisku=data_pasiv.get("fondy_ze_zisku", {}).get("běžné"),
        výsledek_hospodaření_minulých_let=data_pasiv.get("výsledek_hospodaření_z_minulých_let", {}).get("běžné"),
        cizí_zdroje=data_pasiv.get("cizí_zdroje", {}).get("běžné"),
        dlouhodobé_závazky=data_pasiv.get("dlouhodobé_závazky", {}).get("běžné"),
        dlouhodobé_závazky_k_úvěrovým_institucím=data_pasiv.get("dlouhodobé_závazky_k_úvěrovým_institucím", {}).get("běžné"),
        dlouhodobé_závazky_z_obchodních_vztahů=data_pasiv.get("dlouhodobé_závazky_z_obchodních_vztahů", {}).get("běžné"),
        krátkodobé_závazky=data_pasiv.get("krátkodobé_závazky", {}).get("běžné"),
        krátkodobé_závazky_z_obchodních_vztahů=data_pasiv.get("krátkodobé_závazky_z_obchodních_vztahů", {}).get("běžné"),
        krátkodobé_závazky_k_zaměstnancům=data_pasiv.get("krátkodobé_závazky_k_zaměstnancům", {}).get("běžné"),
        krátkodobé_závazky_sociální_zabezpečení=data_pasiv.get("krátkodobé_závazky_sociální_zabezpečení", {}).get("běžné"),
        krátkodobé_daňové_závazky=data_pasiv.get("krátkodobé_daňové_závazky", {}).get("běžné"),
        # Financial Statement
        tržby_výrobky_služby=data_vzz.get("tržby_výrobky_služby", {}).get("běžné"),
        tržby_za_prodej_zboží=data_vzz.get("tržby_za_prodej_zboží", {}).get("běžné"),
        výkonová_spotřeba=data_vzz.get("výkonová_spotřeba", {}).get("běžné"),
        náklady_vynaložené_na_prodané_zboží=data_vzz.get("náklady_vynaložené_na_prodané_zboží", {}).get("běžné"),
        spotřeba_materiálu_a_energie=data_vzz.get("spotřeba_materiálu_a_energie", {}).get("běžné"),
        služby=data_vzz.get("služby", {}).get("běžné"),
        změna_stavu_zásob_vlastní_činnosti=data_vzz.get("změna_stavu_zásob_vlastní_činnosti", {}).get("běžné"),
        aktivace=data_vzz.get("aktivace", {}).get("běžné"),
        osobní_náklady=data_vzz.get("osobní_náklady", {}).get("běžné"),
        mzdové_náklady=data_vzz.get("mzdové_náklady", {}).get("běžné"),
        náklady_na_sociální_zabezpečení_a_zdravotní_pojištění=data_vzz.get("náklady_na_sociální_zabezpečení_a_zdravotní_pojištění", {}).get("běžné"),
        ostatní_náklady=data_vzz.get("ostatní_náklady", {}).get("běžné"),
        úpravy_hodnot_v_provozní_oblasti=data_vzz.get("úpravy_hodnot_v_provozní_oblasti", {}).get("běžné"),
        úpravy_dlouhodobého_nehmotného_a_hmotného_majetku=data_vzz.get("úpravy_dlouhodobého_nehmotného_a_hmotného_majetku", {}).get("běžné"),
        úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_trvalé=data_vzz.get("úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_trvalé", {}).get("běžné"),
        úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_dočasné=data_vzz.get("úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_dočasné", {}).get("běžné"),
        úpravy_zásob=data_vzz.get("úpravy_zásob", {}).get("běžné"),
        úpravy_pohledávek=data_vzz.get("úpravy_pohledávek", {}).get("běžné"),
        ostatní_provozní_výnosy=data_vzz.get("ostatní_provozní_výnosy", {}).get("běžné"),
        tržby_z_prodaného_dlouhodobého_majetku=data_vzz.get("tržby_z_prodaného_dlouhodobého_majetku", {}).get("běžné"),
        tržby_z_prodaného_materiálu=data_vzz.get("tržby_z_prodaného_materiálu", {}).get("běžné"),
        jiné_provozní_výnosy=data_vzz.get("jiné_provozní_výnosy", {}).get("běžné"),
        ostatní_provozní_náklady=data_vzz.get("ostatní_provozní_náklady", {}).get("běžné"),
        zůstatková_cena_prodaného_dlouhodobého_majetku=data_vzz.get("zůstatková_cena_prodaného_dlouhodobého_majetku", {}).get("běžné"),
        prodaný_materiál=data_vzz.get("prodaný_materiál", {}).get("běžné"),
        daně_a_poplatky=data_vzz.get("daně_a_poplatky", {}).get("běžné"),
        rezervy_v_provozní_oblasti=data_vzz.get("rezervy_v_provozní_oblasti", {}).get("běžné"),
        jiné_provozní_náklady=data_vzz.get("jiné_provozní_náklady", {}).get("běžné"),
        čistý_obrat=data_vzz.get("čistý_obrat", {}).get("běžné"),
        výnosy_z_dlouhodobého_finančního_majetku=data_vzz.get("výnosy_z_dlouhodobého_finančního_majetku", {}).get("běžné"),
        výnosy_z_ostaního_dlouhodobého_finančního_majetku_nebo_ovládající_osoba=data_vzz.get("výnosy_z_ostaního_dlouhodobého_finančního_majetku_nebo_ovládající_osoba", {}).get("běžné"),
        ostatní_výnosy_z_ostatního_dlouhodobého_finančního_majetku=data_vzz.get("ostatní_výnosy_z_ostatního_dlouhodobého_finančního_majetku", {}).get("běžné"),
        náklady_související_s_ostatním_dlouhodobým_finančním_majetkem=data_vzz.get("náklady_související_s_ostatním_dlouhodobým_finančním_majetkem", {}).get("běžné"),
        výnosové_úroky_a_podobné_výnosy=data_vzz.get("výnosové_úroky_a_podobné_výnosy", {}).get("běžné"),
        výnosové_úroky_a_podobné_výnosy_ovládané_nebo_ovládající_osoba=data_vzz.get("výnosové_úroky_a_podobné_výnosy_ovládané_nebo_ovládající_osoba", {}).get("běžné"),
        nákladové_úroky_a_podobné_náklady_ovládaná_nebo_ovládající_osoba=data_vzz.get("nákladové_úroky_a_podobné_náklady_ovládaná_nebo_ovládající_osoba", {}).get("běžné"),
        ostatní_výnosové_úroky_a_podobné_výnosy=data_vzz.get("ostatní_výnosové_úroky_a_podobné_výnosy", {}).get("běžné"),
        úpravy_hodnot_a_rezervy_ve_finanční_oblasti=data_vzz.get("úpravy_hodnot_a_rezervy_ve_finanční_oblasti", {}).get("běžné"),
        nákladové_úroky_a_podobné_náklady=data_vzz.get("nákladové_úroky_a_podobné_náklady", {}).get("běžné"),
        ostatní_nákladové_úroky_a_podobné_náklady=data_vzz.get("ostatní_nákladové_úroky_a_podobné_náklady", {}).get("běžné"),
        ostatní_finanční_výnosy=data_vzz.get("ostatní_finanční_výnosy", {}).get("běžné"),
        ostatní_finanční_náklady=data_vzz.get("ostatní_finanční_náklady", {}).get("běžné"),
        finanční_výsledek_hospodaření=data_vzz.get("finanční_výsledek_hospodaření", {}).get("běžné"),
        výsledek_hospodaření_před_zdaněním=data_vzz.get("výsledek_hospodaření_před_zdaněním", {}).get("běžné"),
        daň_z_příjmů=data_vzz.get("daň_z_příjmů", {}).get("běžné"),
        daň_z_příjmů_splatná=data_vzz.get("daň_z_příjmů_splatná", {}).get("běžné"),
        daň_z_příjmů_odložená=data_vzz.get("daň_z_příjmů_odložená", {}).get("běžné"),
        výsledek_hospodaření_po_zdanění=data_vzz.get("výsledek_hospodaření_po_zdanění", {}).get("běžné"),
        převod_podílu_na_výsledku_hospodaření=data_vzz.get("převod_podílu_na_výsledku_hospodaření", {}).get("běžné"),
        výsledek_hospodaření_za_účetní_období=data_vzz.get("výsledek_hospodaření_za_účetní_období", {}).get("běžné"),
        čistý_obrat_za_účetní_období=data_vzz.get("čistý_obrat_za_účetní_období", {}).get("běžné"),
    )

    # Uložení do databáze
    db_conn = DatabaseConnection()
    session = db_conn.get_session()
    
    try:
        session.add(accounting_data)
        session.commit()
        print(f"Data pro IČO {ico} a datum {datum} úspěšně uložena do databáze.")
    except Exception as e:
        session.rollback()
        print(f"Chyba při ukládání dat do databáze: {e}")
        print(traceback.format_exc())
    finally:
        session.close()

    return accounting_data

# Spuštění
zpracuj_uzaverku("24239445_30_3_2025.pdf")