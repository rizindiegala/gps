#!/usr/bin/env python3

from flask import render_template
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import xlsxwriter, random, platform, stat
from os.path import exists
from commons import *
from data_file import *



GENBA_PAGE_URLS = {
    'home':         'https://genbadigital.com',
    'etailer':      'https://etailer.genbadigital.io/',
    'login':        'https://etailer.genbadigital.io/repository/wim/portal.ashx?login',
    'product':      'https://etailer.genbadigital.io/2/repository/wim/portal.ashx?list=52&product=',
    'catalog':      'https://etailer.genbadigital.io/pages/products/product-catalogue',
}

def get_genba_credentials():
    username = os.environ.get('GENBA_USERNAME', '').strip()
    password = os.environ.get('GENBA_PASSWORD', '').strip()
    if not username or not password:
        log_error(
            'Mancano GENBA_USERNAME e/o GENBA_PASSWORD. Copia .env.example in .env e inserisci le credenziali.',
            context="genba_credentials",
        )
        return None
    return {'username': username, 'password': password}

CURRENCY_QUOTES = {
    'USD': 1
}

SELENIUM_LOAD_PAGE_TIMEOUT = 10

# GET /
def get_page_index():
    return render_template('home.html', values={}) 


# POST /ajax/genba-data
def get_ajax_genba_data( request_data ):
    log(request_data, "request_data", "get_genba_data")
    response_data = {}
    response_data['products'] = []
    sku_id_list             = request_data['sku_id_list']
    output_currency         = request_data['currency']
    driver = None
    for sku_id in sku_id_list:
        sku_id = sku_id.strip()
        if not sku_id:
            continue
        log(sku_id, 'Ottengo i dati del prodotto', "get_ajax_genba_data")
        product = get_product_from_data_file( sku_id )
        # log(product, "product", "get_ajax_genba_data")
        if product:
            response_data['products'].append( product )
            continue
        if not driver:
            driver = selenium_get_webdriver()
            if not driver:
                return response_data
        product = {}
        product['sku_id'] = sku_id
        product_data = {}
        product_data['currencies'] = []
        raw_data, error = selenium_build_product_page_data(driver, sku_id)
        if error:
            product_data['title']= f"Errore - {error['text']}"
            product['data'] = product_data
            response_data['products'].append( product )
            continue
        product_data = extract_product_data( raw_data )
        currencies_string_list = []
        # log(product_data['currencies'], "product_data['currencies']", "get_ajax_genba_data")
        for item in product_data['currencies']:
            if item['currency_code'] != 'USD' and not available_currency_quote( item['currency_code'] ):
                currencies_string_list.append( item['currency_code'] )
        if currencies_string_list:
            currency_quotes = get_currency_quotes( currencies_string_list )
            if not currency_quotes:
                return response_data
        product_data['currencies'] = convert_price_to_defaults(product_data['currencies'], output_currency)
        product['data']             = product_data
        product['last_update']      = datetime.now().strftime( DATETIME_ISO_FORMAT )
        save_product_data_file(product, sku_id)
        product['data_origin']                  = 'request'
        product['last_update_readable']         = datetime.now().strftime( DATETIME_READABLE_FORMAT )
        response_data['products'].append( product )
    if driver:
        driver.quit()
    return response_data

def selenium_get_webdriver():
    driver = selenium_init() 
    driver = selenium_process_login( driver )
    return driver

def selenium_get_chrome_driver_filename():
    if platform.system() == 'Windows':
        return 'chromedriver.exe'
    return 'chromedriver'

def selenium_make_executable( driver_path ):
    if platform.system() == 'Windows' or os.access( driver_path, os.X_OK ):
        return driver_path
    log(driver_path, 'Il chromedriver non e\' eseguibile, aggiungo i permessi', context="selenium_init")
    driver_path.chmod( driver_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH )
    return driver_path

