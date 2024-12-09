import re
import typer
from os import environ
import psycopg as psy
from rich.console import Console
from rich.table import Table
from datetime import datetime

app = typer.Typer(help="Aplicação REPL para interação com o banco de dados.")

console = Console()

def get_default_conexao():
    return environ.get("DATABASE_URL", "user=postgres password=password")

default_conexao = get_default_conexao()

def administrador_existe(cur, cpf):
    cur.execute("SELECT 1 FROM ADMINISTRADOR WHERE CPF = %s", (cpf,))
    return cur.fetchone() is not None

def criar_administrador(cur, cpf, nome, data_nascimento):
    cur.execute(
        "INSERT INTO ADMINISTRADOR (CPF, NOME, DATA_NASCIMENTO) VALUES (%s, %s, %s)",
        (cpf, nome, data_nascimento)
    )

def inserir_time(cur, nome, esporte_nome, desempenho, administrador_cpf):
    cur.execute(
        "INSERT INTO TIME (NOME, ESPORTE_NOME, DESEMPENHO, ADMINISTRADOR_CPF) VALUES (%s, %s, %s, %s)",
        (nome, (esporte_nome).upper(), desempenho, administrador_cpf)
    )

@app.command("inserir-time", help="Insere um novo time de forma interativa, criando um administrador se necessário.")
def inserir_time_cmd(conexao: str = typer.Option(get_default_conexao, help="String de conexão do banco de dados.")):
    """Insere um novo time de forma interativa, criando um administrador se necessário."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        
        nome = input("Nome do time: ")
        esporte_nome = input("Nome do esporte: ")
        
        # cur.execute("SELECT 1 FROM ESPORTE WHERE NOME = %s", (esporte_nome.upper(),))
        # if cur.fetchone() is None:
            # typer.echo(f"Esporte '{esporte_nome}' não encontrado. Verifique o nome do esporte e tente novamente.")
            # return
        
        desempenho = float(input("Desempenho do time: "))
        
        administrador_cpf = input("CPF do administrador (XXX.XXX.XXX-XX): ")
        if not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$', administrador_cpf):
            typer.echo("CPF no formato inválido. Use o formato XXX.XXX.XXX-XX.")
            return
        
        
        
        if not administrador_existe(cur, administrador_cpf):
            administrador_nome = input("Nome do administrador: ")
            administrador_data_nascimento = input("Data de nascimento do administrador (DD/MM/YYYY): ")
            administrador_data_nascimento = datetime.strptime(administrador_data_nascimento, "%d/%m/%Y").strftime("%Y-%m-%d")
            criar_administrador(cur, administrador_cpf, administrador_nome, administrador_data_nascimento)
        
        inserir_time(cur, nome, esporte_nome, desempenho, administrador_cpf)
        conn.commit()
        conn.close()
        typer.echo("Time inserido com sucesso.")
    except Exception as e:
        typer.echo(f"Erro ao inserir time: {e}")

@app.command("times-todos-campeonatos", help="Encontra times que participaram de todos os campeonatos de seu esporte.")
def times_todos_campeonatos(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Encontra times que participaram de todos os campeonatos de seu esporte."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT a.nome, ac.esporte_nome
            FROM (
                SELECT a.cpf, t.esporte_nome, COUNT(DISTINCT c.id) AS championships_participated
                FROM atleta a
                JOIN atleta_time at ON a.cpf = at.atleta_cpf
                JOIN time t ON at.time_id = t.id
                JOIN times_participantes tp ON t.id = tp.time_id
                JOIN campeonato c ON tp.campeonato_id = c.id
                WHERE c.ano = 2023 AND c.esporte_nome = t.esporte_nome
                GROUP BY a.cpf, t.esporte_nome
            ) ac
            JOIN (
                SELECT esporte_nome, COUNT(*) AS total_championships
                FROM campeonato
                WHERE ano = 2023
                GROUP BY esporte_nome
            ) tc ON ac.esporte_nome = tc.esporte_nome
            JOIN atleta a ON ac.cpf = a.cpf
            WHERE ac.championships_participated = tc.total_championships;
        """)
        results = cur.fetchall()
        conn.close()
        
        table = Table(title="Atletas Participando de Todos os Campeonatos de Seu Esporte")
        table.add_column("Nome", style="cyan")
        table.add_column("Esporte", style="magenta")
        
        for row in results:
            table.add_row(row[0], row[1])
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Error executing query: {e}")

