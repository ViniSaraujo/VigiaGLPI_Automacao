import mysql.connector
from flask import Flask, render_template, jsonify, request, Response
from datetime import datetime, timedelta
from functools import wraps
import logging
import sys
import os

# Mantem terminal limpo
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ==============================================================================
# 🔒 Credencias de Acesso

PAINEL_USER = "admin"
PAINEL_PASS = ""  # -- Onde defini a senha para logar no site do Flask

# ==============================================================================
# Config do database

DB_HOST = "---------------------------------------"
DB_USER = "infra_monitor"
DB_PASS = "" 
DB_NAME = "slmglpi"
DB_PORT = 3306

# Filtros dos Analistas
ENTITY_ID = 5
DATA_CORTE = "2023-01-14 00:00:00"
GRUPOS_INFRA = "74, 75, 76"
ID_N1, ID_N2, ID_N3 = 74, 75, 76

# SLA (16h Úteis)
HORA_INICIO, HORA_FIM, LIMITE_MINUTOS_UTEIS = 8, 18, 16 * 60 

# Ajuste de pasta para executável ou script
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
else:
    template_folder = 'templates'

app = Flask(__name__, template_folder=template_folder)

# Sistema de login do site ( Http Basica Autenticação)
def check_auth(username, password):
    return username == PAINEL_USER and password == PAINEL_PASS

def authenticate():
    return Response(
    'Acesso Negado. Faça login para visualizar o Painel Vigia.\n', 401,
    {'WWW-Authenticate': 'Basic realm="Login Necessario"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/favicon.ico')
def favicon(): return "", 204

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, 
            database=DB_NAME, port=DB_PORT, connect_timeout=10
        )
        return conn
    except: return None

# --- Logica que carrega em horas úteis
def calcular_tempo_util(data_criacao):
    agora = datetime.now()
    cursor = data_criacao
    minutos = 0
    if cursor > agora: return 0
    while cursor < agora:
        if cursor.weekday() >= 5:
            cursor += timedelta(days=(7 - cursor.weekday()))
            cursor = cursor.replace(hour=HORA_INICIO, minute=0, second=0)
            continue
        if cursor.hour < HORA_INICIO:
            cursor = cursor.replace(hour=HORA_INICIO, minute=0, second=0)
            continue
        if cursor.hour >= HORA_FIM:
            cursor += timedelta(days=1)
            cursor = cursor.replace(hour=HORA_INICIO, minute=0, second=0)
            continue
        fim_hoje = cursor.replace(hour=HORA_FIM, minute=0, second=0)
        limite = min(agora, fim_hoje)
        if limite > cursor:
            minutos += (limite - cursor).total_seconds() / 60
            cursor = limite
        if cursor.hour >= HORA_FIM:
            cursor += timedelta(days=1)
            cursor = cursor.replace(hour=HORA_INICIO, minute=0, second=0)
    return minutos

# --- Queries --
def get_atrasados_16h(cursor):
    query = f"""
        SELECT id, date FROM glpi_tickets 
        WHERE is_deleted=0 AND status IN (2, 4) 
        AND entities_id={ENTITY_ID} AND date > '{DATA_CORTE}'
        AND id IN (SELECT tickets_id FROM glpi_groups_tickets WHERE groups_id IN ({GRUPOS_INFRA}))
    """
    cursor.execute(query)
    candidatos = cursor.fetchall()
    ids_atrasados = []
    for tid, dt in candidatos:
        if dt and calcular_tempo_util(dt) > LIMITE_MINUTOS_UTEIS:
            ids_atrasados.append(str(tid))
    return sorted(ids_atrasados)[:50]