def selenium_get_chrome_driver_path():
    # Restituiamo un driver solo se e' indicato esplicitamente in CHROMEDRIVER_PATH:
    # passare un executable_path a Selenium disattiva il Selenium Manager, che
    # altrimenti procura da solo sia il chromedriver sia Chrome quando mancano.
    custom_path = os.environ.get('CHROMEDRIVER_PATH')
    if not custom_path:
        return None
    custom_path = Path( custom_path )
    if custom_path.is_file():
        return selenium_make_executable( custom_path )
    log(custom_path, 'CHROMEDRIVER_PATH e\' impostato ma il file non esiste, lo ignoro', context="selenium_init")
    return None

def selenium_get_chrome_options():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_argument('lang=en')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
    options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_binary = os.environ.get('CHROME_BINARY')
    if chrome_binary:
        log(chrome_binary, 'Uso il binario di Chrome indicato da CHROME_BINARY', context="selenium_init")
        options.binary_location = chrome_binary
    return options

def selenium_init():
    log("Avvio il web driver...", context="selenium_init")
    log(f'{platform.system()} {platform.machine()}', 'Piattaforma', context="selenium_init")
    chrome_driver_path = selenium_get_chrome_driver_path()
    if chrome_driver_path:
        log(chrome_driver_path, 'Uso il chromedriver indicato in CHROMEDRIVER_PATH', context="selenium_init")
        service = Service(executable_path=str( chrome_driver_path ))
    else:
        log('Driver e browser li procura Selenium: se non sono presenti li scarica (la prima volta puo\' richiedere qualche minuto).', context="selenium_init")
        service = Service()
    try:
        driver = webdriver.Chrome(service=service, options=selenium_get_chrome_options())
    except Exception as e:
        # Driver mancante o di versione incompatibile con il Chrome installato:
        # come ultima risorsa lo scarico al volo per questa macchina.
        log_error(e, 'Avvio del web driver fallito, provo a scaricare quello giusto', context="selenium_init")
        driver = selenium_init_with_downloaded_driver()
    driver.set_window_size(1200, 768)
    return driver

def selenium_init_with_downloaded_driver():
    from webdriver_manager.chrome import ChromeDriverManager
    downloaded_path = Path( ChromeDriverManager().install() )
    driver_filename = selenium_get_chrome_driver_filename()
    if downloaded_path.name != driver_filename:
        # webdriver_manager a volte restituisce un altro file dell'archivio
        # scaricato (es. THIRD_PARTY_NOTICES) invece dell'eseguibile.
        downloaded_path = downloaded_path.parent / driver_filename
    log(downloaded_path, 'Chromedriver scaricato', context="selenium_init")
    service = Service(executable_path=str( selenium_make_executable( downloaded_path ) ))
    return webdriver.Chrome(service=service, options=selenium_get_chrome_options())

def selenium_process_login( driver ):
    credentials = get_genba_credentials()
    if not credentials:
        return False
    driver.get( GENBA_PAGE_URLS['etailer'] )
    add_random_delay()
    log('Pagina login caricata.', context="process_login")
    log('Cerco il bottone per loggarmi via email.', context="process_login")
    clicked = 0
    for retries_counter in range(1, SELENIUM_LOAD_PAGE_TIMEOUT+1):
        try:
            log(f'Tentativo {retries_counter}...', context="process_login")
            login_button = driver.find_element(By.XPATH, "//div[@class='MuiPaper-root jss1 MuiPaper-elevation1 MuiPaper-rounded']")
            log(f'Trovato! Lo clicco...', context="process_login")
            clicked = 1
            login_button.click()
            break
        except Exception as e:
            log(e, 'Errore', context="process_login")
            sleep( 1 )
    if not clicked:
        log('Numero di tentativi massimo raggiunto. Esecuzione terminata.', context="process_login")
        return False
    add_random_delay()
    log('Interfaccia di login caricata.', context="process_login")
    log('Cerco l\'input username...', context="process_login")
    username_input = driver.find_element(By.ID, "username")
    log('Inserisco lo username nel campo input.', context="process_login")
    username_input.send_keys( credentials['username'] )
    add_random_delay()
    log('Cerco l\'input password...', context="process_login")
    password_input = driver.find_element(By.ID, "password")
    log('Inserisco la password nel campo input.', context="process_login")
    password_input.send_keys( credentials['password'] )
    add_random_delay()
    log('Clicco il bottone per loggarmi...', context="process_login")
    submit_button = driver.find_element(By.XPATH, "//button[@class='MuiButtonBase-root MuiButton-root MuiButton-contained MuiButton-containedPrimary MuiButton-containedSizeLarge MuiButton-sizeLarge MuiButton-fullWidth']//span[@class='MuiButton-label' and text()='Sign In']")
    submit_button.click()
    add_random_delay()
    return driver

