from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import re
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import DatabaseConnection, AresData, WebData

# Inicializace připojení k databázi
db = DatabaseConnection()
session = db.get_session()

# Funkce pro náhodné čekání
def random_sleep(min_sec=1, max_sec=3):
    """Náhodné čekání mezi požadavky"""
    time.sleep(random.uniform(min_sec, max_sec))

def setup_driver(proxy=None):
    """Nastavení a inicializace webdriveru s možností Tor proxy"""
    firefox_options = webdriver.FirefoxOptions()
    # firefox_options.add_argument("--headless")  # Odkomentujte pro headless režim
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
    ]
    firefox_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    if proxy and proxy.startswith("socks5://"):
        try:
            host, port = proxy.replace("socks5://", "").split(":")
            firefox_options.set_preference("network.proxy.type", 1)
            firefox_options.set_preference("network.proxy.socks", host)
            firefox_options.set_preference("network.proxy.socks_port", int(port))
            firefox_options.set_preference("network.proxy.socks_version", 5)
            print(f"Používám Tor proxy: {proxy}")
        except Exception as e:
            print(f"Chyba při nastavení Tor proxy {proxy}: {e}")
    
    try:
        driver = webdriver.Firefox(options=firefox_options)
        return driver
    except Exception as e:
        print(f"Chyba při inicializaci webdriveru: {e}")
        return None
    
def setup_local_tor_proxy():
    """
    Nastaví lokální Tor proxy a vrátí adresu proxy.
    Primárně kontroluje Tor Browser na portu 9150.
    
    Returns:
        str: Adresa proxy ve formátu "socks5://127.0.0.1:9150"
    """
    import socket
    import time
    import subprocess
    
    # Hlavní port pro Tor Browser je 9150
    tor_browser_port = 9150
    
    print("Kontroluji dostupnost Tor Browser proxy...")
    
    # Kontrola, zda je Tor Browser proxy dostupný
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    result = s.connect_ex(('127.0.0.1', tor_browser_port))
    s.close()
    
    if result == 0:
        print(f"Tor Browser proxy je dostupný na portu {tor_browser_port}")
        return f"socks5://127.0.0.1:{tor_browser_port}"
    else:
        print(f"Tor Browser proxy není dostupný na portu {tor_browser_port}")
        print("Ujistěte se, že je Tor Browser spuštěn před použitím tohoto programu.")
        
        # Zkusíme ještě standardní Tor port
        standard_tor_port = 9050
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex(('127.0.0.1', standard_tor_port))
        s.close()
        
        if result == 0:
            print(f"Standardní Tor proxy je dostupný na portu {standard_tor_port}")
            return f"socks5://127.0.0.1:{standard_tor_port}"
        
        print("Tor proxy není dostupný. Prosím, spusťte Tor Browser a zkuste to znovu.")
        return None

def get_new_tor_identity():
    """
    Požádá Tor o novou identitu (novou IP adresu).
    Vyžaduje přístup k Tor Control Port.
    
    Returns:
        bool: True pokud se podařilo získat novou identitu, jinak False
    """
    import socket
    import time
    
    # Výchozí nastavení Tor Control Port
    control_port = 9151
    password = ""  # Heslo pro Control Port, pokud je nastaveno
    
    try:
        # Připojení k Tor Control Port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', control_port))
        
        # Autentizace, pokud je nastaveno heslo
        if password:
            auth_cmd = f'AUTHENTICATE "{password}"\r\n'.encode()
            s.send(auth_cmd)
            response = s.recv(1024).decode()
            if not response.startswith("250"):
                print(f"Chyba při autentizaci: {response}")
                s.close()
                return False
        
        # Požadavek na novou identitu
        s.send(b'SIGNAL NEWNYM\r\n')
        response = s.recv(1024).decode()
        s.close()
        
        if response.startswith("250"):
            print("Úspěšně získána nová Tor identita")
            # Počkáme chvíli, aby se změna projevila
            time.sleep(5)
            return True
        else:
            print(f"Chyba při získávání nové Tor identity: {response}")
            return False
            
    except Exception as e:
        print(f"Chyba při komunikaci s Tor Control Port: {e}")
        print("Ujistěte se, že máte správně nakonfigurovaný Tor Control Port")
        return False

