# trabalho-sd

# Parte 1

# Dependências do Tracker
# Para instalar: pip install -r requirements.txt

# Servidor web para o tracker
Flask==2.3.3

# Requisições HTTP (para testar)
requests==2.31.0

# JSON handling (já incluído no Python)
# json - built-in

# Outras dependências básicas (já incluídas no Python)
# random - built-in
# time - built-in
# os - built-in
# sys - built-in

Funcionalidades Implementadas
1. Servidor Principal (tracker_server.py)

POST /registrar_peer: Registra novos peers no sistema
GET /listar_peers: Lista peers disponíveis (exceto o solicitante)
GET /status: Mostra status do tracker
POST /desconectar_peer: Remove peer da lista de ativos

2. Gerenciador de Peers (peer_manager.py)

Mantém lista de peers ativos
Controla timestamps para detectar peers inativos
Funcionalidades de adicionar/remover peers

3. Distribuidor de Blocos (block_distributor.py)

Distribui blocos iniciais aleatórios para novos peers
Cada peer recebe 30-50% dos blocos totais
Rastreia quais blocos cada peer possui

Como Usar:

1. Instalar Dependências

bash ~ pip install -r requirements.txt

2. Iniciar o Tracker

bash ~ python start_tracker.py
O tracker ficará disponível em: http://localhost:5000

3. Testar o Tracker

bash ~ python test_tracker.py

# Parte 3

## Estratégias de Compartilhamento (`feature/strategies`)

Este módulo é responsável por implementar as lógicas inteligentes que os peers utilizam para decidir quais blocos de arquivo baixar e para quais outros peers eles devem dar prioridade no envio de blocos. O objetivo é otimizar a distribuição de blocos na rede e recompensar a cooperação.

As principais estratégias implementadas são:

### 1. Rarest First (`rarest_first.py`)

* **Objetivo**: Acelerar a obtenção de blocos que são menos comuns entre os peers vizinhos.
* **Funcionamento**:
    * O peer identifica os blocos do arquivo que ainda não possui.
    * Para cada bloco necessário, ele verifica quantos peers vizinhos conhecidos possuem aquele bloco.
    * O bloco que estiver disponível no menor número de peers é considerado o "mais raro" e é priorizado para download.
    * Se houver empate, um dos blocos mais raros é selecionado.

### 2. Olho por Olho (Tit-for-Tat Simplificado)

Esta estratégia gerencia para quais peers o nosso peer permitirá o envio de blocos (unchoking). Ela é dividida em duas partes principais:

* **`choking_manager.py`**:
    * Atua como o gerente do estado de "choke" (bloqueado para envio) e "unchoke" (desbloqueado para envio) dos peers vizinhos.
    * A cada 10 segundos, dispara o mecanismo de "unchoke otimista".
    * Mantém uma lista de até 4 peers "fixos" que estão desbloqueados devido à sua utilidade (possuem blocos raros) e 1 peer "otimista".
    * Orquestra as decisões tomadas pelo `tit_for_tat_strategy.py`.

* **`tit_for_tat_strategy.py`**:
    * **Unchoke Otimista**: Implementa a lógica para selecionar aleatoriamente um novo peer (que não seja fixo ou o otimista atual) a cada 10 segundos para ser o "unchoke otimista". Isso permite descobrir novos peers úteis.
    * **Avaliação e Promoção**:
        * Calcula uma pontuação para os peers (o candidato otimista e os fixos atuais) com base na quantidade de blocos "raros" que eles possuem. Um bloco é considerado raro se poucos peers na rede o possuem.
        * Com base nessa pontuação, os peers mais valiosos são selecionados para a lista de "fixos unchoked" (até 4).
        * Se o candidato otimista for bom o suficiente, ele pode ser promovido a fixo, possivelmente substituindo um fixo menos valioso se a lista estiver cheia.
        * Se não for promovido, o candidato otimista continua nessa condição até a próxima avaliação ou seleção aleatória.

**Arquivos Principais do Módulo:**
* `src/peer/strategies/rarest_first.py`
* `src/peer/strategies/choking_manager.py`
* `src/peer/strategies/tit_for_tat_strategy.py`
* `src/peer/strategies/test_estrategias.py` (testes de unidade para o módulo)
* `src/peer/strategies/__init__.py`