def get_novos(cursor):
    cursor.execute(f"SELECT COUNT(id) FROM glpi_tickets WHERE is_deleted=0 AND status=1 AND entities_id={ENTITY_ID} AND date > '{DATA_CORTE}'")
    total = cursor.fetchone()[0]
    cursor.execute(f"SELECT id FROM glpi_tickets WHERE status=1 AND is_deleted=0 AND entities_id={ENTITY_ID} ORDER BY date ASC LIMIT 20")
    ids = [str(r[0]) for r in cursor.fetchall()]
    cursor.execute(f"SELECT COUNT(id) FROM glpi_tickets WHERE status=1 AND is_deleted=0 AND entities_id={ENTITY_ID} AND date < DATE_SUB(NOW(), INTERVAL 30 MINUTE)")
    criticos = cursor.fetchone()[0]
    hoje = datetime.now().strftime('%Y-%m-%d')
    ontem = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.execute(f"SELECT COUNT(id) FROM glpi_tickets WHERE date LIKE '{hoje}%' AND is_deleted=0 AND entities_id={ENTITY_ID}")
    h = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(id) FROM glpi_tickets WHERE date LIKE '{ontem}%' AND is_deleted=0 AND entities_id={ENTITY_ID}")
    o = cursor.fetchone()[0]
    return {'total': total, 'ids': ids, 'criticos': criticos, 'variacao': h - o, 'criados_hoje': h}

def get_stats_hoje(cursor):
    stats = {'criados_hoje': 0, 'solucionados_hoje': 0}
    try:
        q = f"SELECT COUNT(DISTINCT t.id) FROM glpi_tickets t JOIN glpi_groups_tickets gt ON t.id=gt.tickets_id WHERE t.is_deleted=0 AND CAST(t.date AS DATE)=CAST(NOW() AS DATE) AND gt.groups_id IN ({GRUPOS_INFRA}) AND t.entities_id={ENTITY_ID}"
        cursor.execute(q)
        stats['criados_hoje'] = cursor.fetchone()[0]
        q = f"SELECT COUNT(DISTINCT t.id) FROM glpi_tickets t JOIN glpi_groups_tickets gt ON t.id=gt.tickets_id WHERE t.is_deleted=0 AND CAST(t.solvedate AS DATE)=CAST(NOW() AS DATE) AND gt.groups_id IN ({GRUPOS_INFRA}) AND t.entities_id={ENTITY_ID}"
        cursor.execute(q)
        stats['solucionados_hoje'] = cursor.fetchone()[0]
    except: pass
    return stats

def get_stats_mensais(cursor):
    stats = {'criados_mes': 0, 'solucionados_mes': 0}
    try:
        cursor.execute(f"SELECT COUNT(t.id) FROM glpi_tickets t JOIN glpi_groups_tickets gt ON t.id=gt.tickets_id WHERE t.is_deleted=0 AND MONTH(t.date)=MONTH(CURRENT_DATE()) AND YEAR(t.date)=YEAR(CURRENT_DATE()) AND gt.groups_id IN ({GRUPOS_INFRA}) AND t.entities_id={ENTITY_ID}")
        stats['criados_mes'] = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(t.id) FROM glpi_tickets t JOIN glpi_groups_tickets gt ON t.id=gt.tickets_id WHERE t.is_deleted=0 AND MONTH(t.solvedate)=MONTH(CURRENT_DATE()) AND YEAR(t.solvedate)=YEAR(CURRENT_DATE()) AND gt.groups_id IN ({GRUPOS_INFRA}) AND t.entities_id={ENTITY_ID}")
        stats['solucionados_mes'] = cursor.fetchone()[0]
    except: pass
    return stats

def get_fila_grupo(cursor, group_id):
    q = f"SELECT COUNT(t.id), MIN(t.date) FROM glpi_tickets t JOIN glpi_groups_tickets gt ON t.id=gt.tickets_id WHERE gt.groups_id={group_id} AND t.status IN (2,3,4) AND t.is_deleted=0 AND t.entities_id={ENTITY_ID} AND t.date > '{DATA_CORTE}'"
    cursor.execute(q)
    row = cursor.fetchone()
    total = row[0] if row else 0
    tempo = "--"
    dias = 0
    if row and row[1]:
        delta = datetime.now() - row[1]
        dias = delta.days
        horas = delta.seconds // 3600
        tempo = f"{dias}d {horas}h" if dias > 0 else f"{horas}h"
    return {'total': total, 'tempo': tempo, 'dias': dias}