def add_random_delay():
    random_float = round(random.uniform(0.99, 1.99), 2)
    log(f'Sleep {random_float} sec', context="add_random_delay")
    sleep( random_float )
    return

def get_product_from_data_file( sku_id ):
    data_file = data_file_get()
    if not data_file:
        log('Data file non presente', context="get_product_from_data_file")
        data_file_init()
        return {}
    product_data_collection = data_file['products']
    if not sku_id in product_data_collection:
        log(sku_id, 'Sku id non presente nel data file', context="get_product_from_data_file")
        return {}
    product = product_data_collection[sku_id]
    last_update = product['last_update']
    if not last_update:
        log(sku_id, 'Last update non presente', context="get_product_from_data_file")
        return {}
    last_update = datetime.strptime(last_update, DATETIME_ISO_FORMAT)
    now = datetime.now()
    time_difference_in_hours = (now - last_update).total_seconds() / 3600
    # log(time_difference_in_hours, "time_difference_in_hours", "get_product_from_data_file")
    if time_difference_in_hours < DATA_LIFE['products']:
        readable_date_time = last_update.strftime( DATETIME_READABLE_FORMAT )
        log(readable_date_time, 'Dati ottenuti da file, last_update', context='get_product_from_data_file')
        product['sku_id']                       = sku_id
        product['data_origin']                  = 'data file'
        product['last_update_readable']         = readable_date_time
        return product
    return {}

def selenium_build_product_page_data(driver, sku_id):
    raw_data = {}
    driver, error = selenium_get_product_page_driver(driver, sku_id)
    if error:
        return None, error
    raw_data, error = selenium_extract_product_raw_data(driver, sku_id)
    return raw_data, error

def selenium_get_product_page_driver(driver, sku_id):
    error = {}
    log('Ottengo la pagina prodotti...', context="selenium_get_product_page_driver")
    driver.get( GENBA_PAGE_URLS['catalog'] )
    try:
        log('Aspetto che venga caricata la pagina prodotto...', context="selenium_get_product_page_driver")
        WebDriverWait(driver, SELENIUM_LOAD_PAGE_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "sku_id"))
        )
    except Exception as e:
        error['text'] = 'Pagina ricerca prodotti non disponibile'
        log(error['text'], context="selenium_get_product_page_driver")
        return False, error
    add_random_delay()
    log('Inserisco lo sku id nel campo input.', context="selenium_get_product_page_driver")
    sku_id_input = driver.find_element(By.ID, "sku_id")
    sku_id_input.send_keys( sku_id )
    add_random_delay()
    log('Cerco il bottone submit...', context="selenium_get_product_page_driver")
    filter_button = driver.find_element(By.XPATH, "//button[@aria-label='Search' and @type='submit' and contains(@class, 'p-button') and contains(@class, 'p-component')]")
    log('Trovato, lo clicco...', context="selenium_get_product_page_driver")
    filter_button_clicked = 0
    for retries_counter in range(1, SELENIUM_LOAD_PAGE_TIMEOUT+1):
        try:
            filter_button.click()
            filter_button_clicked = 1
            break
        except Exception as e:
            pass
    if not filter_button_clicked:
        error['text'] = 'Click su bottone filter non riuscito.'
        log(error['text'], context="selenium_get_product_page_driver")
        return False, error
    log('Ottengo i risultati della ricerca...', context="selenium_get_product_page_driver")
    product_page_link_found = 0
    for retries_counter in range(1, SELENIUM_LOAD_PAGE_TIMEOUT+1):
        try:
            log(f'Tentativo {retries_counter}...', context="selenium_get_product_page_driver")
            product_page_link = driver.find_element(By.XPATH, "//tr[@class='p-selectable-row' and @tabindex='0']")
            log(f'Trovato! Lo clicco...', context="selenium_get_product_page_driver")
            add_random_delay()
            product_page_link.click()
            product_page_link_found = 1
            break
        except Exception as e:
            sleep( 1 )
    if not product_page_link_found:
        error['text'] = 'Link alla pagina prodotto non trovato'
        log(sku_id, error['text'], context="selenium_get_product_page_driver")
        return False, error
    return driver, error