@app.command("times-participantes-todos-campeonatos", help="Encontra times que participaram de todos os campeonatos de seu esporte.")
def times_participantes_todos_campeonatos(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Encontra times que participaram de todos os campeonatos de seu esporte."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                t.nome AS team_name,
                t.esporte_nome AS sport_name
            FROM 
                time t
            WHERE 
                NOT EXISTS (
                    SELECT 
                        c.id
                    FROM 
                        campeonato c
                    WHERE 
                        c.esporte_nome = t.esporte_nome
                    AND 
                        NOT EXISTS (
                            SELECT 
                                1
                            FROM 
                                times_participantes tp
                            WHERE 
                                tp.campeonato_id = c.id
                            AND 
                                tp.time_id = t.id
                        )
                )
            ORDER BY 
                t.esporte_nome, t.nome;
        """)
        results = cur.fetchall()
        conn.close()
        
        table = Table(title="Times Participando de Todos os Campeonatos de Seu Esporte")
        table.add_column("Nome Time", style="cyan")
        table.add_column("Esporte", style="magenta")
        
        for row in results:
            table.add_row(row[0], row[1])
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Error executing query: {e}")

@app.command("max-desempenho-times", help="Encontrar os times com o maior desempenho médio (mínimo 3 partidas).")
def desempenho_times(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Encontrar os times com o maior desempenho médio (mínimo 3 partidas)."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                tp.nome,
                tp.avg_performance,
                tp.num_matches
            FROM (
                SELECT 
                    t.id,
                    t.nome,
                    COUNT(pt.partida_id) AS num_matches,
                    AVG(pt.desempenho) AS avg_performance
                FROM time t
                JOIN partida_times pt ON t.id = pt.time_id
                GROUP BY t.id, t.nome
                HAVING COUNT(pt.partida_id) >= 3
            ) tp
            WHERE tp.avg_performance = (
                SELECT MAX(sub.avg_performance)
                FROM (
                    SELECT 
                        t.id,
                        t.nome,
                        COUNT(pt.partida_id) AS num_matches,
                        AVG(pt.desempenho) AS avg_performance
                    FROM time t
                    JOIN partida_times pt ON t.id = pt.time_id
                    GROUP BY t.id, t.nome
                    HAVING COUNT(pt.partida_id) >= 3
                ) sub
            );
        """)
        results = cur.fetchall()
        conn.close()
        
        table = Table(title="Times com Maior Desempenho Médio (Mínimo 3 Partidas)")
        table.add_column("Nome Time", style="cyan")
        table.add_column("Desempenho Médio", style="green")
        table.add_column("Numero de Partidas", style="magenta")
        
        for row in results:
            table.add_row(row[0], f"{row[1]:.2f}", str(row[2]))
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Error executing query: {e}")

@app.command("media-desempenho-times", help="Encontrar o desempenho médio dos times em campeonatos.")
def media_desempenho_times(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Encontrar o desempenho médio dos times em campeonatos."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                t.nome AS team_name,
                c.nome AS championship_name,
                AVG(pt.desempenho) AS average_performance
            FROM 
                time t
            JOIN 
                partida_times pt ON t.id = pt.time_id
            JOIN 
                partida p ON pt.partida_id = p.id
            JOIN 
                campeonato c ON p.campeonato_id = c.id
            GROUP BY 
                t.nome, c.nome
            ORDER BY 
                t.nome, c.nome;
        """)
        results = cur.fetchall()
        conn.close()
        
        table = Table(title="Desempenho Medio dos Times em Campeonatos")
        table.add_column("Nome Time", style="cyan")
        table.add_column("Campeonato", style="magenta")
        table.add_column("Desempenho Medio", style="green")
        
        for row in results:
            table.add_row(row[0], row[1], f"{row[2]:.2f}")
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Error executing query: {e}")

@app.command("num-partidas-arbitro", help="Encontrar árbitros e o número de partidas que eles apitaram.")
def num_partidas_arbitro(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Encontrar árbitros e o número de partidas que eles apitaram."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                a.nome AS referee_name,
                e.nome AS sport_name,
                COUNT(p.id) AS number_of_matches
            FROM 
                arbitro a
            JOIN 
                especialidade_arbitros ea ON a.cpf = ea.arbitro_cpf
            JOIN 
                esporte e ON ea.esporte_nome = e.nome
            JOIN 
                partida p ON (p.arbitro1_cpf = a.cpf OR p.arbitro2_cpf = a.cpf OR p.arbitro3_cpf = a.cpf)
            GROUP BY 
                a.nome, e.nome
            ORDER BY 
                a.nome, e.nome;
        """)
        results = cur.fetchall()
        conn.close()
        
        table = Table(title="Numero de Partidas Arbitradas por Arbitro")
        table.add_column("Nome Arbitro", style="cyan")
        table.add_column("Esporte", style="magenta")
        table.add_column("Numero de Partidas", style="green")
        
        for row in results:
            table.add_row(row[0], row[1], str(row[2]))
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Error executing query: {e}")