def get_ranking(cursor, group_id):
    inicio_mes = datetime.now().strftime('%Y-%m-01 00:00:00')
    q = f"SELECT CONCAT(u.firstname, ' ', u.realname), COUNT(t.id) FROM glpi_tickets t JOIN glpi_tickets_users tu ON t.id=tu.tickets_id AND tu.type=2 JOIN glpi_users u ON tu.users_id=u.id JOIN glpi_groups_tickets gt ON t.id=gt.tickets_id WHERE gt.groups_id={group_id} AND t.status IN (5,6) AND t.solvedate >= '{inicio_mes}' AND t.is_deleted=0 AND t.entities_id={ENTITY_ID} GROUP BY u.id ORDER BY 2 DESC LIMIT 50"
    cursor.execute(q)
    return cursor.fetchall()

def coletar_todos_dados():
    conn = get_db_connection()
    dados = {
        'stats_hoje': {'criados_hoje': 0, 'solucionados_hoje': 0},
        'stats_mes': {'criados_mes': 0, 'solucionados_mes': 0},
        'novos': {'total':0, 'ids':[], 'variacao':0, 'criticos':0},
        'n1': {'total':0}, 'n2': {'total':0}, 'n3': {'total':0}, 'n1n2': {'total':0, 'tempo':'--'},
        'atrasados_ids': [], 'atrasados_total': 0,
        'rank_n1': [], 'rank_n2': [], 'rank_n3': []
    }
    if conn:
        try:
            cursor = conn.cursor()
            novos_data = get_novos(cursor)
            dados['novos'] = novos_data
            
            st_hoje = get_stats_hoje(cursor)
            dados['stats_hoje']['criados_hoje'] = novos_data['criados_hoje']
            dados['stats_hoje']['solucionados_hoje'] = st_hoje['solucionados_hoje']
            
            dados['stats_mes'] = get_stats_mensais(cursor)
            dados['n1'] = get_fila_grupo(cursor, ID_N1)
            dados['n2'] = get_fila_grupo(cursor, ID_N2)
            dados['n3'] = get_fila_grupo(cursor, ID_N3)
            
            dados['n1n2']['total'] = dados['n1']['total'] + dados['n2']['total']
            dados['n1n2']['tempo'] = dados['n1']['tempo'] if dados['n1']['dias'] >= dados['n2']['dias'] else dados['n2']['tempo']

            dados['atrasados_ids'] = get_atrasados_16h(cursor)
            dados['atrasados_total'] = len(dados['atrasados_ids'])
            
            dados['rank_n1'] = get_ranking(cursor, ID_N1)
            dados['rank_n2'] = get_ranking(cursor, ID_N2)
            dados['rank_n3'] = get_ranking(cursor, ID_N3)
            cursor.close(); conn.close()
        except: pass
    return dados

# --- Proteção nas rotas
@app.route('/')
@requires_auth
def index():
    print(f">>> [ACESSO] {datetime.now().strftime('%H:%M:%S')} - Usuário: {request.authorization.username}")
    dados = coletar_todos_dados()
    return render_template('vigia.html', dados=dados, 
                           agora=datetime.now().strftime('%d/%m %H:%M'), 
                           base="https://chamados.slmandic.edu.br")

@app.route('/data')
@requires_auth  # < -- Cadeado de segurança 
def data_api():
    dados = coletar_todos_dados()
    dados['agora'] = datetime.now().strftime('%d/%m %H:%M')
    return jsonify(dados)

if __name__ == "__main__":
    print(">>> SERVIDOR VIGIA (VM) RODANDO NA PORTA 5000")
    print(">>> ACESSE: http://IP_DA_VM:5000")
    app.run(host='192.168.0.102', port=5000, debug=False)