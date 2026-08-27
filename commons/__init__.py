
#!/usr/bin/env python3

import os, sys, requests, json
from pathlib import Path
from datetime import datetime, timezone
from time import sleep
from dotenv import load_dotenv
from termcolor import colored, cprint


def log(var, text='', context=None, color=None):
    if not context:
        context = 'DEBUG LOG'
    if text:
        to_print = '### {} ### {}: {}'.format(context.upper(), text, var)
    else:
        to_print = '### {} ### {}'.format(context.upper(), var)
    if color:
        to_print = colored(to_print, color)
    print(to_print, file=sys.stdout)
    return

def log_error(var, text='', context=None):
    return log(var, text, context, color='red')

def get_root_path():
    # La root e' la cartella che contiene il package commons, indipendentemente
    # da come e' stata rinominata la cartella del progetto.
    return Path( __file__ ).resolve().parent.parent

load_dotenv( get_root_path() / '.env' )

def get_country_code_by_currency( currency ):
    currency_to_country = {"BDT": ["BD"], "EUR": ["BE", "BL", "RE", "GR", "GP", "GF", "PT", "PM", "EE", "IT", "ES", "ME", "MF", "MC", "MT", "MQ", "FR", "FI", "NL", "XK", "CY", "SK", "SI", "SM", "DE", "YT", "LV", "LU", "TF", "VA", "AD", "AT", "AX", "IE"], "XOF": ["BF", "BJ", "GW", "ML", "NE", "CI", "SN", "TG"], "BGN": ["BG"], "BAM": ["BA"], "BBD": ["BB"], "XPF": ["WF", "PF", "NC"], "BMD": ["BM"], "BND": ["BN"], "BOB": ["BO"], "BHD": ["BH"], "BIF": ["BI"], "BTN": ["BT"], "JMD": ["JM"], "NOK": ["BV", "SJ", "NO"], "BWP": ["BW"], "WST": ["WS"], "USD": ["BQ", "TL", "GU", "SV", "PR", "PW", "EC", "MH", "MP", "IO", "FM", "VG", "US", "UM", "TC", "VI", "AS"], "BRL": ["BR"], "BSD": ["BS"], "GBP": ["JE", "GS", "GG", "GB", "IM"], "BYR": ["BY"], "BZD": ["BZ"], "RUB": ["RU"], "RWF": ["RW"], "RSD": ["RS"], "TMT": ["TM"], "TJS": ["TJ"], "RON": ["RO"], "NZD": ["TK", "PN", "NZ", "NU", "CK"], "GTQ": ["GT"], "XAF": ["GQ", "GA", "CM", "CG", "CF", "TD"], "JPY": ["JP"], "GYD": ["GY"], "GEL": ["GE"], "XCD": ["GD", "MS", "KN", "DM", "LC", "VC", "AG", "AI"], "GNF": ["GN"], "GMD": ["GM"], "DKK": ["GL", "FO", "DK"], "GIP": ["GI"], "GHS": ["GH"], "OMR": ["OM"], "TND": ["TN"], "JOD": ["JO"], "HRK": ["HR"], "HTG": ["HT"], "HUF": ["HU"], "HKD": ["HK"], "HNL": ["HN"], "AUD": ["HM", "NF", "NR", "CC", "CX", "KI", "TV", "AU"], "VEF": ["VE"], "ILS": ["PS", "IL"], "PYG": ["PY"], "IQD": ["IQ"], "PAB": ["PA"], "PGK": ["PG"], "PEN": ["PE"], "PKR": ["PK"], "PHP": ["PH"], "PLN": ["PL"], "ZMK": ["ZM"], "MAD": ["EH", "MA"], "EGP": ["EG"], "ZAR": ["ZA"], "VND": ["VN"], "SBD": ["SB"], "ETB": ["ET"], "SOS": ["SO"], "ZWL": ["ZW"], "SAR": ["SA"], "ERN": ["ER"], "MDL": ["MD"], "MGA": ["MG"], "UZS": ["UZ"], "MMK": ["MM"], "MOP": ["MO"], "MNT": ["MN"], "MKD": ["MK"], "MUR": ["MU"], "MWK": ["MW"], "MVR": ["MV"], "MRO": ["MR"], "UGX": ["UG"], "TZS": ["TZ"], "MYR": ["MY"], "MXN": ["MX"], "SHP": ["SH"], "FJD": ["FJ"], "FKP": ["FK"], "NIO": ["NI"], "NAD": ["NA"], "VUV": ["VU"], "NGN": ["NG"], "NPR": ["NP"], "CHF": ["CH", "LI"], "COP": ["CO"], "CNY": ["CN"], "CLP": ["CL"], "CAD": ["CA"], "CDF": ["CD"], "CZK": ["CZ"], "CRC": ["CR"], "ANG": ["CW", "SX"], "CVE": ["CV"], "CUP": ["CU"], "SZL": ["SZ"], "SYP": ["SY"], "KGS": ["KG"], "KES": ["KE"], "SSP": ["SS"], "SRD": ["SR"], "KHR": ["KH"], "KMF": ["KM"], "STD": ["ST"], "KRW": ["KR"], "KPW": ["KP"], "KWD": ["KW"], "SLL": ["SL"], "SCR": ["SC"], "KZT": ["KZ"], "KYD": ["KY"], "SGD": ["SG"], "SEK": ["SE"], "SDG": ["SD"], "DOP": ["DO"], "DJF": ["DJ"], "YER": ["YE"], "DZD": ["DZ"], "UYU": ["UY"], "LBP": ["LB"], "LAK": ["LA"], "TWD": ["TW"], "TTD": ["TT"], "TRY": ["TR"], "LKR": ["LK"], "TOP": ["TO"], "LTL": ["LT"], "LRD": ["LR"], "LSL": ["LS"], "THB": ["TH"], "LYD": ["LY"], "AED": ["AE"], "AFN": ["AF"], "ISK": ["IS"], "IRR": ["IR"], "AMD": ["AM"], "ALL": ["AL"], "AOA": ["AO"], "ARS": ["AR"], "AWG": ["AW"], "INR": ["IN"], "AZN": ["AZ"], "IDR": ["ID"], "UAH": ["UA"], "QAR": ["QA"], "MZN": ["MZ"]}
    if not currency in currency_to_country.keys():
        return None
    return currency_to_country[currency]

PROJECT_ROOT = 'bot_prezzi_genba'

VERSION_FILE_PATH               = get_root_path() / 'version.json'
APP_NAME_FALLBACK               = 'Genba price scraper'
APP_VERSION_FALLBACK            = 'sconosciuta'

def get_app_info():
    try:
        with open(VERSION_FILE_PATH, 'r') as f:
            file_content = json.load( f )
    except (OSError, ValueError) as e:
        log_error(e, 'Impossibile leggere version.json', context='get_app_info')
        return {'name': APP_NAME_FALLBACK, 'version': APP_VERSION_FALLBACK}
    return {
        'name':     str( file_content.get('name', APP_NAME_FALLBACK) ),
        'version':  str( file_content.get('version', APP_VERSION_FALLBACK) ),
    }

def get_app_version():
    return get_app_info()['version']

APP_INFO        = get_app_info()
APP_NAME        = APP_INFO['name']
APP_VERSION     = APP_INFO['version']

DATETIME_ISO_FORMAT             = '%Y-%m-%dT%H:%M:%S'
DATETIME_READABLE_FORMAT        = '%d %b %Y %H:%M:%S'