import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuração do banco de dados para vendas no Railway
DATABASE_URL_VENDAS = "mysql+pymysql://root:NCoLDllvIWKKtnZEzZrwzXohnCNJDguK@junction.proxy.rlwy.net:36175/railway"
engine_vendas = create_engine(DATABASE_URL_VENDAS, echo=True)
SessionLocalVendas = sessionmaker(bind=engine_vendas)

Base = declarative_base()

# Modelo da tabela de vendas
class Venda(Base):
    __tablename__ = "vendas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_venda = Column(DateTime, default=datetime.utcnow)
    nome_func = Column(String(255), nullable=False)
    veiculo_vendido = Column(String(255), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco = Column(DECIMAL(10, 2), nullable=False)

Base.metadata.create_all(engine_vendas)

# Configuração do banco de dados para produtos no Railway
DATABASE_URL_PRODUTOS = "mysql+pymysql://root:XfZUPIHFkatAoUdOXgWWwFPLHkSnACjl@mysql-jww1.railway.internal:53494/railway"
engine_produtos = create_engine(DATABASE_URL_PRODUTOS, echo=True)
SessionLocalProdutos = sessionmaker(bind=engine_produtos)

# Registrar venda no banco de dados de vendas
def registrar_venda_no_banco(nome_func, veiculo_vendido, quantidade, preco):
    session = SessionLocalVendas()
    try:
        venda = Venda(nome_func=nome_func, veiculo_vendido=veiculo_vendido, quantidade=quantidade, preco=preco)
        session.add(venda)
        session.commit()
        session.refresh(venda)
        return venda.id
    except Exception as e:
        session.rollback()
        print(f"Erro ao registrar venda: {e}")
    finally:
        session.close()

# Atualizar o estoque no banco de dados de produtos no Railway
def atualizar_estoque_no_outro_banco(id_produto, nova_quantidade, nome, descricao, preco):
    url = f"https://av3-projetos-production.up.railway.app/produtos/{id_produto}"  # Substitua pelo URL do seu serviço no Railway

    dados_atualizados = {
        "nome": nome,
        "descricao": descricao,
        "quantidade": nova_quantidade,
        "preco": preco
    }

    try:
        response = requests.put(url, json=dados_atualizados, timeout=30)
        if response.status_code == 200:
            return True
        else:
            print(f"Erro ao atualizar o estoque: {response.status_code} - {response.json()}")
            return False
    except Exception as e:
        print(f"Erro ao conectar ao servidor Node.js: {e}")
        return False


# Classe que lida com as requisições HTTP
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/registrar_venda":
            try:
                # Receber dados JSON da requisição
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                dados = json.loads(post_data.decode("utf-8"))

                if not dados:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Dados inválidos ou não enviados"}).encode())
                    return

                nome_func = dados.get("nome_func")
                id_produto = dados.get("id_produto")
                quantidade_desejada = dados.get("quantidade")

                if not nome_func or not id_produto or not quantidade_desejada:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Campos 'nome_func', 'id_produto' ou 'quantidade' faltando"}).encode())
                    return

                # Buscar o produto no servidor de produtos no Railway
                url = f"https://av3-projetos-production.up.railway.app/produtos/{id_produto}"

                response = requests.get(url)
                if response.status_code != 200:
                    self.send_response(response.status_code)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Produto não encontrado ou erro ao buscar o produto"}).encode())
                    return

                produto = response.json()
                nome_produto = produto.get("nome")
                descricao = produto.get("descricao")
                quantidade_atual = produto.get("quantidade")
                preco = produto.get("preco")

                if not nome_produto or not descricao or quantidade_atual is None or preco is None:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Dados do produto estão incompletos"}).encode())
                    return

                # Validar quantidade disponível
                if quantidade_desejada > quantidade_atual:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Quantidade solicitada excede o estoque disponível"}).encode())
                    return

                # Atualizar o estoque no outro banco
                nova_quantidade = quantidade_atual - quantidade_desejada
                estoque_atualizado = atualizar_estoque_no_outro_banco(
                    id_produto, nova_quantidade, nome_produto, descricao, preco
                )
                if not estoque_atualizado:
                    self.send_response(500)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Erro ao atualizar o estoque no outro banco"}).encode())
                    return

                # Calcular o preço total da venda
                preco_total = quantidade_desejada * preco
                
                # Registrar a venda no banco de vendas
                venda_id = registrar_venda_no_banco(nome_func, nome_produto, quantidade_desejada, preco_total)

                # Retornar sucesso
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "message": "Venda registrada com sucesso",
                    "venda_id": venda_id,
                    "produto": {
                        "nome": nome_produto,
                        "descricao": descricao,
                        "quantidade_vendida": quantidade_desejada,
                        "preco": preco_total  # Agora retornando o preço total da venda
                    }
                }).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

# Função para rodar o servidor
def run(server_class=HTTPServer, handler_class=RequestHandler, port=36175):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Server running on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run(port=36175)