def selenium_extract_product_raw_data(driver, sku_id):
    error = {}
    try:
        log('Aspetto che venga caricata la pagina prodotto...', context="selenium_extract_product_raw_data")
        WebDriverWait(driver, SELENIUM_LOAD_PAGE_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='card']//h5[text()='Prices']"))
        )
    except Exception as e:
        error['text'] = 'Pagina prodotto non disponibile.'
        log(sku_id, error['text'], context="selenium_extract_product_raw_data")
        return False, error
    add_random_delay()
    raw_data = {}
    log('Ottengo il titolo del prodotto...', context="selenium_extract_product_raw_data")
    try:
        h4_element = driver.find_element(By.TAG_NAME, "h4")
        raw_data['title'] = h4_element.get_attribute("outerHTML")
    except Exception as e:
        log(e, 'Errore nell\' ottenere il titolo del prodotto', context="selenium_extract_product_raw_data")
        raw_data['title'] = 'Titolo non trovato'
    log('Ottengo il contenitore delle immagini', context="selenium_extract_product_raw_data")
    try:
        images_container = driver.find_element(By.XPATH, "//div[@class='p-galleria-thumbnail-items-container' and @data-pc-section='thumbnailitemscontainer']")
        raw_data['images'] = images_container.get_attribute("outerHTML")
    except Exception as e:
        raw_data['images'] = None
        log('Non ho trovato immagini del prodotto', context="selenium_extract_product_raw_data")
    log('Ottengo il contenitore dei dati dei prezzi prodotto...', context="selenium_extract_product_raw_data")
    prices_title        = driver.find_element(By.XPATH, "//div[@class='card']//h5[text()='Prices']")
    prices_card         = prices_title.find_element(By.XPATH, "./ancestor::div[@class='card']")
    raw_data['prices'] = prices_card.get_attribute("outerHTML")
    return raw_data, error

def extract_product_data( raw_data ):
    product_data = {}
    try:
        html_soup = BeautifulSoup(raw_data['title'], 'html.parser')
        product_data['title'] = html_soup.find('h4').text
    except Exception as e:
        product_data['title'] = 'Titolo non trovato'
    product_data['img'] = ''
    if raw_data['images']:
        try:
            html_soup = BeautifulSoup(raw_data['images'], 'html.parser')
            img_items = html_soup.find_all('img')
            to_match = ['header', 'Header', 'HEADER', 'capsule', 'Capsule', 'CAPSULE', 'logo', 'Logo', 'LOGO']
            for image in img_items:
                src = image['src']
                for target in to_match:
                    if target in src:
                        product_data['img'] = src
                        break
        except Exception as e:
            pass
    product_data['currencies'] = []
    html_soup = BeautifulSoup(raw_data['prices'], 'html.parser')
    grids = html_soup.find_all('div', class_='grid')
    for grid in grids[1:]:
        temp_item = {}
        currency_code_soup      = grid.find('div', class_='col-3').find('strong')
        currency_code           = currency_code_soup.text.strip().upper()
        if currency_code == 'CIS':
            continue
        temp_item['currency_code']      = currency_code
        temp_item['country_code']       =  get_country_code_string( currency_code )
        try:
            currency_amount = grid.find_all('div', class_='col-3')[-1].text.strip()
            # log(currency_amount, "currency_amount", "extract_product_data")
            if ',' in currency_amount:
                currency_amount = currency_amount.replace(",", "")
            temp_item['currency_amount'] = float( currency_amount )
        except Exception as e:
            temp_item['currency_amount'] = '[errore]'
        product_data['currencies'].append( temp_item )
    product_data['currencies'] = sorted(product_data['currencies'], key=lambda i: i['currency_code'], reverse=False)
    return product_data