# Upravíme třídu ProxyRotator
class ProxyRotator:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.proxy_stats = {}
        self.use_tor = False
        self.tor_proxy = None
        
    def setup_proxies(self, use_tor=True):
        """Nastaví Tor proxy server"""
        self.proxies = []
        
        if use_tor:
            self.use_tor = True
            self.tor_proxy = setup_local_tor_proxy()
            if self.tor_proxy:
                self.proxies.append(self.tor_proxy)
        
        self.proxy_stats = {proxy: {"success": 0, "failure": 0} for proxy in self.proxies}
        
        if not self.proxies:
            print("Varování: Tor proxy není dostupný")
            return False
            
        print(f"Nakonfigurován Tor proxy: {self.tor_proxy}")
        return True
        
    def get_next_proxy(self):
        """Vrátí Tor proxy a případně požádá o novou identitu"""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        if self.use_tor and proxy == self.tor_proxy and self.current_index == 0:
            get_new_tor_identity()
            
        return proxy
        
    def report_success(self, proxy):
        """Zaznamená úspěšné použití proxy"""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]["success"] += 1
            
    def report_failure(self, proxy):
        """Zaznamená neúspěšné použití proxy"""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]["failure"] += 1
            
    def get_stats(self):
        """Vrátí statistiky použití proxy"""
        return self.proxy_stats
    
def detect_captcha(driver):
    """Detekuje, zda jsme narazili na CAPTCHA"""
    # Různé způsoby detekce CAPTCHA na Google
    captcha_indicators = [
        "//form[contains(@action, 'sorry')]",  # Google's "Sorry..." page
        "//input[@id='captcha']",
        "//img[contains(@src, 'captcha')]",
        "//div[contains(text(), 'captcha')]",
        "//div[contains(text(), 'Captcha')]",
        "//div[contains(text(), 'CAPTCHA')]",
        "//div[contains(text(), 'reCAPTCHA')]",
        "//div[contains(text(), 'robot')]",
        "//iframe[contains(@src, 'recaptcha')]"
    ]
    
    for indicator in captcha_indicators:
        try:
            if driver.find_elements(By.XPATH, indicator):
                return True
        except:
            pass
    
    # Kontrola URL, která může obsahovat "sorry", "challenge" apod.
    current_url = driver.current_url
    if "sorry" in current_url or "captcha" in current_url or "challenge" in current_url:
        return True
        
    return False

def wait_for_captcha_solution(driver):
    """Čeká na ruční vyřešení CAPTCHA"""
    print("\n" + "="*50)
    print("DETEKOVÁNA CAPTCHA! Vyřešte ji ručně v otevřeném prohlížeči.")
    print("Až budete hotovi, stiskněte Enter pro pokračování...")
    print("="*50 + "\n")
    
    input("Stiskněte Enter po vyřešení CAPTCHA...")
    
    # Kontrola, zda byla CAPTCHA vyřešena
    if detect_captcha(driver):
        print("CAPTCHA stále detekována. Zkusíme počkat ještě chvíli...")
        time.sleep(3)
        if detect_captcha(driver):
            print("CAPTCHA nebyla vyřešena správně, zkusíme přeskočit aktuální firmu.")
            return False
    
    print("CAPTCHA úspěšně vyřešena, pokračujeme...")
    return True

def normalize_text(text):
    # Převede text na malá písmena a odstraní interpunkci
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

