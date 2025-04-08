from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import random
import re
import os
import sys
import socket
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import DatabaseConnection, AresData, WebData

# Připojení k databázi
db = DatabaseConnection()
session = db.get_session()

def random_sleep(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

def setup_driver(proxy=None):
    firefox_options = webdriver.FirefoxOptions()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0"
    firefox_options.add_argument(f"user-agent={user_agent}")
    
    if proxy:
        host, port = proxy.replace("socks5://", "").split(":")
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference("network.proxy.socks", host)
        firefox_options.set_preference("network.proxy.socks_port", int(port))
        firefox_options.set_preference("network.proxy.socks_version", 5)
        print(f"Používám proxy: {proxy}")
    
    return webdriver.Firefox(options=firefox_options)

def check_tor_proxy(port=9150):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    result = s.connect_ex(('127.0.0.1', port))
    s.close()
    return f"socks5://127.0.0.1:{port}" if result == 0 else None

def get_new_tor_identity():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 9151))
        s.send(b'SIGNAL NEWNYM\r\n')
        response = s.recv(1024).decode()
        s.close()
        time.sleep(5)
        return response.startswith("250")
    except Exception as e:
        print(f"Chyba při změně Tor identity: {e}")
        return False

class ProxyRotator:
    def __init__(self, use_tor=False):
        self.use_tor = use_tor
        self.proxy = check_tor_proxy() if use_tor else None
    
    def get_proxy(self):
        if self.use_tor and self.proxy and random.random() < 0.2:
            get_new_tor_identity()
        return self.proxy

def handle_captcha(driver):
    if "captcha" in driver.current_url or driver.find_elements(By.XPATH, "//*[contains(text(), 'captcha')]"):
        print("DETEKOVÁNA CAPTCHA! Vyřešte ji ručně a stiskněte Enter...")
        input("Pokračujte po vyřešení: ")
        return not "captcha" in driver.current_url
    return True

def find_company_website(driver, company_name):
    if not company_name:
        return None
    
    search_query = f'"{company_name}" web'
    url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
    driver.get(url)
    random_sleep(2, 4)
    
    if not handle_captcha(driver):
        return None
    
    # Původní seznam selektorů z první verze
    selectors = [
        "div.g a[href^='http']",
        "div.yuRUbf a[href^='http']",
        ".LC20lb",
        "a[jsname]",
        "a[data-ved]",
        "div.tF2Cxc a",
        "h3.LC20lb + div + a",
        ".kCrYT a",
        "a[ping]",
        "div[jscontroller] a[href^='http']",
        "a[href^='http']"
    ]
    
    # Původní seznam blokovaných domén
    blocked_domains = [
        'facebook', 'twitter', 'instagram', 'linkedin', 'google', 'youtube.com', 'wikipedia', 'reddit',
        'pinterest', 'tumblr', 'flickr', 'vimeo', 'dailymotion', 'soundcloud', 'twitch', 'tiktok', 'snapchat',
        'gov.cz', 'justice.cz', 'zivefirmy.cz', 'firmy.cz', 'katalog-firem.cz', 'ares.cz', 'rejstrik-firem.cz',
        'rejstrik.penize.cz', 'edb.cz', 'seznam.cz', 'idnes.cz', 'novinky.cz', 'ihned.cz', 'aktualne.cz',
        'blesk.cz', 'reflex.cz', 'lidovky.cz', 'e15.cz', 'denik.cz', 'tyden.cz', 'zpravy.aktualne.cz',
        'zpravy.idnes.cz', 'zpravy.ihned.cz', 'zpravy.blesk.cz', 'zpravy.reflex.cz', 'obchodnirejstrik.cz',
        'databox.cz', 'firmycz.cz', 'podnikatel.cz', 'mistoprodeje.cz', 'hledamefirmy.cz', 'zlatestranky.cz',
        'zlutyodjezd.cz', 'najisto.cz', 'adresarfirem.cz', 'info-firmy.cz', 'empatica.cz'
    ]
    
    # Najdeme potenciální výsledky
    potential_sites = []
    for selector in selectors:
        try:
            results = driver.find_elements(By.CSS_SELECTOR, selector)
            for result in results:
                href = result.get_attribute("href")
                if href and href.startswith("http") and href not in potential_sites:
                    if not any(domain in href.lower() for domain in blocked_domains):
                        potential_sites.append(href)
        except Exception as e:
            print(f"Chyba při použití selektoru {selector}: {e}")
            continue
    
    potential_sites = potential_sites[:5]  # Omezíme na prvních 5
    
    print(f"Potenciální weby pro '{company_name}':")
    for i, site in enumerate(potential_sites):
        print(f"  {i+1}. {site}")
    
    # Scoring podle původní logiky
    if potential_sites:
        company_name_normalized = company_name.lower().replace(r'[^\w\s]', '')
        best_match, best_score = None, 0
        
        for site in potential_sites:
            domain_match = re.findall(r'https?://(?:www\.)?([^/]+)', site)
            if not domain_match:
                continue
            
            domain = domain_match[0].lower().replace(r'[^\w\s]', '')
            score = 0
            
            if company_name_normalized in domain:
                score += 10
            
            company_words = company_name_normalized.split()
            for word in company_words:
                if len(word) > 2 and word in domain:
                    score += 3
            
            print(f"    Skóre pro {domain}: {score}")
            
            if score > best_score:
                best_score, best_match = score, site
        
        if best_match and best_score > 0:
            print(f"Nejlepší shoda: {best_match} (skóre: {best_score})")
            return best_match
        elif potential_sites:
            print(f"Žádná dobrá shoda, vracím první výsledek: {potential_sites[0]}")
            return potential_sites[0]
    
    print(f"Pro firmu '{company_name}' nebyly nalezeny žádné potenciální weby.")
    return None

def process_company(driver, company, proxy_rotator):
    ico, name = company.ico, company.obchodni_jmeno
    if not name:
        print(f"Chybí jméno pro IČO {ico}")
        return None
    
    existing_web = session.query(WebData).filter_by(ico=ico).first()
    if existing_web and existing_web.url:
        print(f"Web již existuje: {existing_web.url}")
        return existing_web.url
    
    print(f"Zpracovávám: {name} (IČO: {ico})")
    website = find_company_website(driver, name)
    
    if website:
        print(f"Nalezen web: {website}")
        if existing_web:
            existing_web.url = website
        else:
            session.add(WebData(ico=ico, url=website))
        session.commit()
    else:
        if not existing_web:
            session.add(WebData(ico=ico, url=None))
            session.commit()
    
    return website

def main():
    companies = session.query(AresData).join(WebData, AresData.ico == WebData.ico, isouter=True).filter(
        (WebData.ico == None) & (AresData.obchodni_jmeno != None)
    ).limit(50).all()
    
    if not companies:
        print("Žádné firmy k zpracování.")
        return
    
    use_tor = input("Použít Tor proxy? (ano/ne, výchozí: ne): ").lower() == "ano"
    proxy_rotator = ProxyRotator(use_tor=use_tor)
    driver = setup_driver(proxy_rotator.get_proxy())
    
    success_count, requests_count = 0, 0
    
    try:
        for company in companies:
            requests_count += 1
            website = process_company(driver, company, proxy_rotator)
            if website:
                success_count += 1
            if requests_count % 5 == 0:
                print(f"Statistika: {success_count}/{requests_count} úspěchů")
            random_sleep(3, 10)
    finally:
        driver.quit()
        print("Dokončeno.")

if __name__ == "__main__":
    main()