def get_country_code_string( currency ):
    countries_list = get_country_code_by_currency( currency )
    if not countries_list:
        return '-'
    if len( countries_list ) == 1:
        return countries_list[0]
    exceptions = {
        'EUR': 'UE',
        'USD': 'US',
        'GBP': 'GB',
        'CHF': 'CH',
        'AUD': 'AU',
        'NZD': 'NZ',
        'ILS': 'IL',
        'NOK': 'NO',
    }
    if currency in exceptions.keys():
        return exceptions[currency]
    return ', '.join( countries_list )

def available_currency_quote( currency ):
    quotes = data_file_get()['quotes']
    if not currency in quotes:
        return False
    currency_data       = quotes[currency]
    last_update         = currency_data['last_update']
    last_update         = datetime.strptime(last_update, DATETIME_ISO_FORMAT)
    now                 = datetime.now()
    time_difference_in_hours = (now - last_update).total_seconds() / 3600
    # log(time_difference_in_hours, "time_difference_in_hours", "available_currency_quote")
    if time_difference_in_hours < DATA_LIFE['quotes']:
        return True
    return False

def get_currency_quotes_api_key():
    api_key = os.environ.get('CURRENCYLAYER_API_KEY', '').strip()
    if not api_key:
        log_error(
            'Manca CURRENCYLAYER_API_KEY. Copia .env.example in .env e inserisci la chiave.',
            context="currency_quotes_api_key",
        )
        return None
    return api_key

# Pseudo-valute ISO 4217 senza tasso di cambio reale (es. USM/USS/USN): l'API dei
# cambi non le supporta e, se inviate, fa fallire l'intera richiesta. Usata come
# fallback quando non e' possibile ottenere la lista ufficiale delle valute supportate.
UNSUPPORTED_CURRENCY_FALLBACK = ['USM', 'USS', 'USN', 'XXX', 'XTS']

# http://apilayer.net/api/list?access_key=xxx
def get_supported_currencies():
    data_file = data_file_get()
    if not data_file:
        data_file = data_file_init()
    cached = data_file.get('supported_currencies')
    if cached and cached.get('last_update') and cached.get('list'):
        last_update = datetime.strptime(cached['last_update'], DATETIME_ISO_FORMAT)
        hours = (datetime.now() - last_update).total_seconds() / 3600
        if hours < DATA_LIFE.get('supported_currencies', 168):
            return set(cached['list'])
    response_data = {}
    api_key = get_currency_quotes_api_key()
    if api_key:
        supported_currencies_api_url = 'http://apilayer.net/api/list?access_key={}'.format(api_key)
        log('Ottengo la lista delle valute supportate', context='get_supported_currencies')
        try:
            r = requests.get( supported_currencies_api_url )
            response_data = r.json()
        except Exception as e:
            log(e, 'Impossibile ottenere la lista delle valute supportate', context='get_supported_currencies', color='light_red')
    if response_data.get('success') and response_data.get('currencies'):
        supported = list( response_data['currencies'].keys() )
        data_file['supported_currencies'] = {
            'list': supported,
            'last_update': datetime.now().strftime( DATETIME_ISO_FORMAT ),
        }
        data_file_save( data_file )
        return set( supported )
    # Fallback: se ho una cache (anche scaduta) la riuso, altrimenti nessuna lista disponibile
    if cached and cached.get('list'):
        return set( cached['list'] )
    return None

