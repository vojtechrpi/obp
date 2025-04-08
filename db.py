from sqlalchemy import create_engine, Column, String, Integer, Date, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker 

Base = declarative_base()

class AresData(Base):
    __tablename__ = 'ares_data'
    
    ico = Column(String(20), primary_key=True)
    obchodni_jmeno = Column(Text)
    datum_platnosti = Column(Date)
    statisticka_pravni_forma_kod = Column(Integer)
    statisticka_pravni_forma_nazev = Column(Text)
    velikostni_kategorie_kod = Column(Integer)
    velikostni_kategorie_nazev = Column(Text)
    institucionalni_sektor_kod = Column(Integer)
    institucionalni_sektor_nazev = Column(Text)
    kraj_kod = Column(String(10))
    kraj_nazev = Column(Text)
    okres_kod = Column(String(10))
    okres_nazev = Column(Text)
    obec_kod = Column(Integer)
    obec_nazev = Column(Text)
    adresa_sidla = Column(Text)
    datum_vzniku = Column(Date)
    datum_zaniku = Column(Date)
    zpusob_zaniku_kod = Column(Integer)
    zpusob_zaniku_nazev = Column(Text)
    priznak = Column(Text)
    hlavni_nace_kod = Column(String(10))
    hlavni_nace_nazev = Column(Text)
    
    def __repr__(self):
        return f"<AresData(ico='{self.ico}', obchodni_jmeno='{self.obchodni_jmeno}')>"