# Command to list Administradores
@app.command("listar-administradores", help="Lista todos os administradores.")
def listar_administradores(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os administradores."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT CPF, NOME, DATA_NASCIMENTO FROM ADMINISTRADOR")
        administradores = cur.fetchall()
        conn.close()
        
        table = Table(title="Administradores")
        table.add_column("CPF", style="cyan")
        table.add_column("Nome", style="magenta")
        table.add_column("Data de Nascimento", style="green")
        
        for admin in administradores:
            table.add_row(admin[0], admin[1], str(admin[2]))
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar administradores: {e}")

# Command to list Atletas
@app.command("listar-atletas", help="Lista todos os atletas.")
def listar_atletas(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os atletas."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT CPF, NOME, DATA_NASCIMENTO FROM ATLETA")
        atletas = cur.fetchall()
        conn.close()
        
        table = Table(title="Atletas")
        table.add_column("CPF", style="cyan")
        table.add_column("Nome", style="magenta")
        table.add_column("Data de Nascimento", style="green")
        
        for atleta in atletas:
            table.add_row(atleta[0], atleta[1], str(atleta[2]))
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar atletas: {e}")

# Command to list Técnicos
@app.command("listar-tecnicos", help="Lista todos os técnicos.")
def listar_tecnicos(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os técnicos."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT CPF, NOME, DATA_NASCIMENTO FROM TECNICO")
        tecnicos = cur.fetchall()
        conn.close()
        
        table = Table(title="Técnicos")
        table.add_column("CPF", style="cyan")
        table.add_column("Nome", style="magenta")
        table.add_column("Data de Nascimento", style="green")
        
        for tecnico in tecnicos:
            table.add_row(tecnico[0], tecnico[1], str(tecnico[2]))
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar técnicos: {e}")

# Command to list Árbitros
@app.command("listar-arbitros", help="Lista todos os árbitros.")
def listar_arbitros(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os árbitros."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT CPF, NOME, DATA_NASCIMENTO, FEDERACAO, COD_REGISTRO FROM ARBITRO")
        arbitros = cur.fetchall()
        conn.close()
        
        table = Table(title="Árbitros")
        table.add_column("CPF", style="cyan")
        table.add_column("Nome", style="magenta")
        table.add_column("Data de Nascimento", style="green")
        table.add_column("Federação", style="yellow")
        table.add_column("Código Registro", style="red")
        
        for arbitro in arbitros:
            table.add_row(arbitro[0], arbitro[1], str(arbitro[2]), arbitro[3], arbitro[4])
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar árbitros: {e}")

# Command to list Centros de Treinamento
@app.command("listar-centros-treinamento", help="Lista todos os centros de treinamento.")
def listar_centros_treinamento(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os centros de treinamento."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT CNPJ, NOME, RUA, NUMERO, CEP, CIDADE, ESTADO, BAIRRO FROM CENTRO_TREINAMENTO")
        centros = cur.fetchall()
        conn.close()
        
        table = Table(title="Centros de Treinamento")
        table.add_column("CNPJ", style="cyan")
        table.add_column("Nome", style="magenta")
        table.add_column("Endereço", style="green")
        
        for centro in centros:
            endereco = f"{centro[2]}, {centro[3]}, {centro[7]}, {centro[5]} - {centro[6]}, CEP: {centro[4]}"
            table.add_row(centro[0], centro[1], endereco)
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar centros de treinamento: {e}")