# http://apilayer.net/api/live?access_key=xxx&currencies=EUR,GBP&source=USD&format=1
def get_currency_quotes( currencies_list ):
    data_file = data_file_get()
    if not data_file:
        data_file = data_file_init()
    supported = get_supported_currencies()
    if supported is not None:
        bypassed        = [c for c in currencies_list if c not in supported]
        currencies_list = [c for c in currencies_list if c in supported]
    else:
        # Nessuna lista ufficiale disponibile: uso la blacklist minima di codici noti
        bypassed        = [c for c in currencies_list if c in UNSUPPORTED_CURRENCY_FALLBACK]
        currencies_list = [c for c in currencies_list if c not in UNSUPPORTED_CURRENCY_FALLBACK]
    if bypassed:
        log(', '.join(bypassed), 'Valute non supportate ignorate', context='get_currency_quotes', color='yellow')
    if 'EUR' not in currencies_list and 'EUR' not in data_file['quotes']:
        currencies_list.append( 'EUR' )
    if 'GBP' not in currencies_list and 'GBP' not in data_file['quotes']:
        currencies_list.append( 'GBP' )
    currencies_list.sort()
    if not currencies_list:
        # Non resta nulla da aggiornare (valute gia' in cache o tutte ignorate)
        return data_file['quotes']
    currency_quotes_api_key = get_currency_quotes_api_key()
    if not currency_quotes_api_key:
        return {}
    currencies_str = ','.join( currencies_list )
    currency_quotes_api_url = 'http://apilayer.net/api/live?access_key={}&currencies={}&source=USD&format=1'.format(currency_quotes_api_key, currencies_str)
    log(currencies_str, 'Ottengo i tassi di cambio per', context='get_currency_quotes')
    r = requests.get( currency_quotes_api_url )
    response_data = r.json()
    # {
    #     "success":true,
    #     "terms":"https:\/\/currencylayer.com\/terms",
    #     "privacy":"https:\/\/currencylayer.com\/privacy",
    #     "timestamp":1696946103,
    #     "source":"USD",
    #     "quotes":{
    #         "USDEUR":0.94429,
    #         "USDGBP":0.81656
    #     }
    # }
    if not response_data['success']:
        log(response_data['error']['info'], 'Tassi di cambio NON ottenuti', context='get_currency_quotes', color='light_red')
        return {}
    # log('Tassi di cambio ottenuti tramite api', context='get_currency_quotes')
    # log(response_data['quotes'], "response_data['quotes']", context='get_currency_quotes', color="yellow")
    for currency in currencies_list:
        key = 'USD{}'.format( currency )
        data_file['quotes'][currency] = {}
        data_file['quotes'][currency]['quote']              = response_data['quotes'][key]
        data_file['quotes'][currency]['last_update']        = datetime.now().strftime( DATETIME_ISO_FORMAT )
    log('Salvo i le quotazioni su file', context="get_currency_quotes")
    data_file_save( data_file )
    return response_data