class AccountingData(Base):
    __tablename__ = 'accounting_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ico = Column(String(20), ForeignKey('ares_data.ico'), nullable=False)
    běžné_účetní_období = Column(Date, nullable=False)
    
    # AKTIVA - Balance Sheet (Assets)
    aktiva_celkem = Column(Float, nullable=True)
    stálá_aktiva = Column(Float, nullable=True)
    oběžná_aktiva = Column(Float, nullable=True)
    dlouhodobý_nehmotný_majetek = Column(Float, nullable=True)
    souftware = Column(Float, nullable=True)
    dlouhodobý_hmotný_majetek = Column(Float, nullable=True)
    pozemky = Column(Float, nullable=True)
    stavby = Column(Float, nullable=True)
    dlouhodobý_finanční_majetek = Column(Float, nullable=True)
    zásoby = Column(Float, nullable=True)
    zboží = Column(Float, nullable=True)
    pohledávky = Column(Float, nullable=True)
    pohledávky_z_obchodních_vztahů = Column(Float, nullable=True)
    krátkodobý_finanční_majetek = Column(Float, nullable=True)
    peněžní_prostředky_v_pokladně = Column(Float, nullable=True)
    peněžní_prostředky_na_účtech = Column(Float, nullable=True)
    
    # PASIVA - Balance Sheet (Liabilities & Equity)

    pasiva_celkem = Column(Float, nullable=True)
    vlastní_kapitál = Column(Float, nullable=True)
    základní_kapitál = Column(Float, nullable=True)
    kapitálové_fondy = Column(Float, nullable=True)
    fondy_ze_zisku = Column(Float, nullable=True)
    výsledek_hospodaření_minulých_let = Column(Float, nullable=True)
    cizí_zdroje = Column(Float, nullable=True)
    dlouhodobé_závazky = Column(Float, nullable=True)
    dlouhodobé_závazky_k_úvěrovým_institucím = Column(Float, nullable=True)
    dlouhodobé_závazky_z_obchodních_vztahů = Column(Float, nullable=True)
    krátkodobé_závazky = Column(Float, nullable=True)
    krátkodobé_závazky_z_obchodních_vztahů = Column(Float, nullable=True)
    krátkodobé_závazky_k_zaměstnancům = Column(Float, nullable=True)
    krátkodobé_závazky_sociální_zabezpečení = Column(Float, nullable=True)
    krátkodobé_daňové_závazky = Column(Float, nullable=True)

    # VÝKAZ ZISKU A ZTRÁTY - Income Statement
    # I. Tržby z prodeje výrobků a služeb (Sales of Products and Services)
    tržby_výrobky_služby = Column(Float, nullable=True)
    tržby_za_prodej_zboží = Column(Float, nullable=True)
    výkonová_spotřeba = Column(Float, nullable=True)
    náklady_vynaložené_na_prodané_zboží = Column(Float, nullable=True)
    spotřeba_materiálu_a_energie = Column(Float, nullable=True)
    služby = Column(Float, nullable=True)
    změna_stavu_zásob_vlastní_činnosti = Column(Float, nullable=True)
    aktivace = Column(Float, nullable=True)
    osobní_náklady = Column(Float, nullable=True)
    mzdové_náklady = Column(Float, nullable=True)
    náklady_na_sociální_zabezpečení_a_zdravotní_pojištění = Column(Float, nullable=True)
    ostatní_náklady = Column(Float, nullable=True)
    úpravy_hodnot_v_provozní_oblasti = Column(Float, nullable=True)    
    úpravy_dlouhodobého_nehmotného_a_hmotného_majetku = Column(Float, nullable=True)
    úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_trvalé = Column(Float, nullable=True)
    úpravy_dlouhodobého_nehmotného_a_hmotného_majetku_dočasné = Column(Float, nullable=True)
    úpravy_zásob = Column(Float, nullable=True)
    úpravy_pohledávek = Column(Float, nullable=True)
    ostatní_provozní_výnosy = Column(Float, nullable=True)
    tržby_z_prodaného_dlouhodobého_majetku = Column(Float, nullable=True)
    tržby_z_prodaného_materiálu = Column(Float, nullable=True)
    jiné_provozní_výnosy = Column(Float, nullable=True)
    ostatní_provozní_náklady = Column(Float, nullable=True)
    zůstatková_cena_prodaného_dlouhodobého_majetku = Column(Float, nullable=True)
    prodaný_materiál = Column(Float, nullable=True)
    daně_a_poplatky = Column(Float, nullable=True)
    rezervy_v_provozní_oblasti = Column(Float, nullable=True)
    jiné_provozní_náklady = Column(Float, nullable=True)
    čistý_obrat = Column(Float, nullable=True)
    výnosy_z_dlouhodobého_finančního_majetku = Column(Float, nullable=True)
    výnosy_z_ostaního_dlouhodobého_finančního_majetku_nebo_ovládající_osoba = Column(Float, nullable=True)
    ostatní_výnosy_z_ostatního_dlouhodobého_finančního_majetku = Column(Float, nullable=True)
    náklady_související_s_ostatním_dlouhodobým_finančním_majetkem = Column(Float, nullable=True)
    výnosové_úroky_a_podobné_výnosy= Column(Float, nullable=True)
    výnosové_úroky_a_podobné_výnosy_ovládané_nebo_ovládající_osoba = Column(Float, nullable=True)
    nákladové_úroky_a_podobné_náklady_ovládaná_nebo_ovládající_osoba = Column(Float, nullable=True)
    ostatní_výnosové_úroky_a_podobné_výnosy = Column(Float, nullable=True)
    úpravy_hodnot_a_rezervy_ve_finanční_oblasti = Column(Float, nullable=True)
    nákladové_úroky_a_podobné_náklady = Column(Float, nullable=True)
    nákladové_úroky_a_podobné_náklady_ovládaná_nebo_ovládající_osoba = Column(Float, nullable=True)
    ostatní_nákladové_úroky_a_podobné_náklady = Column(Float, nullable=True)
    ostatní_finanční_výnosy = Column(Float, nullable=True)
    ostatní_finanční_náklady = Column(Float, nullable=True)
    finanční_výsledek_hospodaření = Column(Float, nullable=True)
    výsledek_hospodaření_před_zdaněním = Column(Float, nullable=True)
    daň_z_příjmů = Column(Float, nullable=True)
    daň_z_příjmů_splatná = Column(Float, nullable=True)
    daň_z_příjmů_odložená = Column(Float, nullable=True)
    výsledek_hospodaření_po_zdanění = Column(Float, nullable=True)
    převod_podílu_na_výsledku_hospodaření = Column(Float, nullable=True)
    výsledek_hospodaření_za_účetní_období = Column(Float, nullable=True)
    čistý_obrat_za_účetní_období = Column(Float, nullable=True)   #Mám to tam 2x
    
    def __repr__(self):
        return f"<AccountingData(ico='{self.ico}', běžné_účetní_období='{self.běžné_účetní_období}', výsledek_hospodaření_za_účetní_období='{self.výsledek_hospodaření_za_účetní_období}')>"
    
class WebData(Base):
    __tablename__ = 'web_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Unikátní ID záznamu
    ico = Column(String(20), ForeignKey('ares_data.ico'), nullable=False)  # Cizí klíč na AresData
    url = Column(Text)  # URL webové stránky
    
    def __repr__(self):
        return f"<WebData(ico='{self.ico}', url='{self.url}')>"

class EmployeeCountMapping(Base):
    __tablename__ = 'employee_count_mapping'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Unikátní ID záznamu
    interval_zamestnancu = Column(String(50), unique=True, nullable=False)  # Textový popis intervalu (např. "20 – 24 zaměstnanců")
    max_pocet_zamestnancu = Column(Integer, nullable=True)  # Nejvyšší hodnota z intervalu (např. 24), pro "Ne uvedeno" bude NULL
    
    def __repr__(self):
        return f"<EmployeeCountMapping(interval_zamestnancu='{self.interval_zamestnancu}', max_pocet_zamestnancu={self.max_pocet_zamestnancu})>"

class DatabaseConnection:
    _instance = None
    _engine = None
    _session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._engine = create_engine('postgresql://postgres:postgres@localhost/postgres')
            Base.metadata.create_all(cls._engine)
            Session = sessionmaker(bind=cls._engine)
            cls._session = Session()
        return cls._instance

    @classmethod
    def get_session(cls):
        return cls._session