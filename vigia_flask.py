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
import sys

# --- CONFIGURAÇÕES ---
GLPI_URL_BASE = 'https://chamados.slmandic.edu.br'
URL_FORMULARIO_LOGIN = f'{GLPI_URL_BASE}/glpi/index.php?noAUTO=1'
URL_POST_LOGIN = f'{GLPI_URL_BASE}/glpi/front/login.php'
URL_HOME = f'{GLPI_URL_BASE}/glpi/front/central.php'

# --- CREDENCIAIS ---
GLPI_USER = ""
GLPI_PASSWORD = ""

# [SEU BLOCO ORIGINAL - SIMPLES E FUNCIONAL]
if os.path.exists('config.ini'):
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        GLPI_USER = config['GLPI']['USUARIO']
        GLPI_PASSWORD = config['GLPI']['SENHA']
    except KeyError: pass

# --- URLs FILAS ---
URL_N1 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=notold&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=74&search=Pesquisar&itemtype=Ticket&start=0"""
URL_N2 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&search=Pesquisar&itemtype=Ticket&savedsearches_id=765&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=notold&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=75&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=6&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=0&reset=reset"""
URL_N3 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&search=Pesquisar&itemtype=Ticket&savedsearches_id=778&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=notold&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=76&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=6&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=0&reset=reset"""
URL_ATRASADOS = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?criteria%5B1%5D%5Blink%5D=OR&criteria%5B1%5D%5Bfield%5D=12&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=4&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=5&criteria%5B2%5D%5Bsearchtype%5D=equals&criteria%5B2%5D%5Bvalue%5D=0&criteria%5B3%5D%5Blink%5D=AND&criteria%5B3%5D%5Bfield%5D=8&criteria%5B3%5D%5Bsearchtype%5D=equals&criteria%5B3%5D%5Bvalue%5D=0&search=Pesquisar&itemtype=Ticket&start=0"""

# --- URLs NOVOS E RANKING ---
URL_NOVOS = f"{GLPI_URL_BASE}/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=1&search=Pesquisar&itemtype=Ticket&start=0&sort=15&order=ASC"
URL_CRIADOS_HOJE = f"{GLPI_URL_BASE}/glpi/front/ticket.php?is_deleted=0&criteria%5B0%5D%5Bfield%5D=15&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=TODAY&search=Pesquisar&itemtype=Ticket"
URL_CRIADOS_ONTEM = f"{GLPI_URL_BASE}/glpi/front/ticket.php?is_deleted=0&criteria%5B0%5D%5Bfield%5D=15&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=-1DAY&search=Pesquisar&itemtype=Ticket"

URL_RANK_N1 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=old&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=74&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=16&criteria%5B2%5D%5Bsearchtype%5D=equals&_select_criteria%5B2%5D%5Bvalue%5D=BEGINMONTH&criteria%5B2%5D%5Bvalue%5D=BEGINMONTH&search=Pesquisar&itemtype=Ticket&start=0&glpilist_limit=50"""
URL_RANK_N2 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=old&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=75&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=16&criteria%5B2%5D%5Bsearchtype%5D=equals&_select_criteria%5B2%5D%5Bvalue%5D=BEGINMONTH&criteria%5B2%5D%5Bvalue%5D=BEGINMONTH&search=Pesquisar&itemtype=Ticket&start=0&glpilist_limit=50"""
URL_RANK_N3 = """https://chamados.slmandic.edu.br/glpi/front/ticket.php?is_deleted=0&as_map=0&criteria%5B0%5D%5Blink%5D=AND&criteria%5B0%5D%5Bfield%5D=12&criteria%5B0%5D%5Bsearchtype%5D=equals&criteria%5B0%5D%5Bvalue%5D=old&criteria%5B1%5D%5Blink%5D=AND&criteria%5B1%5D%5Bfield%5D=8&criteria%5B1%5D%5Bsearchtype%5D=equals&criteria%5B1%5D%5Bvalue%5D=76&criteria%5B2%5D%5Blink%5D=AND&criteria%5B2%5D%5Bfield%5D=16&criteria%5B2%5D%5Bsearchtype%5D=equals&_select_criteria%5B2%5D%5Bvalue%5D=BEGINMONTH&criteria%5B2%5D%5Bvalue%5D=BEGINMONTH&search=Pesquisar&itemtype=Ticket&start=0&glpilist_limit=50"""

INDICE_COLUNA_TECNICO = 8
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}

if getattr(sys, 'frozen', False):
    pasta_templates = os.path.join(sys._MEIPASS, 'templates')
else:
    pasta_templates = 'templates'
app = Flask(__name__, template_folder=pasta_templates)

# --- FUNÇÕES ---

def fazer_login(session):
    print("Iniciando missão: Fazer Login...")
    try:
        # Login simples sem headers excessivos
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
        
        # Acessar Home é necessário para firmar sessão, senão Ranking falha
        if "Sair" in post.text or "preference.php" in post.text:
            session.get(URL_HOME, timeout=10)
            return True
        return False
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