def convert_price_to_defaults(product_currencies_data, output_currency):
    quotes = data_file_get()['quotes']
    log('Converto i prezzi in valuta in USD, EUR e GBP', context='convert_price_to_defaults')
    for item in product_currencies_data:
        item['amount_usd'] = '-'
        item['amount_eur'] = '-'
        item['amount_gbp'] = '-'
        if not is_number( item['currency_amount'] ):
            continue
        currency            = item['currency_code']
        if currency not in quotes:
            # Valuta non supportata dall'API dei cambi: la mostriamo senza conversione
            item['unsupported_currency'] = True
            continue
        currency_quote      = quotes[currency]['quote']
        item['amount_usd']      = round(item['currency_amount'] / currency_quote, 2)
        item['quote']           = currency_quote
        if currency not in ['EUR', 'GBP']:
            for currency_key in ['EUR', 'GBP']:
                item['amount_{}'.format(currency_key.lower())] = round(item['amount_usd'] * quotes[currency_key]['quote'], 2)
        else:
            if currency == 'EUR':
                item['amount_eur'] = item['currency_amount']
                item['amount_gbp'] = round(item['amount_usd'] * quotes['GBP']['quote'], 2)
            else:
                item['amount_gbp'] = item['currency_amount']
                item['amount_eur'] = round(item['amount_usd'] * quotes['EUR']['quote'], 2)
    # log(product_currencies_data, "product_currencies_data", "convert_price_to_defaults")
    # I prezzi senza conversione (valute non supportate o importi non validi) hanno
    # amount_usd = '-' : li ordiniamo in fondo per evitare confronti tra float e stringhe.
    def _sort_key( item ):
        amount = item['amount_usd']
        if isinstance(amount, (int, float)):
            return (0, amount)
        return (1, 0)
    sorted_data = sorted(product_currencies_data, key=_sort_key)
    return sorted_data

def is_number( val ):
    try:
        float( val )
        return True
    except ValueError:
        return False

def save_product_data_file(product, sku_id):
    data_file = data_file_get()
    data_file['products']
    data_file['products'][sku_id] = product
    log('Salvo i dati su file', context="save_product_data_file")
    data_file_save( data_file )


# GET /ajax/export-xls
def get_ajax_export_xls( requests_data ):
    response_data           = {}
    upper_dir               = get_root_path()
    now                     = datetime.now()
    name                    = now.strftime( "%Y%m%d-%H%M%S-genba_prices" )
    extension               = 'xlsx'
    filename                = '{}.{}'.format(name, extension)
    exports_dir             = Path( '{}/exports'.format(upper_dir) )
    exports_dir.mkdir( parents=True, exist_ok=True )
    file_path               = exports_dir / filename
    workbook                = xlsxwriter.Workbook( file_path )
    bold                    = workbook.add_format({'bold': True})
    currency_format = workbook.add_format()
    currency_format.set_num_format('0.00')
    worksheet = workbook.add_worksheet( name )
    row = 0
    col = 0
    try:
        for product in requests_data['products']:
            title       = product['data']['title']
            sku_id      = product['sku_id']
            worksheet.write(row, col, title, bold)
            worksheet.write(row, col+1, sku_id)
            worksheet.write(row, col+2, '')
            worksheet.write(row, col+3, '')
            worksheet.write(row, col+4, '')
            worksheet.write(row, col+5, '')
            worksheet.write(row, col+6, '')
            row += 1
            worksheet.write(row, col, 'COUNTRY', bold)
            worksheet.write(row, col+1, 'CURRENCY', bold)
            worksheet.write(row, col+2, 'PRICE IN CURRENCY', bold)
            worksheet.write(row, col+3, 'USD TO CURRENCY QUOTE', bold)
            worksheet.write(row, col+4, 'PRICE IN USD', bold)
            worksheet.write(row, col+5, 'PRICE IN EUR', bold)
            worksheet.write(row, col+6, 'PRICE IN GBP', bold)
            row += 1
            for table_line in product['data']['currencies']:
                worksheet.write(row, col, table_line['country_code'])
                worksheet.write(row, col+1, table_line['currency_code'])
                worksheet.write(row, col+2, table_line['currency_amount'], currency_format)
                worksheet.write(row, col+3, table_line.get('quote', '-'), currency_format)
                worksheet.write(row, col+4, table_line['amount_usd'], currency_format)
                worksheet.write(row, col+5, table_line['amount_eur'], currency_format)
                worksheet.write(row, col+6, table_line['amount_gbp'], currency_format)
                row += 1
            worksheet.write(row, col, '')
            worksheet.write(row, col+1, '')
            worksheet.write(row, col+2, '')
            worksheet.write(row, col+3, '')
            worksheet.write(row, col+4, '')
            worksheet.write(row, col+5, '')
            worksheet.write(row, col+6, '')
            row += 1
        workbook.close()
        response_data['success'] = 1
    except Exception as e:
        log(e, "Errore nell esportazione", "get_ajax_export_xls")
        response_data['success']        = 0
        response_data['info']           = e
    return response_data