def find_company_website_google(driver, company_name, proxy_rotator=None, current_proxy=None):
    """Hledání webové stránky firmy pomocí Google - bere první 3 výsledky a vybere nejpodobnější"""
    if not company_name:
        return None
    
    # Kontrola, zda driver není None
    if driver is None:
        print("Webdriver není inicializován, nemohu vyhledat webovou stránku.")
        return None
        
    # Použití celého názvu firmy v dotazu
    search_query = f'"{company_name}" web'  # Použití uvozovek pro přesné vyhledávání
    url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
    
    try:
        driver.get(url)
        random_sleep(2, 4)
        
        # Kontrola CAPTCHA
        if detect_captcha(driver):
            if not wait_for_captcha_solution(driver):
                # CAPTCHA nebyla vyřešena, zkusíme změnit proxy, pokud je k dispozici
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_failure(current_proxy)
                    print("Měníme proxy a zkusíme znovu...")
                    return None
            else:
                # CAPTCHA byla vyřešena, pokračujeme
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_success(current_proxy)
        
        # Rozšířené selektory pro hledání výsledků
        selectors = [
            "div.g a[href^='http']",  # Standardní výsledky
            "div.yuRUbf a[href^='http']",  # Novější formát Google
            ".LC20lb", # Názvy výsledků
            "a[jsname]", # Další možný selector
            "a[data-ved]", # Ještě další selector
            "div.tF2Cxc a", # Dodatečný selector
            "h3.LC20lb + div + a", # Zkusíme najít odkaz poblíž nadpisu
            ".kCrYT a", # Mobilní verze
            "a[ping]", # Linky s ping atributem (Google často používá)
            "div[jscontroller] a[href^='http']", # Obecnější selector
            "a[href^='http']" # Nejobecnější selector - použijeme jako poslední možnost
        ]
        
        # Rozšířený seznam blokovaných domén
        blocked_domains = [
            'facebook', 'twitter', 'instagram', 'linkedin', 'google', 'youtube.com', "youtube.cz", "echo24.cz", "seznamzpravy.cz",
            'wikipedia', 'reddit', 'pinterest', 'tumblr', 'flickr', 'vimeo', 'dailymotion', 'soundcloud', 'twitch', 'tiktok', 'snapchat', "lupa.cz",
            'gov.cz', 'justice.cz', 'zivefirmy.cz', 'firmy.cz', 'katalog-firem.cz', "kurzy.cz", "businessinfo.cz", "penize.cz",
            'ares.cz', 'rejstrik-firem.cz', 'rejstrik.penize.cz', 'edb.cz', "mesec.cz", "infoprovest.cz", "atmoskop.cz",
            'seznam.cz', 'idnes.cz', 'novinky.cz', 'ihned.cz', 'aktualne.cz', 'blesk.cz', 'reflex.cz', 'lidovky.cz', "ceskestavby.cz",
            'e15.cz', 'denik.cz', 'tyden.cz', 'zpravy.aktualne.cz', 'zpravy.idnes.cz', 'zpravy.ihned.cz', 'zpravy.blesk.cz', 'zpravy.reflex.cz',
            'obchodnirejstrik.cz', 'databox.cz', 'firmycz.cz', 'podnikatel.cz', "transparex.cz", "vut.cz", "vse.cz", "karaoketexty.cz",
            'mistoprodeje.cz', 'hledamefirmy.cz', 'zlatestranky.cz', 'zlutyodjezd.cz', "obchodnirejstrik.podnikani.cz", "expanzo.com",
            'najisto.cz', 'adresarfirem.cz', 'info-firmy.cz', 'empatica.cz', "rejstrik-firem.kurzy.cz", "hlidacstatu.cz",
            "finstat.cz", "finstat.sk", "slovnik-cizich-slov.cz", "slovnik-cizich-slov.cz", "slovnik-cizich-slov.cz", "jenprace.cz",
            "slovnik-cizich-slov.cz", "slovnik-cizich-slov.cz", "slovnik-cizich-slov.cz", "slovnik-cizich-slov.cz", "www.detail.cz",
            "slovnik-cizich-slov.abz.cz", "slovnik-cizich-slov.cz", "slovnik-cizich-slov.net","wikipeida.cz", "finmag.cz", "cs.wikipedia.cz",
            "cs.wikipedia.org", "cs.wikipedia.net", "cs.wikipedia.com", "cs.wikipedia.info", "cs.wikipedia.eu", "transparex.sk", "cs.wikipedia.gov",
            "cs.wikipedia.edu", "cs.wikipedia.co.uk", "cs.wikipedia.de", "karaoketexty.cz", "ekatalog.cz", "generaliceska.cz", "seznamit.cz", "foaf.sk","cs.wikipedia.fr", "cs.wikipedia.it", "cs.wikipedia.pl",
        ]
        
        # Najdeme všechny potenciální výsledky pomocí různých selektorů
        potential_sites = []
        for selector in selectors:
            try:
                results = driver.find_elements(By.CSS_SELECTOR, selector)
                for result in results:
                    href = result.get_attribute("href")
                    # Zkontrolujeme, že URL je platná a není již v seznamu
                    if href and href.startswith("http") and href not in potential_sites:
                        # Filtrujeme blokované domény
                        if not any(domain in href.lower() for domain in blocked_domains):
                            potential_sites.append(href)
            except Exception as e:
                print(f"Chyba při použití selektoru {selector}: {e}")
                continue
        
        # Omezíme počet kandidátů na prvních 5
        potential_sites = potential_sites[:5]
        
        # Vypíšeme kandidáty pro debugging
        print(f"Potenciální weby pro '{company_name}':")
        for i, site in enumerate(potential_sites):
            print(f"  {i+1}. {site}")
        
        # Vybereme nejpodobnější stránku podle názvu firmy
        if potential_sites:
            company_name_normalized = normalize_text(company_name)
            best_match = None
            best_score = 0
            
            for site in potential_sites:
                try:
                    # Extrahujeme doménu z URL
                    domain_match = re.findall(r'https?://(?:www\.)?([^/]+)', site)
                    if not domain_match:
                        continue
                    
                    domain = domain_match[0]
                    domain_normalized = normalize_text(domain)
                    
                    # Počítáme skóre shody - jednoduchá metoda
                    score = 0
                    
                    # Přímá shoda s názvem firmy v doméně
                    if company_name_normalized in domain_normalized:
                        score += 10
                    
                    # Částečná shoda - hledáme jednotlivá slova
                    company_words = company_name_normalized.split()
                    for word in company_words:
                        if len(word) > 2 and word in domain_normalized:  # Ignorujeme krátká slova
                            score += 3
                    
                    print(f"    Skóre pro {domain}: {score}")
                    
                    # Pokud je toto nejlepší skóre zatím, zapamatujeme si ho
                    if score > best_score:
                        best_score = score
                        best_match = site
                except Exception as e:
                    print(f"Chyba při vyhodnocení domény: {e}")
                    continue
            
            # Vrátíme nejlepší shodu, nebo první výsledek, pokud nic nenajdeme
            if best_match and best_score > 0:
                print(f"Nejlepší shoda: {best_match} (skóre: {best_score})")
                return best_match
            elif potential_sites:
                print(f"Žádná dobrá shoda, vracím první výsledek: {potential_sites[0]}")
                return potential_sites[0]
        else:
            print(f"Pro firmu '{company_name}' nebyly nalezeny žádné potenciální weby.")
            return None
    
    except Exception as e:
        print(f"Chyba při hledání webu na Google pro firmu '{company_name}': {e}")
        if proxy_rotator and current_proxy:
            proxy_rotator.report_failure(current_proxy)
    
    return None