def calcular_minutos_atraso(texto_data):
    texto_data = texto_data.strip()
    formatos = ["%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%y %H:%M"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(texto_data, fmt)
            delta = datetime.now() - dt
            return int(delta.total_seconds() / 60)
        except: continue
    return 0

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
        
        if info['total'] == 0:
            for td in soup.find_all(['td', 'th']):
                m = re.search(r'de\s+(\d+)\s*$', td.get_text().strip(), re.IGNORECASE)
                if m: info['total'] = int(m.group(1)); break

        if info['total'] > 0:
            tabela = soup.find('table', class_='tab_cadrehov') or soup.find('table', class_='tab_cadre_fixehov')
            if tabela:
                for tr in tabela.find_all('tr'):
                    if 'tab_bg_' in str(tr.get('class', [])):
                        for col in tr.find_all('td'):
                            if re.search(r'\d{2}[-/]\d{2}[-/]\d{4}\s\d{2}:\d{2}', col.text):
                                info['tempo'], info['dias'] = calcular_tempo(col.text)
                                break
                        break
        return info
    except: return info

# --- FUNÇÕES DE NOVOS ---
def analisar_sla_novos(session):
    count_criticos = 0
    try:
        # Usamos headers simples aqui para garantir que o GLPI não bloqueie
        # Mas se o login foi sem headers, aqui também pode ir sem ou com User-Agent basico
        h_simples = {'User-Agent': 'Mozilla/5.0'}
        r = session.get(URL_NOVOS, headers=h_simples, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tabela = soup.find('table', class_='tab_cadrehov') or soup.find('table', class_='tab_cadre_fixehov')
        if not tabela: return 0

        for tr in tabela.find_all('tr'):
            if 'tab_bg_' in str(tr.get('class', [])): continue
            for col in tr.find_all('td'):
                txt = col.get_text().strip()
                if re.search(r'\d{2}[-/]\d{2}.*\d{2}:\d{2}', txt):
                    minutos = calcular_minutos_atraso(txt)
                    if minutos > 30: count_criticos += 1
                    break
        return count_criticos
    except: return 0

def buscar_ids_novos(session, url):
    ids = []
    try:
        h_simples = {'User-Agent': 'Mozilla/5.0'}
        r = session.get(url, headers=h_simples, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if 'ticket.form.php' in a['href'] and 'id=' in a['href']:
                try:
                    m = re.search(r'id=(\d+)', a['href'])
                    if m: ids.append(m.group(1))
                except: continue
        return sorted(list(set(ids)))
    except: return []
# ------------------------

def buscar_ids_atrasados(session, url):
    ids = []
    try:
        r = session.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if 'ticket.form.php' in a['href'] and 'id=' in a['href']:
                try:
                    m = re.search(r'id=(\d+)', a['href'])
                    if m: ids.append(m.group(1))
                except: continue
        return sorted(list(set(ids)))
    except: return []

def gerar_ranking(session, url):
    ranking = {}
    try:
        # Referer ajuda a não cair a sessão no relatório
        h_rank = {'Referer': URL_HOME}
        r = session.get(url, headers=h_rank, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        tabela = soup.find('table', class_='tab_cadrehov') or soup.find('table', class_='tab_cadre_fixehov')
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
        'novos': {'total':0, 'criados_hoje':0, 'criados_ontem':0, 'variacao':0, 'criticos':0, 'ids':[]},
        'n1': {'total':0, 'tempo':'--', 'dias':0}, 
        'n2': {'total':0, 'tempo':'--', 'dias':0}, 
        'n3': {'total':0, 'tempo':'--', 'dias':0}, 
        'n1n2': {'total': 0, 'tempo': '--'},
        'atrasados_ids': [], 'atrasados_total': 0, 
        'rank_n1': [], 'rank_n2': [], 'rank_n3': []
    }
    msg, erro = "Iniciando...", None

    if fazer_login(s):
        msg = "Login OK."
        
        # 1. Novos
        dados['novos'] = analisar_fila(s, URL_NOVOS, "Novos")
        dados['novos']['criticos'] = analisar_sla_novos(s)
        dados['novos']['ids'] = buscar_ids_novos(s, URL_NOVOS)
        
        try:
            h = analisar_fila(s, URL_CRIADOS_HOJE, "H")['total']
            o = analisar_fila(s, URL_CRIADOS_ONTEM, "O")['total']
            dados['novos'].update({'criados_hoje': h, 'criados_ontem': o, 'variacao': h - o})
        except: pass

        # 2. Filas
        dados['n1'] = analisar_fila(s, URL_N1, "N1")
        dados['n2'] = analisar_fila(s, URL_N2, "N2")
        dados['n3'] = analisar_fila(s, URL_N3, "N3")
        
        # Fusão
        dados['n1n2']['total'] = dados['n1']['total'] + dados['n2']['total']
        if dados['n1']['dias'] >= dados['n2']['dias']:
             dados['n1n2']['tempo'] = dados['n1']['tempo']
        else:
             dados['n1n2']['tempo'] = dados['n2']['tempo']

        # 3. Atrasados
        dados['atrasados_ids'] = buscar_ids_atrasados(s, URL_ATRASADOS)
        dados['atrasados_total'] = len(dados['atrasados_ids'])
        
        # 4. Rankings
        print("  - Buscando Rankings...")
        dados['rank_n1'] = gerar_ranking(s, URL_RANK_N1)
        dados['rank_n2'] = gerar_ranking(s, URL_RANK_N2)
        dados['rank_n3'] = gerar_ranking(s, URL_RANK_N3)
        
        msg = "Atualizado"
    else:
        msg = "Falha Login"
        erro = "Verifique senha no config.ini"

    return render_template('vigia.html', dados=dados, msg=msg, erro=erro, 
                           agora=datetime.now().strftime('%d/%m/%Y %H:%M:%S'), base=GLPI_URL_BASE)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)