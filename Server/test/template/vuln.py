import sqlite3
import os
import pickle
import base64

def get_user(username: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()

def ping_host(hostname: str):
    command = f"ping -c 4 {hostname}"
    os.system(command)

def load_session(session_data: str):
    data = base64.b64decode(session_data)
    session = pickle.loads(data)
    return session

def read_file(filepath: str):
    base_dir = "/var/www/html/public/"
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, 'r') as f:
        return f.read()

def process_xml(xml_content: str):
    import xml.etree.ElementTree as ET
    tree = ET.fromstring(xml_content)
    return tree.tag