def process_company(driver, company, proxy_rotator=None, current_proxy=None):
    """Zpracování jedné firmy - pouze vyhledáním na Google"""
    ico = company.ico
    company_name = company.obchodni_jmeno
    
    if not company_name:
        print(f"Pro IČO {ico} není uvedeno obchodní jméno, přeskakuji.")
        return None
        
    print(f"Zpracovávám firmu: {company_name} (IČO: {ico})")
    
    # Kontrola, zda už nemáme web v databázi
    existing_web = session.query(WebData).filter_by(ico=ico).first()
    if existing_web and existing_web.url:
        print(f"Web pro IČO {ico} již existuje v databázi: {existing_web.url}")
        return existing_web.url
    
    # Kontrola, zda driver není None
    if driver is None:
        print("Webdriver není inicializován, nelze zpracovat firmu.")
        return None
    
    # Hledáme web přímo na Google
    website = find_company_website_google(driver, company_name, proxy_rotator, current_proxy)
    
    # Uložení do databáze
    if website:
        print(f"Nalezen web pro IČO {ico}: {website}")
        if existing_web:
            existing_web.url = website
        else:
            web_data = WebData(ico=ico, url=website)
            session.add(web_data)
        
        session.commit()
    else:
        print(f"Web pro firmu '{company_name}' (IČO {ico}) nebyl nalezen")
        # Přesto vytvoříme záznam s prázdnou URL, abychom věděli, že jsme tuto firmu již zpracovali
        if not existing_web:
            web_data = WebData(ico=ico, url=None)
            session.add(web_data)
            session.commit()
    
    return website

