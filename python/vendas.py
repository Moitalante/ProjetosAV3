import requests
from flask import Flask, request, jsonify
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from waitress import serve

# Configuração do banco de dados
DATABASE_URL = "mysql+pymysql://root:MekYvOHqGvOkEyrgvqDNYWYwdgEryzbm@junction.proxy.rlwy.net:42540/railway"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

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

Base.metadata.create_all(engine)

# Registrar venda no banco local
def registrar_venda_no_banco(nome_func, veiculo_vendido, quantidade, preco):
    session = SessionLocal()
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

# Atualizar o estoque no outro banco
def atualizar_estoque_no_outro_banco(id_produto, nova_quantidade, nome, descricao, preco):
    # URL do servidor Node.js para atualizar o produto
    url = f"http://localhost:3300/produtos/{id_produto}"

    # Dados para enviar ao servidor
    dados_atualizados = {
        "nome": nome,
        "descricao": descricao,
        "quantidade": nova_quantidade,
        "preco": preco
    }

    try:
        # Fazendo a requisição PUT para atualizar o produto
        response = requests.put(url, json=dados_atualizados)
        if response.status_code == 200:
            return True
        else:
            print(f"Erro ao atualizar o estoque: {response.json()}")
            return False
    except Exception as e:
        print(f"Erro ao conectar ao servidor Node.js: {e}")
        return False

# Rota para buscar produto e registrar venda
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

        # URL para buscar o produto
        url = f"http://localhost:3300/produtos/{id_produto}"

        # Buscar o produto
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

        # Registrar a venda no banco local
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



   

@app.route("/buscar_produto", methods=["GET"])
def buscar_produto():
    # A URL do seu servidor Node.js



            #utilizando GET
    #/produtos --- retorna todos os produtos
    #/produtos/id --- retorna o produto com base no id

            #Utilizando POST
    #/produtos      (nome,descricao,quantidade,preco)

            #Utilizando PUT
    #/produtos/id   (nome,descricao,quantidade,preco)

            #Utilizando DELETE
    #/produtos/id


    # colunas = nome, descricao, quantidade, preco




    url = "http://localhost:3300/produtos/7"  # Ou outra URL que você deseja buscar

    try:
        # Fazendo a requisição GET para buscar os dados do produto
        response = requests.get(url)
        if response.status_code == 200:
            # Se a requisição for bem-sucedida, retorna o produto em JSON
            produto = response.json()
            print(produto)
            return jsonify(produto)
        else:
            return jsonify({"error": "Produto não encontrado ou erro ao buscar o produto"}), response.status_code
    except Exception as e:
        # Caso ocorra algum erro ao fazer a requisição
        return jsonify({"error": str(e)}), 500
    





# Rota para enviar dados ao servidor Node.js (POST ou PUT)
@app.route("/atualizar_produto", methods=["POST", "PUT"])
def atualizar_produto():
    url = "http://localhost:3300/produtos/1"  # URL do seu servidor Node.js

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