# Command to list Campeonatos
@app.command("listar-campeonatos", help="Lista todos os campeonatos.")
def listar_campeonatos(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os campeonatos."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT ID, NOME, ESPORTE_NOME, ANO, CENTRO_TREINAMENTO_CNPJ, VENCEDOR
            FROM CAMPEONATO
        """)
        campeonatos = cur.fetchall()
        conn.close()
        
        table = Table(title="Campeonatos")
        table.add_column("ID", style="cyan")
        table.add_column("Nome", style="magenta")
        table.add_column("Esporte", style="green")
        table.add_column("Ano", style="yellow")
        table.add_column("Centro Treinamento", style="red")
        table.add_column("Vencedor (Time ID)", style="blue")
        
        for campeonato in campeonatos:
            table.add_row(
                str(campeonato[0]),
                campeonato[1],
                campeonato[2],
                str(campeonato[3]),
                campeonato[4],
                str(campeonato[5]) if campeonato[5] else "N/A"
            )
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar campeonatos: {e}")

# Command to list Partidas
@app.command("listar-partidas", help="Lista todas as partidas.")
def listar_partidas(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todas as partidas."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT ID, CAMPEONATO_ID, DATA_HORA, LOCAL, ARBITRO1_CPF, ARBITRO2_CPF, ARBITRO3_CPF, VENCEDOR
            FROM PARTIDA
        """)
        partidas = cur.fetchall()
        conn.close()
        
        table = Table(title="Partidas")
        table.add_column("ID", style="cyan")
        table.add_column("Campeonato ID", style="magenta")
        table.add_column("Data e Hora", style="green")
        table.add_column("Local", style="yellow")
        table.add_column("Árbitro 1", style="red")
        table.add_column("Árbitro 2", style="blue")
        table.add_column("Árbitro 3", style="purple")
        table.add_column("Vencedor (Time ID)", style="white")
        
        for partida in partidas:
            table.add_row(
                str(partida[0]),
                str(partida[1]),
                str(partida[2]),
                partida[3],
                partida[4] or "N/A",
                partida[5] or "N/A",
                partida[6] or "N/A",
                str(partida[7]) if partida[7] else "N/A"
            )
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar partidas: {e}")

# Command to list Patrocinadores
@app.command("listar-patrocinadores", help="Lista todos os patrocinadores.")
def listar_patrocinadores(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os patrocinadores."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT CNPJ, NOME FROM PATROCINADOR")
        patrocinadores = cur.fetchall()
        conn.close()
        
        table = Table(title="Patrocinadores")
        table.add_column("CNPJ", style="cyan")
        table.add_column("Nome", style="magenta")
        
        for patrocinador in patrocinadores:
            table.add_row(patrocinador[0], patrocinador[1])
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar patrocinadores: {e}")

# Command to list Bolsas
@app.command("listar-bolsas", help="Lista todas as bolsas concedidas.")
def listar_bolsas(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todas as bolsas concedidas."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT FACULDADE_CNPJ, ATLETA_CPF, DATA_INICIO, DATA_FIM
            FROM BOLSA
        """)
        bolsas = cur.fetchall()
        conn.close()
        
        table = Table(title="Bolsas")
        table.add_column("Faculdade CNPJ", style="cyan")
        table.add_column("Atleta CPF", style="magenta")
        table.add_column("Data Início", style="green")
        table.add_column("Data Fim", style="yellow")
        
        for bolsa in bolsas:
            table.add_row(
                bolsa[0],
                bolsa[1],
                str(bolsa[2]),
                str(bolsa[3]) if bolsa[3] else "Em andamento"
            )
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar bolsas: {e}")

# Command to list Contratações
@app.command("listar-contratacoes", help="Lista todas as contratações de técnicos.")
def listar_contratacoes(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todas as contratações de técnicos."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT TECNICO_CPF, CENTRO_TREINAMENTO_CNPJ, DATA_INICIO, DATA_FIM
            FROM CONTRATACAO
        """)
        contratacoes = cur.fetchall()
        conn.close()
        
        table = Table(title="Contratações")
        table.add_column("Técnico CPF", style="cyan")
        table.add_column("Centro Treinamento CNPJ", style="magenta")
        table.add_column("Data Início", style="green")
        table.add_column("Data Fim", style="yellow")
        
        for contrato in contratacoes:
            table.add_row(
                contrato[0],
                contrato[1],
                str(contrato[2]),
                str(contrato[3]) if contrato[3] else "Em andamento"
            )
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar contratações: {e}")