def main():
    """Hlavní funkce skriptu"""
    companies = session.query(AresData).join(
        WebData, AresData.ico == WebData.ico, isouter=True
    ).filter(
        (WebData.ico == None) & (AresData.obchodni_jmeno != None)
    ).limit(50).all()
    
    if not companies:
        print("V databázi nejsou žádné firmy bez webu nebo všechny firmy již byly zpracovány!")
        return
    
    print(f"Nalezeno {len(companies)} firem v databázi, které zatím nemají přiřazený web")
    
    proxy_rotator = ProxyRotator()
    
    print("\nVyberte režim práce:")
    print("1 - Lokální připojení (bez proxy)")
    print("2 - Použít lokální Tor proxy pro rotaci IP")
    
    choice = input("Zadejte číslo (výchozí: 1): ") or "1"
    
    use_tor = False
    
    if choice == "2":
        use_tor = True
        proxy_rotator.setup_proxies(use_tor=True)
    elif choice != "1":
        print("Neplatná volba, používám výchozí lokální připojení.")
    
    if use_tor and not proxy_rotator.proxies:
        print("Tor proxy není k dispozici. Používám lokální připojení.")
        use_tor = False
    
    input("\nStiskněte Enter pro spuštění programu...")
    
    requests_count = 0
    captcha_count = 0
    success_count = 0
    
    current_proxy = None
    driver = None
    
    try:
        for company in companies:
            if requests_count > 0 and requests_count % 5 == 0:
                print(f"\nStatistika: {requests_count} požadavků, {captcha_count} CAPTCHA, {success_count} úspěchů")
                print(f"Míra úspěšnosti: {success_count/requests_count*100:.1f}%")
                
                if captcha_count > 2:
                    print("Detekováno příliš mnoho CAPTCHA, možná jsme blokováni.")
                    if use_tor:
                        if driver:
                            driver.quit()
                            driver = None
                        captcha_count = 0
                        if current_proxy == proxy_rotator.tor_proxy:
                            get_new_tor_identity()
                        current_proxy = proxy_rotator.get_next_proxy()
                        print(f"Měním proxy na: {current_proxy}")
                        driver = setup_driver(current_proxy)
                    else:
                        wait_time = random.randint(60, 120)
                        print(f"Čekám {wait_time} sekund před dalším pokusem...")
                        time.sleep(wait_time)
            
            if driver is None:
                if use_tor:
                    current_proxy = proxy_rotator.get_next_proxy()
                    print(f"Používám proxy: {current_proxy}")
                    driver = setup_driver(current_proxy)
                else:
                    driver = setup_driver()
                
                if driver is None:
                    print("Nepodařilo se inicializovat webdriver. Přeskakuji aktuální firmu.")
                    continue
            
            requests_count += 1
            website = process_company(driver, company, proxy_rotator, current_proxy)
            
            if website:
                success_count += 1
            
            if driver and detect_captcha(driver):
                captcha_count += 1
            
            random_sleep(3, 10)
        
        print("\nZpracování dokončeno! Výsledky:")
        results = session.query(WebData).filter(WebData.ico.in_([c.ico for c in companies])).all()
        for result in results:
            print(f"IČO: {result.ico}, Web: {result.url or 'Nenalezen'}")
            
        if use_tor:
            print("\nStatistiky proxy:")
            for proxy, stats in proxy_rotator.get_stats().items():
                success_rate = 0
                if (stats["success"] + stats["failure"]) > 0:
                    success_rate = stats["success"] / (stats["success"] + stats["failure"]) * 100
                print(f"{proxy}: Úspěch {stats['success']}x, Selhání {stats['failure']}x, Úspěšnost {success_rate:.1f}%")
        
    except Exception as e:
        print(f"Došlo k chybě: {e}")
    finally:
        if driver:
            driver.quit()
            print("Webdriver byl ukončen")

if __name__ == "__main__":
    main()