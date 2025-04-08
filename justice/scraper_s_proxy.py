from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import re
import random
import signal
import json
import socket
import sys
from datetime import datetime
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import AresData, DatabaseConnection  # Import třídy AresData a DatabaseConnection z db.py
from sqlalchemy.orm import Session

def load_icos_from_db():
    """Načte seznam IČO z tabulky AresData v databázi."""
    try:
        db = DatabaseConnection()  # Singleton instance z db.py
        session = db.get_session()  # Získáme existující session
        icos = [record.ico for record in session.query(AresData).all()]
        # Session nezavíráme, respektujeme váš singleton design
        return icos
    except Exception as e:
        print(f"Chyba při načítání IČO z databáze: {e}")
        return []

# Třída ProxyRotator pro rotaci proxy
class ProxyRotator:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.proxy_stats = {}
        self.use_tor = False
        self.tor_proxy = None
        
    def setup_proxies(self, use_external_proxies=True, use_tor=True):
        """Nastaví seznam proxy serverů"""
        self.proxies = []
        
        # Přidáme externí proxy, pokud jsou požadovány
        if use_external_proxies:
            external_proxies = [
                # Zde přidejte svoje externí proxy servery
                # "http://proxy1.example.com:8080",
                # "http://proxy2.example.com:8080",
            ]
            self.proxies.extend(external_proxies)
        
        # Přidáme lokální Tor proxy, pokud je požadován
        if use_tor:
            self.use_tor = True
            self.tor_proxy = setup_local_tor_proxy()
            if self.tor_proxy:
                self.proxies.append(self.tor_proxy)
        
        # Inicializace statistik
        self.proxy_stats = {proxy: {"success": 0, "failure": 0} for proxy in self.proxies}
        
        if not self.proxies:
            print("Varování: Nejsou nakonfigurovány žádné proxy servery")
            return False
            
        print(f"Nakonfigurováno {len(self.proxies)} proxy serverů")
        return True
        
    def get_next_proxy(self):
        if not self.proxies:
            print("Žádné proxy nejsou k dispozici.")
            return None
            
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        if self.use_tor and proxy == self.tor_proxy and self.current_index == 0:
            old_ip = verify_ip_change()
            success = get_new_tor_identity()
            if success:
                new_ip = verify_ip_change(old_ip)
                print(f"Změna Tor identity - Stará IP: {old_ip}, Nová IP: {new_ip}")
            else:
                print(f"Změna Tor identity selhala, proxy: {proxy}")
        else:
            print(f"Používám proxy: {proxy}")
            current_ip = verify_ip_change()
            print(f"Aktuální IP adresa pro proxy {proxy}: {current_ip}")
            
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
# Třída RequestLimiter pro omezení počtu požadavků
class RequestLimiter:
    def __init__(self, limit_file_path, daily_limit=2950):
        """
        Inicializace limiteru požadavků.
        Args:
            limit_file_path (str): Cesta k souboru pro ukládání stavu požadavků
            daily_limit (int): Maximální počet požadavků za den
        """
        self.limit_file_path = limit_file_path
        self.daily_limit = daily_limit
        self.state = self._load_state()
    
    def _load_state(self):
        """Načte stav z JSON souboru nebo vytvoří nový stav"""
        if os.path.exists(self.limit_file_path):
            try:
                with open(self.limit_file_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                # Kontrola, zda den odpovídá dnešnímu dni
                if state.get('date') != datetime.now().strftime('%Y-%m-%d'):
                    # Nový den - resetujeme počítadlo
                    return {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'count': 0,
                        'last_request': datetime.now().isoformat()
                    }
                return state
            except (json.JSONDecodeError, IOError) as e:
                print(f"Chyba při načítání stavu limiteru: {e}")
        
        # Výchozí stav při neexistujícím souboru nebo chybě
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'count': 0,
            'last_request': datetime.now().isoformat()
        }
    
    def _save_state(self):
        """Uloží aktuální stav do JSON souboru"""
        try:
            with open(self.limit_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Chyba při ukládání stavu limiteru: {e}")
    
    def can_make_request(self):
        """Zkontroluje, zda lze provést další požadavek"""
        # Kontrola, zda je aktuální den stejný jako v uloženém stavu
        current_date = datetime.now().strftime('%Y-%m-%d')
        if self.state['date'] != current_date:
            # Nový den - resetujeme počítadlo
            self.state = {
                'date': current_date,
                'count': 0,
                'last_request': datetime.now().isoformat()
            }
            self._save_state()
            return True
        
        # Kontrola, zda není překročen denní limit
        return self.state['count'] < self.daily_limit
    
    def register_request(self):
        """Zaregistruje nový požadavek a vrátí True, pokud byl úspěšně zaregistrován"""
        if not self.can_make_request():
            return False
        
        # Zvýšení počítadla a aktualizace času posledního požadavku
        self.state['count'] += 1
        self.state['last_request'] = datetime.now().isoformat()
        self._save_state()
        return True
    
    def get_remaining_requests(self):
        """Vrátí počet zbývajících požadavků pro aktuální den"""
        # Kontrola, zda je aktuální den stejný jako v uloženém stavu
        if self.state['date'] != datetime.now().strftime('%Y-%m-%d'):
            return self.daily_limit
        return max(0, self.daily_limit - self.state['count'])
    
    def get_status_report(self):
        """Vrátí textový report o stavu požadavků"""
        remaining = self.get_remaining_requests()
        return (
            f"Stav požadavků k {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}:\n"
            f"- Celkem provedeno: {self.state['count']} z {self.daily_limit}\n"
            f"- Zbývá požadavků: {remaining}\n"
            f"- Poslední požadavek: {self.state['last_request'].replace('T', ' ').split('.')[0]}"
        )

# Funkce pro nastavení lokálního Tor proxy
def setup_local_tor_proxy():
    """
    Nastaví lokální Tor proxy a vrátí adresu proxy.
    Primárně kontroluje Tor Browser na portu 9150.
    
    Returns:
        str: Adresa proxy ve formátu "socks5://127.0.0.1:9150"
    """
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

def randomize_browser_fingerprint(driver):
    """
    Upraví parametry prohlížeče pro minimalizaci možnosti fingerprinting detekce.
    """
    # Náhodné nastavení rozlišení obrazovky
    screen_width = random.choice([1366, 1440, 1536, 1920, 2048])
    screen_height = random.choice([768, 900, 864, 1080, 1152])
    driver.execute_script(f"window.outerWidth = {screen_width}")
    driver.execute_script(f"window.outerHeight = {screen_height}")
    
    # Úprava canvas fingerprinting
    canvas_noise = '''
        (function() {
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                const context = originalGetContext.apply(this, arguments);
                if (type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function() {
                        let args = arguments;
                        const noise = Math.floor(Math.random() * 3) - 1;
                        args[1] = args[1] + noise;
                        args[2] = args[2] + noise;
                        return originalFillText.apply(this, args);
                    };
                }
                return context;
            };
        })();
    '''
    driver.execute_script(canvas_noise)
    
    # Úprava Navigator properties
    plugins_count = random.randint(5, 10)
    plugins_script = f'''
        Object.defineProperty(navigator, 'plugins', {{
            get: function() {{
                const plugins = [];
                for (let i = 0; i < {plugins_count}; i++) {{
                    plugins.push({{
                        name: 'Plugin ' + i,
                        description: 'Random plugin ' + i,
                        filename: 'plugin' + i + '.dll'
                    }});
                }}
                return plugins;
            }}
        }});
    '''
    driver.execute_script(plugins_script)
    
    # Úprava hardware concurrency
    hw_concurrency = random.choice([2, 4, 6, 8])
    driver.execute_script(f"Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw_concurrency} }});")
    
    # Úprava platform
    platforms = ["Win32", "Win64", "MacIntel", "Linux x86_64"]
    chosen_platform = random.choice(platforms)
    driver.execute_script(f"Object.defineProperty(navigator, 'platform', {{ get: () => '{chosen_platform}' }});")
    
    print(f"Nastavena randomizace prohlížeče: {chosen_platform}, {hw_concurrency} jádra, rozlišení {screen_width}x{screen_height}")

def get_existing_icos(download_dir):
    """Načte seznam IČO z názvů souborů ve složce."""
    existing_icos = set()
    for filename in os.listdir(download_dir):
        if filename.endswith('.pdf'):
            # Předpokládáme formát názvu: ICO_datum.pdf (např. 18240054_16_03_2025.pdf)
            ico = filename.split('_')[0]  # Vezmeme první část před podtržítkem
            if ico.isdigit() and len(ico) == 8:  # Kontrola, že to vypadá jako IČO
                existing_icos.add(ico)
    return existing_icos

def rotate_user_agent():
    """
    Generuje a vrací náhodný user agent.
    """
    os_list = ["Windows NT 10.0", "Windows NT 6.1", "Macintosh; Intel Mac OS X 10_15", "X11; Linux x86_64"]
    browser_versions = {
        "Chrome": ["90.0.4430", "91.0.4472", "92.0.4515", "93.0.4577", "94.0.4606", "95.0.4638", "96.0.4664"],
        "Firefox": ["88.0", "89.0", "90.0", "91.0", "92.0", "93.0", "94.0", "95.0", "96.0"],
        "Safari": ["14.1", "14.1.1", "15.0", "15.1", "15.2"]
    }
    
    chosen_os = random.choice(os_list)
    
    if random.random() < 0.6:  # 60% šance na Chrome
        browser = "Chrome"
        version = random.choice(browser_versions["Chrome"])
        ua = f"Mozilla/5.0 ({chosen_os}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
    elif random.random() < 0.9:  # 30% šance na Firefox
        browser = "Firefox"
        version = random.choice(browser_versions["Firefox"])
        ua = f"Mozilla/5.0 ({chosen_os}; rv:{version}) Gecko/20100101 Firefox/{version}"
    else:  # 10% šance na Safari
        browser = "Safari"
        version = random.choice(browser_versions["Safari"])
        ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"
    
    print(f"Použit user agent: {browser} {version}")
    return ua


def setup_driver_with_enhanced_privacy(proxy=None, download_dir=None):
    """
    Nastaví a inicializuje webdriver s rozšířenými funkcemi anonymity.
    """
    firefox_options = webdriver.FirefoxOptions()
    
    # Náhodný user agent
    user_agent = rotate_user_agent()
    firefox_options.add_argument(f"user-agent={user_agent}")
    
    # Zakázání WebRTC (může prozradit skutečnou IP)
    firefox_options.set_preference("media.peerconnection.enabled", False)
    
    # Zakázání geolokace
    firefox_options.set_preference("geo.enabled", False)
    
    # Zakázání automatického ukládání formulářů
    firefox_options.set_preference("browser.formfill.enable", False)
    
    # Zakázání ukládání historie
    firefox_options.set_preference("places.history.enabled", False)
    
    # Anonymní režim
    firefox_options.add_argument("-private")
    
    # Další nastavení pro privátní prohlížení
    firefox_options.set_preference("browser.privatebrowsing.autostart", True)
    
    # Vypnutí cache
    firefox_options.set_preference("browser.cache.disk.enable", False)
    firefox_options.set_preference("browser.cache.memory.enable", False)
    
    # Zakázání DOM storage
    firefox_options.set_preference("dom.storage.enabled", False)
    
    # Vypnutí hlášení o pádu
    firefox_options.set_preference("browser.crashReports.unsubmittedCheck.enabled", False)
    
    # Zakázání telemetrie
    firefox_options.set_preference("toolkit.telemetry.enabled", False)
    firefox_options.set_preference("toolkit.telemetry.archive.enabled", False)
    
    # Vypnutí automatického aktualizování
    firefox_options.set_preference("app.update.auto", False)
    
    # Nastavení proxy, pokud byla poskytnuta
    if proxy:
        if proxy.startswith("socks5://"):
            host, port = proxy.replace("socks5://", "").split(":")
            firefox_options.set_preference("network.proxy.type", 1)
            firefox_options.set_preference("network.proxy.socks", host)
            firefox_options.set_preference("network.proxy.socks_port", int(port))
            firefox_options.set_preference("network.proxy.socks_version", 5)
            # Zabráni DNS leakům přes Tor
            firefox_options.set_preference("network.proxy.socks_remote_dns", True)
        elif proxy.startswith("http://"):
            proxy_parts = proxy.replace("http://", "").split("@")
            if len(proxy_parts) > 1:
                auth, addr = proxy_parts
                user, pwd = auth.split(":")
                host, port = addr.split(":")
                firefox_options.set_preference("network.proxy.type", 1)
                firefox_options.set_preference("network.proxy.http", host)
                firefox_options.set_preference("network.proxy.http_port", int(port))
                firefox_options.set_preference("network.proxy.ssl", host)
                firefox_options.set_preference("network.proxy.ssl_port", int(port))
                firefox_options.set_preference("network.proxy.socks_username", user)
                firefox_options.set_preference("network.proxy.socks_password", pwd)
            else:
                host, port = proxy_parts[0].split(":")
                firefox_options.set_preference("network.proxy.type", 1)
                firefox_options.set_preference("network.proxy.http", host)
                firefox_options.set_preference("network.proxy.http_port", int(port))
                firefox_options.set_preference("network.proxy.ssl", host)
                firefox_options.set_preference("network.proxy.ssl_port", int(port))
    
    # Nastavení pro stahování souborů
    if download_dir:
        firefox_options.set_preference("browser.download.folderList", 2)
        firefox_options.set_preference("browser.download.manager.showWhenStarting", False)
        firefox_options.set_preference("browser.download.dir", download_dir)
        firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
        firefox_options.set_preference("pdfjs.disabled", True)
    
    try:
        driver = webdriver.Firefox(options=firefox_options)
        
        # Po inicializaci prohlížeče upravíme další parametry pro anonymizaci
        randomize_browser_fingerprint(driver)
        
        return driver
    except Exception as e:
        print(f"Chyba při inicializaci webdriveru: {e}")
        return None


class EnhancedProxyRotator(ProxyRotator):
    """
    Rozšířená třída pro rotaci proxy s lepší správou Tor identit.
    """
    def __init__(self):
        super().__init__()
        self.ip_usage_counter = 0
        self.ip_change_threshold = 2500
        self.last_identity_change = datetime.now()
        self.min_identity_change_interval = 60  # minimální interval změny identity v sekundách
    
    def should_change_identity(self):
        """Zkontroluje, zda by měla být změněna identita na základě počtu požadavků a času"""
        if self.ip_usage_counter >= self.ip_change_threshold:
            return True
        
        # Také změníme identitu, pokud uplynul určitý čas od poslední změny
        time_since_change = (datetime.now() - self.last_identity_change).total_seconds()
        return time_since_change > 1800  # změna každých 30 minut
    
    def get_next_proxy_with_counter(self):
        if self.should_change_identity() and self.use_tor:
            time_since_change = (datetime.now() - self.last_identity_change).total_seconds()
            if time_since_change >= self.min_identity_change_interval:
                print("Dosažen limit požadavků nebo času, měním Tor identitu...")
                success = get_new_tor_identity()
                if success:
                    self.ip_usage_counter = 0
                    self.last_identity_change = datetime.now()
                else:
                    print("Nepodařilo se změnit Tor identitu, pokračuji se stávající.")
        proxy = self.get_next_proxy()
        self.ip_usage_counter += 1
        return proxy
    
    def register_request_with_monitoring(self):
        """Zaregistruje požadavek a monitoruje počet použití"""
        self.ip_usage_counter += 1
        if self.should_change_identity():
            return False  # signál pro změnu identity
        return True


def verify_ip_change(old_ip=None):
    try:
        temp_driver = webdriver.Firefox(options=webdriver.FirefoxOptions())
        ip_services = [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com"
        ]
        
        for service in ip_services:
            try:
                temp_driver.get(service)
                time.sleep(2)
                ip = temp_driver.find_element(By.TAG_NAME, "body").text.strip()
                
                if ip and "." in ip:
                    temp_driver.quit()
                    if old_ip and ip == old_ip:
                        print(f"VAROVÁNÍ: IP adresa se nezměnila! Stále: {ip}")
                    else:
                        print(f"Aktuální IP adresa: {ip}")
                    return ip
            except:
                continue
        
        temp_driver.quit()
        print("Nepodařilo se zjistit IP adresu")
        return None
    except Exception as e:
        print(f"Chyba při ověřování IP: {e}")
        return None

def load_processed_icos(download_dir):
    """Načte seznam zpracovaných IČO z JSON souboru."""
    processed_file = os.path.join(download_dir, "processed_icos.json")
    if os.path.exists(processed_file):
        try:
            with open(processed_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Chyba při načítání zpracovaných IČO: {e}")
    return set()

def save_processed_ico(download_dir, ico, processed_icos):
    """Uloží nové IČO do seznamu zpracovaných."""
    processed_icos.add(ico)
    processed_file = os.path.join(download_dir, "processed_icos.json")
    try:
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(list(processed_icos), f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Chyba při ukládání zpracovaných IČO: {e}")

def timeout_handler(signum, frame):
    """Obsluha timeoutu pro operace, které by mohly zablokovat"""
    raise TimeoutError("Operace trvala příliš dlouho")


def safe_request_with_backoff(driver, url, max_retries=3):
    """
    Provede bezpečný požadavek s exponenciálním backoff při selhání.
    """
    retry = 0
    while retry < max_retries:
        try:
            # Nastavíme timeout pro případ, že by stránka trvala příliš dlouho
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 sekund timeout
            
            driver.get(url)
            
            # Vypneme alarm, pokud se požadavek povedl
            signal.alarm(0)
            
            # Náhodné čekání pro simulaci lidského chování
            random_sleep(2 + random.random() * 3, 5 + random.random() * 3)
            
            return True
        except TimeoutError:
            print(f"Timeout při požadavku na {url}")
        except Exception as e:
            print(f"Chyba při požadavku na {url}: {e}")
        
        # Exponenciální backoff
        wait_time = (2 ** retry) + random.random() * 2
        print(f"Čekám {wait_time:.1f} sekund před dalším pokusem...")
        time.sleep(wait_time)
        retry += 1
    
    return False

def get_new_tor_identity():
    control_port = 9051
    password = ""  # Nastav heslo, pokud je v torrc nastaveno
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)  # Timeout pro připojení
        s.connect(('127.0.0.1', control_port))
        
        if password:
            auth_cmd = f'AUTHENTICATE "{password}"\r\n'.encode()
            s.send(auth_cmd)
            response = s.recv(1024).decode()
            if not response.startswith("250"):
                print(f"Chyba při autentizaci na Tor Control Port: {response}")
                s.close()
                return False
        
        s.send(b'SIGNAL NEWNYM\r\n')
        response = s.recv(1024).decode()
        s.close()
        
        if response.startswith("250"):
            print("Úspěšně získána nová Tor identita")
            time.sleep(5)  # Čekání na projevení změny
            return True
        else:
            print(f"Chyba při získávání nové Tor identity: {response}")
            return False
    except Exception as e:
        print(f"Chyba při komunikaci s Tor Control Port: {e}")
        print("Ujistěte se, že Tor běží a ControlPort je nastaven na 9051 v torrc.")
        return False



def setup_driver(proxy=None, download_dir=None):
    firefox_options = webdriver.FirefoxOptions()
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
    ]
    firefox_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    if download_dir:
        firefox_options.set_preference("browser.download.folderList", 2)
        firefox_options.set_preference("browser.download.manager.showWhenStarting", False)
        firefox_options.set_preference("browser.download.dir", download_dir)
        firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
        firefox_options.set_preference("pdfjs.disabled", True)
    
    if proxy:
        try:
            if proxy.startswith("http://"):
                proxy_parts = proxy.replace("http://", "").split("@")
                if len(proxy_parts) > 1:
                    auth, addr = proxy_parts
                    user, pwd = auth.split(":")
                    host, port = addr.split(":")
                    firefox_options.set_preference("network.proxy.type", 1)
                    firefox_options.set_preference("network.proxy.http", host)
                    firefox_options.set_preference("network.proxy.http_port", int(port))
                    firefox_options.set_preference("network.proxy.ssl", host)
                    firefox_options.set_preference("network.proxy.ssl_port", int(port))
                    firefox_options.set_preference("network.proxy.socks_username", user)
                    firefox_options.set_preference("network.proxy.socks_password", pwd)
                else:
                    host, port = proxy_parts[0].split(":")
                    firefox_options.set_preference("network.proxy.type", 1)
                    firefox_options.set_preference("network.proxy.http", host)
                    firefox_options.set_preference("network.proxy.http_port", int(port))
                    firefox_options.set_preference("network.proxy.ssl", host)
                    firefox_options.set_preference("network.proxy.ssl_port", int(port))
            elif proxy.startswith("socks5://"):
                host, port = proxy.replace("socks5://", "").split(":")
                firefox_options.set_preference("network.proxy.type", 1)
                firefox_options.set_preference("network.proxy.socks", host)
                firefox_options.set_preference("network.proxy.socks_port", int(port))
                firefox_options.set_preference("network.proxy.socks_version", 5)
            print(f"Používám proxy: {proxy}")
        except Exception as e:
            print(f"Chyba při nastavení proxy {proxy}: {e}")
            raise Exception("Proxy selhalo, ukončuji skript.")
    
    try:
        driver = webdriver.Firefox(options=firefox_options)
        return driver
    except Exception as e:
        print(f"Chyba při inicializaci webdriveru: {e}")
        if proxy:
            raise Exception("Nepodařilo se inicializovat webdriver s proxy, ukončuji skript.")
        else:
            raise Exception("Nepodařilo se inicializovat webdriver, ukončuji skript.")

def detect_captcha(driver):
    """Detekuje, zda jsme narazili na CAPTCHA nebo jsme blokováni"""
    # Indikátory CAPTCHA a blokace pro justice.cz
    captcha_indicators = [
        "//form[contains(@action, 'captcha')]",
        "//input[@id='captcha']",
        "//img[contains(@src, 'captcha')]",
        "//div[contains(text(), 'captcha')]",
        "//div[contains(text(), 'Captcha')]",
        "//div[contains(text(), 'CAPTCHA')]",
        "//div[contains(text(), 'překročil denní limit')]", 
        "//div[contains(text(), 'byla omezena')]",
        "//div[contains(text(), 'omezení přístupu')]",
        "//div[contains(text(), 'přístup byl zakázán')]",
        "//div[contains(text(), 'access denied')]",
        "//div[contains(text(), 'access forbidden')]"
    ]
    
    for indicator in captcha_indicators:
        try:
            if driver.find_elements(By.XPATH, indicator):
                return True
        except:
            pass
    
    # Kontrola textu stránky na blokaci
    try:
        page_text = driver.page_source.lower()
        blocking_phrases = ["přístup byl omezen", "denní limit požadavků", "access denied", 
                          "přístup zakázán", "došlo k překročení", "omezená funkčnost", 
                          "služba není dostupná"]
        for phrase in blocking_phrases:
            if phrase in page_text:
                return True
    except:
        pass
        
    return False

def wait_for_captcha_solution(driver):
    """Čeká na ruční vyřešení CAPTCHA"""
    print("\n" + "="*50)
    print("DETEKOVÁNA CAPTCHA nebo BLOKACE! Vyřešte ji ručně v otevřeném prohlížeči.")
    print("Až budete hotovi, stiskněte Enter pro pokračování...")
    print("="*50 + "\n")
    
    input("Stiskněte Enter po vyřešení CAPTCHA...")
    
    # Kontrola, zda byla CAPTCHA vyřešena
    if detect_captcha(driver):
        print("CAPTCHA/blokace stále detekována. Zkusíme počkat ještě chvíli...")
        time.sleep(3)
        if detect_captcha(driver):
            print("CAPTCHA/blokace nebyla vyřešena správně, zkusíme přeskočit aktuální firmu.")
            return False
    
    print("CAPTCHA/blokace úspěšně vyřešena, pokračujeme...")
    return True

# Funkce pro náhodné čekání
def random_sleep(min_sec=1, max_sec=3):
    """Náhodné čekání mezi požadavky"""
    time.sleep(random.uniform(min_sec, max_sec))

# Funkce pro zpracování jednoho IČO s podporou proxy
def process_ico(ico, driver, limiter, download_dir, proxy_rotator=None, current_proxy=None, processed_icos=None):
    """Zpracování jednoho IČO s ochranou proti detekci a blokaci"""
    # Kontrola limitu požadavků
    if not limiter.can_make_request():
        print(f"Dosažen denní limit požadavků ({limiter.daily_limit}). Další zpracování není možné.")
        return False

    # Kontrola, zda máme funkční driver
    if driver is None:
        print("Webdriver není inicializován. Inicializuji nový.")
        if proxy_rotator and current_proxy:
            driver = setup_driver(current_proxy, download_dir)
        else:
            driver = setup_driver(None, download_dir)
        
        if driver is None:
            print("Nepodařilo se inicializovat webdriver. Přeskakuji IČO.")
            return False

    # Zaznamenáme požadavek do limiteru
    limiter.register_request()
    
    try:
        print(f"Zpracovávám IČO: {ico}")
        driver.get("https://or.justice.cz/ias/ui/rejstrik")
        random_sleep(3, 5)
        
        if detect_captcha(driver):
            if not wait_for_captcha_solution(driver):
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_failure(current_proxy)
                    print("Blokace detekována, měníme proxy a zkusíme znovu...")
                    return None
            else:
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_success(current_proxy)
        
        try:
            chatbot_close_button = driver.find_element(By.CSS_SELECTOR, ".chat-close-btn, .close-button, button.close, .chat-header button, svg.close")
            chatbot_close_button.click()
            print("Chatbot byl zavřen")
            random_sleep(0, 1)
        except Exception as ce:
            print(f"Nepodařilo se zavřít chatbota: {ce}")
            try:
                close_buttons = driver.find_elements(By.XPATH, "//*[contains(@class, 'close') or contains(@class, 'button')]")
                for button in close_buttons:
                    if button.is_displayed():
                        print(f"Zkouším kliknout na potenciální zavírací tlačítko: {button.get_attribute('outerHTML')}")
                        button.click()
                        random_sleep(2, 3)
                        break
            except Exception as e:
                print(f"Alternativní metoda zavření chatbota selhala: {e}")
        
        search_box = driver.find_element(By.XPATH, "//input[@type='text' and contains(@id, 'search')]")
        search_box.clear()
        search_box.send_keys(ico)
        
        search_button = driver.find_element(By.ID, "quick-search-button")
        search_button.click()
        
        print(f"Čekám na výsledky vyhledávání pro IČO: {ico}...")
        random_sleep(0.1, 1)
        
        if detect_captcha(driver):
            if not wait_for_captcha_solution(driver):
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_failure(current_proxy)
                    print("Blokace detekována po hledání, měníme proxy...")
                    return None
            else:
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_success(current_proxy)
        
        print("Vyhledávání bylo dokončeno")
        driver.implicitly_wait(2)

        driver.execute_script("window.scrollBy(0, 1000)")
        driver.implicitly_wait(1)

        try:
            sbirka_listin = driver.find_element(By.XPATH, "//a[contains(@href, 'vypis-sl-firma')]")
            sbirka_listin.click()
            print("Kliknuto na Sbírka listin")
        except NoSuchElementException:
            print("Odkaz na sbírku listin nebyl nalezen, možná firma nemá žádné dokumenty.")
            save_processed_ico(download_dir, ico, processed_icos)  # Zaznamenáme i bez závěrky
            return False

        driver.execute_script("window.scrollBy(0, 1000)")
        
        if detect_captcha(driver):
            if not wait_for_captcha_solution(driver):
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_failure(current_proxy)
                    return None
            else:
                if proxy_rotator and current_proxy:
                    proxy_rotator.report_success(current_proxy)
                    
        try:
            print("Hledám tabulku s listinami...")
            random_sleep(1, 2)
            
            rows = driver.find_elements(By.XPATH, "//table//tr")
            ucetni_zaverka_found = False
            datum_podani = ""
            
            for row in rows:
                try:
                    typ_listiny_elements = row.find_elements(By.XPATH, "./td[2]")
                    if not typ_listiny_elements:
                        continue
                        
                    typ_listiny = typ_listiny_elements[0].text.lower()
                    
                    if "účetní závěrka" in typ_listiny:
                        listina_link = row.find_element(By.XPATH, "./td[1]/a")
                        print(f"Nalezena účetní závěrka: {listina_link.text}")
                        
                        listina_link.click()
                        print("Úspěšně kliknuto na poslední účetní závěrku.")
                        
                        random_sleep(1.3, 2)
                        
                        if detect_captcha(driver):
                            if not wait_for_captcha_solution(driver):
                                if proxy_rotator and current_proxy:
                                    proxy_rotator.report_failure(current_proxy)
                                    return None
                            else:
                                if proxy_rotator and current_proxy:
                                    proxy_rotator.report_success(current_proxy)
                        
                        try:
                            try:
                                datum_element = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div/table/tbody/tr[12]/td")
                                datum_podani = datum_element.text.strip()
                            except:
                                rows_detail = driver.find_elements(By.XPATH, "//tr")
                                for row_detail in rows_detail:
                                    cell_labels = row_detail.find_elements(By.XPATH, "./th")
                                    for label in cell_labels:
                                        if "Kdy došla:" in label.text:
                                            datum_podani = row_detail.find_element(By.XPATH, "./td").text.strip()
                                            break
                            print(f"Nalezeno datum podání: '{datum_podani}'")
                        except Exception as e:
                            print(f"Chyba při hledání data podání: {e}")
                            datum_podani = datetime.now().strftime("%d.%m.%Y")
                        
                        ucetni_zaverka_found = True
                        break
                except Exception as row_error:
                    print(f"Chyba při zpracování řádku: {row_error}")
            
            if ucetni_zaverka_found:
                print("Účetní závěrka nalezena, čekám na načtení obsahu...")
                random_sleep(0.3, 1)
                
                formatted_date = ""
                if datum_podani:
                    try:
                        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', datum_podani)
                        if match:
                            den, mesic, rok = match.groups()
                            formatted_date = f"{den}_{mesic}_{rok}"
                        else:
                            formatted_date = datetime.now().strftime("%d_%m_%Y")
                    except Exception as e:
                        print(f"Chyba při formátování data: {e}")
                        formatted_date = datetime.now().strftime("%d_%m_%Y")
                else:
                    formatted_date = datetime.now().strftime("%d_%m_%Y")
                
                print(f"Datum pro název souboru: {formatted_date}")
                
                try:
                    pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/ias/content/download') and contains(., '.pdf')]")
                    print(f"Nalezeno {len(pdf_links)} PDF odkazů")
                    
                    target_link = None
                    for link in pdf_links:
                        link_text = link.text.lower()
                        if "priloha" in link_text or "přiloha" in link_text:
                            continue
                        if ".xlsx" in link_text:
                            continue
                        if "uz-" in link_text:
                            target_link = link
                            break
                        if not target_link and ".pdf" in link_text:
                            target_link = link
                    
                    if target_link:
                        print(f"Stahuji soubor: {target_link.text}")
                        new_filename = f"{ico}_{formatted_date}.pdf"
                        new_filepath = os.path.join(download_dir, new_filename)
                        files_before = set(os.listdir(download_dir))
                        
                        driver.execute_script("window.open(arguments[0]);", target_link.get_attribute("href"))
                        print("Čekám na stažení souboru...")
                        random_sleep(2, 3)
                        
                        if detect_captcha(driver):
                            if not wait_for_captcha_solution(driver):
                                if proxy_rotator and current_proxy:
                                    proxy_rotator.report_failure(current_proxy)
                                    return None
                            else:
                                if proxy_rotator and current_proxy:
                                    proxy_rotator.report_success(current_proxy)
                        
                        files_after = set(os.listdir(download_dir))
                        new_files = files_after - files_before
                        
                        if new_files:
                            downloaded_file = os.path.join(download_dir, list(new_files)[0])
                            if os.path.exists(new_filepath):
                                os.remove(new_filepath)
                            os.rename(downloaded_file, new_filepath)
                            print(f"Soubor úspěšně přejmenován na: {new_filename}")
                            save_processed_ico(download_dir, ico, processed_icos)  # Zaznamenáme po stažení
                            return True
                        else:
                            print("Soubor se nestáhl do cílové složky, kontroluji výchozí složku...")
                            default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                            try:
                                files_after_default = set(os.listdir(default_download_dir))
                                new_files_default = files_after_default - set(os.listdir(default_download_dir))
                                if new_files_default:
                                    downloaded_file = os.path.join(default_download_dir, list(new_files_default)[0])
                                    if os.path.exists(new_filepath):
                                        os.remove(new_filepath)
                                    shutil.copy(downloaded_file, new_filepath)
                                    print(f"Soubor úspěšně zkopírován z výchozí složky na: {new_filename}")
                                    save_processed_ico(download_dir, ico, processed_icos)  # Zaznamenáme po stažení
                                    return True
                            except Exception as e:
                                print(f"Chyba při kontrole výchozí složky stahování: {e}")
                    else:
                        print("Nenalezen žádný vhodný PDF soubor ke stažení")
                except Exception as e:
                    print(f"Chyba při stahování souboru: {e}")
            else:
                print("Firma nezveřejnila účetní uzávěrku nebo nebyla nalezena.")
        except Exception as e:
            print(f"Chyba při hledání účetní závěrky: {e}")
    
    except Exception as e:
        print(f"Chyba při zpracování IČO {ico}: {e}")
        if proxy_rotator and current_proxy:
            proxy_rotator.report_failure(current_proxy)
        return False
    
    # Zaznamenáme IČO jako zpracované i při neúspěchu (kromě CAPTCHA/proxy problémů)
    if processed_icos is not None:
        save_processed_ico(download_dir, ico, processed_icos)
    return False

# Hlavní funkce programu
def main():
    # Nastavení cílové složky pro stažené soubory
    download_dir = r"C:\Moje stahování\kodovani\unor_2025\antana\lead\justice\uzaverky"
    default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    # Vytvoření složky, pokud neexistuje
    os.makedirs(download_dir, exist_ok=True)

    # Načtení existujících IČO ze složky (pro informaci)
    existing_icos = get_existing_icos(download_dir)
    print(f"Nalezeno {len(existing_icos)} již stažených IČO: {existing_icos}")

    # Načtení zpracovaných IČO (včetně těch bez závěrky)
    processed_icos = load_processed_icos(download_dir)
    print(f"Nalezeno {len(processed_icos)} zpracovaných IČO: {processed_icos}")

    # Inicializace limiteru
    limiter_file = os.path.join(download_dir, "request_limiter.json")
    limiter = RequestLimiter(limiter_file, daily_limit=2950)

    # Inicializace rotátoru proxy
    proxy_rotator = ProxyRotator()
    proxy_rotator.setup_proxies(use_external_proxies=False, use_tor=True)
    
    # Výpis stavu požadavků
    print(limiter.get_status_report())
    print(f"Zbývající počet požadavků: {limiter.get_remaining_requests()}")

    # Načtení seznamu IČO z databáze
    ico_list = load_icos_from_db()
    if not ico_list:
        print("Nepodařilo se načíst IČO z databáze, ukončuji...")
        return
    
    print(f"Celkem načteno {len(ico_list)} IČO ke zpracování z databáze")
    
    # Zpracování seznamu IČO
    driver = None
    current_proxy = None
    processed_count = 0
    
    try:
        for ico in ico_list:
            if ico in processed_icos:
                print(f"IČO {ico} již bylo zpracováno, přeskakuji...")
                continue

            if proxy_rotator and (driver is None or processed_count % 10 == 0):
                if driver is not None:
                    driver.quit()
                    driver = None
                
                current_proxy = proxy_rotator.get_next_proxy()
                if current_proxy:
                    print(f"Používám novou proxy: {current_proxy}")
                    driver = setup_driver(current_proxy, download_dir)
                    current_ip = verify_ip_change()
                    print(f"Aktuální IP adresa po nastavení proxy: {current_ip}")
                else:
                    print("Nepodařilo se získat proxy. Ukončuji skript.")
                    sys.exit(1)
            
            result = process_ico(ico, driver, limiter, download_dir, proxy_rotator, current_proxy, processed_icos)
            
            if result is None:
                print(f"Problém s proxy nebo CAPTCHA při zpracování IČO {ico}. Měním proxy...")
                if driver is not None:
                    driver.quit()
                    driver = None
                
                current_proxy = proxy_rotator.get_next_proxy()
                if current_proxy:
                    print(f"Používám novou proxy: {current_proxy}")
                    driver = setup_driver(current_proxy, download_dir)
                    current_ip = verify_ip_change()
                    print(f"Aktuální IP adresa po nastavení proxy: {current_ip}")
                else:
                    print("Nepodařilo se získat proxy. Ukončuji skript.")
                    sys.exit(1)
                
                process_ico(ico, driver, limiter, download_dir, proxy_rotator, current_proxy, processed_icos)
            
            processed_count += 1
            
    except KeyboardInterrupt:
        print("\nSkript byl přerušen uživatelem...")
    except Exception as e:
        print(f"Neočekávaná chyba: {e}")
        sys.exit(1)
    finally:
        # Výpis statistik
        print("\n" + "="*50)
        print("Statistiky proxy serverů:")
        stats = proxy_rotator.get_stats()
        for proxy, stat in stats.items():
            success_rate = 0
            if (stat["success"] + stat["failure"]) > 0:
                success_rate = (stat["success"] / (stat["success"] + stat["failure"])) * 100
            print(f"- {proxy}: úspěch {stat['success']}, selhání {stat['failure']}, úspěšnost {success_rate:.1f}%")
        
        print("\nStav požadavků:")
        print(limiter.get_status_report())
        
        # Zavření prohlížeče
        if driver is not None:
            print("Zavírám prohlížeč...")
            driver.quit()
        
        print("Skript dokončen.")

# Spuštění hlavní funkce
if __name__ == "__main__":
    main()