# Command to list Treinamentos
@app.command("listar-treinamentos", help="Lista todos os treinamentos realizados.")
def listar_treinamentos(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os treinamentos realizados."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT TIME_ID, TECNICO_CPF, CENTRO_TREINAMENTO_CNPJ, DATA_HORA
            FROM TREINAMENTO
        """)
        treinamentos = cur.fetchall()
        conn.close()
        
        table = Table(title="Treinamentos")
        table.add_column("Time ID", style="cyan")
        table.add_column("Técnico CPF", style="magenta")
        table.add_column("Centro Treinamento CNPJ", style="green")
        table.add_column("Data e Hora", style="yellow")
        
        for treino in treinamentos:
            table.add_row(
                str(treino[0]),
                treino[1],
                treino[2],
                str(treino[3])
            )
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar treinamentos: {e}")

# Command to list Especialidades de Árbitros
@app.command("listar-especialidades-arbitros", help="Lista as especialidades dos árbitros.")
def listar_especialidades_arbitros(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista as especialidades dos árbitros."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT ARBITRO_CPF, ESPORTE_NOME
            FROM ESPECIALIDADE_ARBITROS
        """)
        especialidades = cur.fetchall()
        conn.close()
        
        table = Table(title="Especialidades dos Árbitros")
        table.add_column("Árbitro CPF", style="cyan")
        table.add_column("Esporte", style="magenta")
        
        for esp in especialidades:
            table.add_row(esp[0], esp[1])
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar especialidades dos árbitros: {e}")

# Command to list Times Participantes
@app.command("listar-times-participantes", help="Lista os times participantes nos campeonatos.")
def listar_times_participantes(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista os times participantes nos campeonatos."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("""
            SELECT TIME_ID, CAMPEONATO_ID
            FROM TIMES_PARTICIPANTES
        """)
        participantes = cur.fetchall()
        conn.close()
        
        table = Table(title="Times Participantes")
        table.add_column("Time ID", style="cyan")
        table.add_column("Campeonato ID", style="magenta")
        
        for participante in participantes:
            table.add_row(str(participante[0]), str(participante[1]))
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao listar times participantes: {e}")

@app.command("listar-esportes", help="Lista todos os esportes e suas descrições.")
def listar_esportes(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os esportes e suas descrições."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT NOME, DESCRICAO FROM ESPORTE")
        esportes = cur.fetchall()
        conn.close()
        
        table = Table(title="Esportes")
        table.add_column("Nome", justify="left", style="cyan", no_wrap=True)
        table.add_column("Descrição", justify="left", style="magenta")
        
        for esporte in esportes:
            table.add_row(esporte[0], esporte[1])
        
        console.print(table)
    except Exception as e:
        typer.echo(f"Erro ao conectar: {e}")

@app.command("listar-times", help="Lista todos os times e seus respectivos esportes.")
def listar_times(conexao: str = typer.Option(default_conexao, help="String de conexão do banco de dados.")):
    """Lista todos os times e seus respectivos esportes."""
    try:
        conn = psy.connect(conexao)
        cur = conn.cursor()
        cur.execute("SELECT TIME.NOME, TIME.ESPORTE_NOME, TIME.DESEMPENHO, ADMINISTRADOR.NOME FROM TIME LEFT JOIN ADMINISTRADOR ON TIME.ADMINISTRADOR_CPF = ADMINISTRADOR.CPF")
        times = cur.fetchall()
        conn.close()
        
        table = Table(title="Times")
        table.add_column("Nome", justify="left", style="cyan", no_wrap=True)
        table.add_column("Esporte", justify="left", style="magenta")
        table.add_column("Desempenho", justify="right", style="green")
        table.add_column("Administrador", justify="left", style="yellow")
        
        for time in times:
            table.add_row(time[0], time[1], str(time[2]), time[3])
        
        console.print(table)
    except psy.OperationalError as e:
        typer.echo(f"Erro operacional ao conectar: {e}")
    except psy.DatabaseError as e:
        typer.echo(f"Erro no banco de dados: {e}")
    except Exception as e:
        typer.echo(f"Erro inesperado: {e}")


if __name__ == "__main__":
    app()