# GET /test
def get_test():
    return


def get_genba_product_page_data_old( sku_id ):
    credentials = get_genba_credentials()
    if not credentials:
        return
    driver = selenium_init() 
    driver.get( GENBA_PAGE_URLS['login'] )
    max_retries             = 25
    retries_counter         = 0
    log('Mi loggo su Genba...', context="get_genba_product_page_source")
    while True:
        if retries_counter >= max_retries:
            log('Numero di tentativi massimo raggiunto. Esecuzione terminata.', context="get_genba_product_page_source")
            return
        try:
            driver.find_element(By.ID, 'username' ).send_keys( credentials['username'] )
            driver.find_element(By.ID, 'password' ).send_keys( credentials['password'] )
            driver.find_element(By.ID, 'submitBTN' ).click()
            log('Loggato.', context="get_genba_product_page_source")
            break
        except Exception as e:
            log(e, 'Errore', context="get_genba_product_page_source")
            retries_counter += 1
            sleep(0.2)
            continue
    retries_counter = 0
    paga_data = {}
    driver.set_page_load_timeout( SELENIUM_LOAD_PAGE_TIMEOUT ) # setto un timeout per il caricamento delle pagine
    page_url = GENBA_PAGE_URLS['product'] + sku_id
    log(page_url, 'Apro la pagina prodotto...', context="get_genba_product_page_source", color='light_blue')
    driver.get( page_url )
    log('Sorgente pagina prodotto ottenuto.', context="get_genba_product_page_source")
    sleep( 1 )
    while True:
        if retries_counter >= max_retries:
            log('Numero di tentativi massimo raggiunto. Esecuzione terminata.', context="get_genba_product_page_source")
            driver.quit()
            return paga_data
        try:
            page_source = driver.page_source
            paga_data['page']           = page_source
            paga_data['prices']         = []
            table               = ''
            aside               = driver.find_element(By.ID, 'rightAside' )
            article_list        = aside.find_elements(By.TAG_NAME, 'article')
            log('Cerco la tabella prezzi...', context="get_genba_product_page_source")
            for article in article_list:
                h3 = article.find_element(By.TAG_NAME, 'h3' )
                if h3.text.lower() == 'prices':
                    log('Trovata.', context="get_genba_product_page_source")
                    table = article.find_element(By.TAG_NAME, 'table')
                    tbody = table.find_element(By.TAG_NAME, 'tbody')
                    prices_source = tbody.find_elements(By.TAG_NAME, 'tr')
                    log('Aspetto che la tabella venga popolata... ({})'.format( retries_counter ), context="get_genba_product_page_source")
                    # Se al 5o tentativo c' e ancora solo una riga nella tabella e perche probabilmente e l'unico prezzo (prodotto worldwide) quindi restituisco solo il prezzo default
                    if len( prices_source ) == 1 and retries_counter == 4:
                        paga_data['prices'].append( prices_source[0].get_attribute('innerHTML') )
                        log('Dati tabella prezzi ottenuti. Probabile prodotto worldwide.', context="get_genba_product_page_source")
                        return paga_data
                    if len( prices_source ) > 1:
                        for tr in prices_source:
                            paga_data['prices'].append( tr.get_attribute('innerHTML') )
                        log('Dati tabella prezzi ottenuti.', context="get_genba_product_page_source")
                        driver.quit()
                        return paga_data
                    retries_counter += 1
            if not table:
                log('Tabella prezzi non trovata.', context="get_genba_product_page_source")
                return paga_data
        except Exception as e:
            print( 'Errore: {}'.format( e ) )
            retries_counter += 1
            sleep(0.2)
            continue
