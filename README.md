# ProjetosAV3
Trabalho de AV3 de cana (Microsserviço)

No código, o padrão Singleton é implementado  ao garantir que exista apenas uma instância da conexão com o banco de dados. A classe SessionLocal é configurada uma vez, sendo reutilizada em todas as requisições. assegurando que a conexão com o banco não seja recriada repetidamente, otimizando a performance e evitando o consumo excessivo de recursos.

O padrão Factory Method é utilizado na criação da instância de Venda. A função 'registrar_venda_no_banco()' é responsável por criar objetos Venda, centralizando a criação da instância e encapsulando as lógicas necessárias para persistir a venda no banco de dados. Permitindo que a criação de objetos Venda seja feita de forma padronizada e facilitada em toda a aplicação.



1 - pip install requests /
2 - pip install flask /
3 - pip install sqlalchemy /
4 - pip install waitress /


BD
nome: Vendas
hostname: junction.proxy.rlwy.net    port: 36175
password: NCoLDllvIWKKtnZEzZrwzXohnCNJDguK

