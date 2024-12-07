import re
import typer
from os import environ
import psycopg as psy
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Aplicação REPL para interação com o banco de dados.")

console = Console()

def get_default_conexao():
    return environ.get("DATABASE_URL", "user=postgres password=password")

default_conexao = get_default_conexao()

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
        
        cur.execute("SELECT 1 FROM ESPORTE WHERE NOME = %s", (esporte_nome.upper(),))
        if cur.fetchone() is None:
            typer.echo(f"Esporte '{esporte_nome}' não encontrado. Verifique o nome do esporte e tente novamente.")
            return
        
        desempenho = float(input("Desempenho do time: "))
        
        administrador_cpf = input("CPF do administrador (XXX.XXX.XXX-XX): ")
        if not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$', administrador_cpf):
            typer.echo("CPF no formato inválido. Use o formato XXX.XXX.XXX-XX.")
            return
        
        
        
        if not administrador_existe(cur, administrador_cpf):
            administrador_nome = input("Nome do administrador: ")
            administrador_data_nascimento = input("Data de nascimento do administrador (YYYY-MM-DD): ")
            criar_administrador(cur, administrador_cpf, administrador_nome, administrador_data_nascimento)
        
        inserir_time(cur, nome, esporte_nome, desempenho, administrador_cpf)
        conn.commit()
        conn.close()
        typer.echo("Time inserido com sucesso.")
    except Exception as e:
        typer.echo(f"Erro ao inserir time: {e}")

if __name__ == "__main__":
    app()
