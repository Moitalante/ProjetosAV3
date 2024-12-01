import requests
from flask import Flask, request, jsonify
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from waitress import serve

# Configuração do banco de dados para vendas no Railway
DATABASE_URL_VENDAS = "mysql+pymysql://root:MekYvOHqGvOkEyrgvqDNYWYwdgEryzbm@junction.proxy.rlwy.net:42540/railway"
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
DATABASE_URL_PRODUTOS = "mysql+pymysql://root:XfZUPIHFkatAoUdOXgWWwFPLHkSnACjl@junction.proxy.rlwy.net:53494/railway"
# Substitua <username>, <password>, <hostname>, <port> e <database> com as credenciais do banco de dados de produtos no Railway.
engine_produtos = create_engine(DATABASE_URL_PRODUTOS, echo=True)
SessionLocalProdutos = sessionmaker(bind=engine_produtos)

# Cabeçalhos de autenticação (se necessário)
#headers = {
#   "Authorization": "Bearer <seu_token_aqui>"  # Substitua com seu token de autenticação, se necessário
#}

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
        response = requests.put(url, json=dados_atualizados)
        if response.status_code == 200:
            return True
        else:
            print(f"Erro ao atualizar o estoque: {response.status_code} - {response.json()}")
            return False
    except Exception as e:
        print(f"Erro ao conectar ao servidor Node.js: {e}")
        return False

# Rota para registrar venda e atualizar estoque
app = Flask(__name__)

@app.route("/registrar_venda", methods=["POST"])
def registrar_venda():
    try:
        # Receber os dados da requisição
        dados = request.get_json()
        if not dados:
            return jsonify({"error": "Dados inválidos ou não enviados"}), 400

        nome_func = dados.get("nome_func")
        id_produto = dados.get("id_produto")
        quantidade_desejada = dados.get("quantidade")

        if not nome_func or not id_produto or not quantidade_desejada:
            return jsonify({"error": "Campos 'nome_func', 'id_produto' ou 'quantidade' faltando"}), 400

        # Buscar o produto no servidor de produtos no Railway
        url = f"https://av3-projetos-production.up.railway.app/produtos/{id_produto}"

        response = requests.get(url)
        if response.status_code != 200:
            return jsonify({"error": "Produto não encontrado ou erro ao buscar o produto"}), response.status_code

        produto = response.json()
        nome_produto = produto.get("nome")
        descricao = produto.get("descricao")
        quantidade_atual = produto.get("quantidade")
        preco = produto.get("preco")

        if not nome_produto or not descricao or quantidade_atual is None or preco is None:
            return jsonify({"error": "Dados do produto estão incompletos"}), 400

        # Validar quantidade disponível
        if quantidade_desejada > quantidade_atual:
            return jsonify({"error": "Quantidade solicitada excede o estoque disponível"}), 400

        # Atualizar o estoque no outro banco
        nova_quantidade = quantidade_atual - quantidade_desejada
        estoque_atualizado = atualizar_estoque_no_outro_banco(
            id_produto, nova_quantidade, nome_produto, descricao, preco
        )
        if not estoque_atualizado:
            return jsonify({"error": "Erro ao atualizar o estoque no outro banco"}), 500

        # Registrar a venda no banco de vendas
        venda_id = registrar_venda_no_banco(nome_func, nome_produto, quantidade_desejada, preco)

        # Retornar sucesso
        return jsonify({
            "message": "Venda registrada com sucesso",
            "venda_id": venda_id,
            "produto": {
                "nome": nome_produto,
                "descricao": descricao,
                "quantidade_vendida": quantidade_desejada,
                "preco": preco
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Rota para buscar produto
@app.route("/buscar_produto", methods=["GET"])
def buscar_produto():
    try:
        id_produto = request.args.get("id_produto")
        if not id_produto:
            return jsonify({"error": "ID do produto é necessário"}), 400

        # Buscar o produto no servidor de produtos no Railway
        url = f"https://av3-projetos-production.up.railway.app/produtos{id_produto}"

        response = requests.get(url)
        if response.status_code == 200:
            produto = response.json()
            return jsonify(produto)
        else:
            return jsonify({"error": "Produto não encontrado ou erro ao buscar o produto"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Rota para atualizar produto
@app.route("/atualizar_produto", methods=["POST", "PUT"])
def atualizar_produto():
    url = f"https://seu-nome.railway.app/produtos/1"  # Exemplo de URL para atualizar um produto

    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"error": "Dados inválidos ou não enviados"}), 400

        # Envia os dados para o servidor Node.js
        if request.method == "POST":
            # Se for um POST, enviar para adicionar um produto
            response = requests.post(url, json=dados)
        else:
            # Se for um PUT, enviar para atualizar um produto
            product_id = dados.get("id")
            if not product_id:
                return jsonify({"error": "ID do produto é necessário para atualizar"}), 400
            response = requests.put(f"{url}/{product_id}", json=dados)

        if response.status_code == 200 or response.status_code == 201:
            return jsonify({"message": "Produto processado com sucesso", "data": response.json()}), response.status_code
        else:
            return jsonify({"error": "Erro ao processar o produto", "details": response.json()}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5002)
