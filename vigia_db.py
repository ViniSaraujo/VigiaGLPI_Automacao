import mysql.connector
from flask import Flask, render_template
import configparser
import os
from datetime import datetime

# --- CARREGAR CONFIGURAÇÕES ---
pasta_script = os.path.dirname(os.path.abspath(__file__))
caminho_config = os.path.join(pasta_script, 'config.ini')
config = configparser.ConfigParser()
config.read(caminho_config)

try:
    DB_HOST = config['DATABASE']['HOST']
    DB_USER = config['DATABASE']['USER']
    DB_PASS = config['DATABASE']['PASSWORD']
    DB_NAME = config['DATABASE']['DATABASE']
    DB_PORT = config.get('DATABASE', 'PORT', fallback=3306)
    
    ID_N1 = config['GRUPOS']['ID_N1']
    ID_N2 = config['GRUPOS']['ID_N2']
    ID_N3 = config['GRUPOS']['ID_N3']
except KeyError as e:
    print(f"ERRO: Faltando configuração no config.ini: {e}")
    exit()

app = Flask(__name__, template_folder='templates')

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=int(DB_PORT),
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"Erro ao conectar no banco: {e}")
        return None

def formatar_tempo(minutos):
    """Converte minutos em dias/horas"""
    if not minutes: return "--"
    dias = minutos // 1440
    horas = (minutos % 1440) // 60
    if dias > 0: return f"{dias}d {horas}h"
    return f"{horas}h"

def get_dados_fila(cursor, group_id):
    """
    Conta chamados ABERTOS (status 1,2,3,4) atribuídos ao Grupo X
    e pega a data mais antiga.
    """
    # Status: 1=Novo, 2=Atribuido, 3=Planejado, 4=Pendente. (5=Soluc, 6=Fechado ignorados)
    query = f"""
        SELECT 
            COUNT(t.id) as total,
            MIN(t.date) as data_antiga
        FROM glpi_tickets t
        JOIN glpi_groups_tickets gt ON t.id = gt.tickets_id
        WHERE 
            gt.groups_id = {group_id}
            AND t.status IN (1, 2, 3, 4)
            AND t.is_deleted = 0
    """
    cursor.execute(query)
    row = cursor.fetchone()
    
    total = row[0]
    tempo_str = "--"
    
    if row[1]:
        # Calcula tempo desde a abertura
        delta = datetime.now() - row[1]
        dias = delta.days
        horas = delta.seconds // 3600
        tempo_str = f"{dias}d {horas}h"

    return {'total': total, 'tempo': tempo_str}

def get_atrasados(cursor):
    """
    Busca chamados que estouraram o SLA (time_to_resolve < agora)
    e que ainda não foram solucionados.
    """
    query = """
        SELECT id 
        FROM glpi_tickets 
        WHERE 
            time_to_resolve IS NOT NULL 
            AND time_to_resolve < NOW() 
            AND status IN (1, 2, 3, 4)
            AND is_deleted = 0
        LIMIT 50
    """
    cursor.execute(query)
    result = cursor.fetchall()
    ids = [str(row[0]) for row in result]
    return sorted(ids)

def get_ranking(cursor, group_id):
    """
    Ranking de quem mais resolveu chamados (status 5 ou 6) 
    no MÊS ATUAL, filtrado pelo grupo técnico.
    """
    # Primeiro dia do mês atual
    inicio_mes = datetime.now().strftime('%Y-%m-01 00:00:00')
    
    query = f"""
        SELECT 
            CONCAT(u.firstname, ' ', u.realname) as nome_tecnico,
            COUNT(t.id) as total_solucionados
        FROM glpi_tickets t
        -- Join para saber quem é o técnico (Type 2 = Assignee)
        JOIN glpi_tickets_users tu ON t.id = tu.tickets_id AND tu.type = 2
        JOIN glpi_users u ON tu.users_id = u.id
        -- Join para filtrar pelo grupo do chamado
        JOIN glpi_groups_tickets gt ON t.id = gt.tickets_id
        WHERE 
            gt.groups_id = {group_id}
            AND t.status IN (5, 6) -- Solucionado ou Fechado
            AND t.solvedate >= '{inicio_mes}'
            AND t.is_deleted = 0
        GROUP BY u.id
        ORDER BY total_solucionados DESC
        LIMIT 50
    """
    cursor.execute(query)
    return cursor.fetchall()

@app.route('/')
def index():
    conn = get_db_connection()
    dados = {
        'n1': {'total': 0, 'tempo': '--'},
        'n2': {'total': 0, 'tempo': '--'},
        'n3': {'total': 0, 'tempo': '--'},
        'atrasados_ids': [], 'atrasados_total': 0,
        'rank_n1': [], 'rank_n2': [], 'rank_n3': []
    }
    msg, erro = "Online (DB)", None
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # 1. Filas
            dados['n1'] = get_dados_fila(cursor, ID_N1)
            dados['n2'] = get_dados_fila(cursor, ID_N2)
            dados['n3'] = get_dados_fila(cursor, ID_N3)
            
            # 2. Atrasados
            # Nota: Se sua regra de "Atrasado" for diferente de SLA estourado,
            # precisamos ajustar a query SQL. Usei SLA < Agora como padrão.
            dados['atrasados_ids'] = get_atrasados(cursor)
            dados['atrasados_total'] = len(dados['atrasados_ids'])
            
            # 3. Ranking
            dados['rank_n1'] = get_ranking(cursor, ID_N1)
            dados['rank_n2'] = get_ranking(cursor, ID_N2)
            dados['rank_n3'] = get_ranking(cursor, ID_N3)
            
            cursor.close()
            conn.close()
        except Exception as e:
            erro = f"Erro na consulta SQL: {e}"
            msg = "Erro DB"
    else:
        erro = "Não foi possível conectar ao Banco de Dados."
        msg = "Offline"

    # URL Base para os links do HTML
    base_url = f"https://{config['DATABASE']['HOST']}"

    return render_template('vigia.html', 
                           dados=dados, 
                           msg=msg, 
                           erro=erro, 
                           agora=datetime.now().strftime('%d/%m %H:%M'),
                           base=base_url)

if __name__ == "__main__":
    # Roda na porta 5000
    app.run(host='127.0.0.1', port=5000, debug=True)