import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from flask import Flask, render_template
import webbrowser
from threading import Timer
import configparser
import os
import re

# --- Configurações ---
GLPI_URL_BASE = 'https://chamados.slmandic.edu.br'
URL_FORMULARIO_LOGIN = f'{GLPI_URL_BASE}/glpi/index.php?noAUTO=1'
URL_POST_LOGIN = f'{GLPI_URL_BASE}/glpi/front/login.php'

# --- Credencias simbólicas ---
GLPI_USER = ""
GLPI_PASSWORD = ""

if os.path.exists('config.ini'):
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        GLPI_USER = config['GLPI']['USUARIO']
        GLPI_PASSWORD = config['GLPI']['SENHA']
    except KeyError: pass

# --- URLs das filas dos analistas ---
URL_N1 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=notold&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=74&search=Pesquisar&itemtype=Ticket&start=0"""
URL_N2 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&search=Pesquisar&itemtype=Ticket&savedsearches_id=765&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=notold&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=75&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=6&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=0&reset=reset"""
URL_N3 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&search=Pesquisar&itemtype=Ticket&savedsearches_id=778&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=notold&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=76&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=6&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=0&reset=reset"""
URL_ATRASADOS = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?criteria%5B1%5D%5Blink%5D=OR&criteria%5B1%5D%5Bfield%5D=12&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=4&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=5&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=0&criteria%5B3%5D%5Blink%5D=AND&criteria%5B3%5D%5Bfield%5D=8&criteria%5B3%5D%5Bsearchtype%5D=equals&criteria%5B3%5D%5Bvalue%5D=0&search=Pesquisar&itemtype=Ticket&start=0"""

# --- URLs Rranking dos analistas >50 chamados  ---
URL_RANKING_N1 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=old&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=74&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=16&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=TODAY&search=Pesquisar&itemtype=Ticket&start=0&glpilist_limit=50"""
URL_RANKING_N2 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=old&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=75&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=16&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=TODAY&search=Pesquisar&itemtype=Ticket&start=0&glpilist_limit=50"""
URL_RANKING_N3 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=old&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=76&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=16&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=TODAY&search=Pesquisar&itemtype=Ticket&start=0&glpilist_limit=50"""

INDICE_COLUNA_TECNICO = 8
app = Flask(__name__)

# --- FUNÇÕES (Retornando ao padrão original) ---

def fazer_login(session):
    print("Iniciando missão: Fazer Login...")
    try:
        # Acesso simples, sem headers complexos
        r = session.get(URL_FORMULARIO_LOGIN, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        try: user_field = soup.find('input', {'id': 'login_name'})['name']
        except: user_field = 'login_name'
        try: pass_field = soup.find('input', {'id': 'login_password'})['name']
        except: pass_field = 'login_password'
        try: token = soup.find('input', {'name': '_glpi_csrf_token'})['value']
        except: token = ''

        payload = {
            user_field: GLPI_USER,
            pass_field: GLPI_PASSWORD,
            '_glpi_csrf_token': token,
            'submit': 'Enviar',
            'noAUTO': '1'
        }
        post = session.post(URL_POST_LOGIN, data=payload, timeout=10)
        
        # Sem acessar Home extra, login puro e simples
        return "Sair" in post.text or "preference.php" in post.text
    except: return False

def calcular_tempo(texto):
    texto = texto.strip()
    formatos = ["%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(texto, fmt)
            delta = datetime.now() - dt
            return f"{delta.days}d {delta.seconds//3600}h", delta.days
        except: continue
    return "--", 0

def analisar_fila(session, url, nome):
    print(f"  - Analisando {nome}...")
    info = {'total': 0, 'tempo': '--', 'dias': 0}
    try:
        r = session.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        el = soup.find('td', class_='tab_bg_2 b')
        if el:
            try: info['total'] = int(el.text.strip().split()[-1])
            except: pass
        
        if info['total'] > 0:
            # Tenta achar a tabela com a classe nova OU antiga
            tabela = soup.find('table', class_='tab_cadrehov')
            if not tabela: tabela = soup.find('table', class_='tab_cadre_fixehov')
            
            if tabela:
                for tr in tabela.find_all('tr'):
                    if 'tab_bg_' in str(tr.get('class', [])):
                        cols = tr.find_all('td')
                        for col in cols:
                            if re.search(r'\d{2}[-/]\d{2}[-/]\d{4}\s\d{2}:\d{2}', col.text):
                                info['tempo'], info['dias'] = calcular_tempo(col.text)
                                break
                        break
        return info
    except: return info

def buscar_ids_atrasados(session, url):
    print("  - Caçando Atrasados...")
    ids = []
    try:
        r = session.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if 'ticket.form.php' in a['href'] and 'id=' in a['href']:
                m = re.search(r'id=(\d+)', a['href'])
                if m: 
                    val = m.group(1)
                    if val != '0' and val not in ids: ids.append(val)
        return sorted(list(set(ids)))
    except: return []

def gerar_ranking(session, url):
    # print("  - Calculando Ranking...")
    ranking = {}
    try:
        r = session.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tabela = soup.find('table', class_='tab_cadrehov')
        if not tabela: tabela = soup.find('table', class_='tab_cadre_fixehov')
        if not tabela: return []

        for tr in tabela.find_all('tr'):
            if 'tab_bg_' not in str(tr.get('class', [])): continue
            cols = tr.find_all('td')
            if len(cols) > INDICE_COLUNA_TECNICO:
                try:
                    textos = list(cols[INDICE_COLUNA_TECNICO].stripped_strings)
                    if textos:
                        n = textos[0].strip()
                        if n and "Técnico" not in n: ranking[n] = ranking.get(n, 0) + 1
                except: continue
        return sorted(ranking.items(), key=lambda x: x[1], reverse=True)
    except: return []

@app.route('/')
def index():
    s = requests.Session()
    dados = {
        'n1': {'total':0}, 'n2':{'total':0}, 'n3':{'total':0}, 
        'atrasados_ids': [], 'atrasados_total': 0, 
        'rank_n1': [], 'rank_n2': [], 'rank_n3': []
    }
    msg, erro = "Iniciando...", None

    if fazer_login(s):
        msg = "Login OK."
        dados['n1'] = analisar_fila(s, URL_N1, "N1")
        dados['n2'] = analisar_fila(s, URL_N2, "N2")
        dados['n3'] = analisar_fila(s, URL_N3, "N3")
        dados['atrasados_ids'] = buscar_ids_atrasados(s, URL_ATRASADOS)
        dados['atrasados_total'] = len(dados['atrasados_ids'])
        
        print("  - Gerando Rankings N1, N2, N3...")
        dados['rank_n1'] = gerar_ranking(s, URL_RANKING_N1)
        dados['rank_n2'] = gerar_ranking(s, URL_RANKING_N2)
        dados['rank_n3'] = gerar_ranking(s, URL_RANKING_N3)
        
        msg = "Atualizado"
    else:
        msg = "Falha Login"
        erro = "Verifique senha"

    return render_template('vigia.html', dados=dados, msg=msg, erro=erro, 
                           agora=datetime.now().strftime('%d/%m/%Y %H:%M:%S'), base=GLPI_URL_BASE)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)