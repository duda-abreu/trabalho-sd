from flask import Flask, request, jsonify
from tracker.block_distributor import DistribuidorBlocos
from tracker.peer_manager import GerenciadorPeers

app = Flask(__name__)

# Instâncias dos gerenciadores
distribuidor = DistribuidorBlocos(total_blocos=20)
gerenciador_peers = GerenciadorPeers()


@app.route('/registrar_peer', methods=['POST'])
def registrar_peer():
    data = request.get_json()
    peer_id = data.get('peer_id')
    ip = data.get('ip')
    porta = data.get('porta')
    blocos_do_peer = data.get('blocks', [])

    if gerenciador_peers.obter_peer(peer_id) is None:
        print(f"Novo peer registrado: {peer_id} em {ip}:{porta}")
        gerenciador_peers.adicionar_peer(peer_id, ip, porta)
        blocos_iniciais = distribuidor.distribuir_blocos_iniciais(peer_id)
        distribuidor.atualizar_blocos_peer(peer_id, list(set(blocos_iniciais) | set(blocos_do_peer)))
    else:
        gerenciador_peers.adicionar_peer(peer_id, ip, porta)
        distribuidor.atualizar_blocos_peer(peer_id, blocos_do_peer)
        blocos_iniciais = []

    peers_para_retornar = []
    for peer in gerenciador_peers.listar_peers_ativos():
        blocos_do_p = distribuidor.obter_blocos_peer(peer["peer_id"])
        peers_para_retornar.append({
            "peer_id": peer["peer_id"],
            "ip": peer["ip"],
            "porta": peer["porta"],
            "blocks": blocos_do_p
        })

    return jsonify({
        "message": "Peer registrado com sucesso!",
        "peers": peers_para_retornar,
        "blocos_iniciais": blocos_iniciais
    })


@app.route('/listar_peers')
def listar_peers():
    data = request.get_json(silent=True)
    peer_id_solicitante = request.args.get('peer_id')
    # Remove peers inativos com mais de 60s de inatividade
    gerenciador_peers.limpar_peers_inativos(timeout=60)

    if data and 'blocks' in data and peer_id_solicitante:
        distribuidor.atualizar_blocos_peer(peer_id_solicitante, data['blocks'])

    # 🔄 Agora retorna todos os peers (exceto o solicitante)
    peers_disponiveis = [
        peer for peer in gerenciador_peers.listar_peers_ativos()
        if peer["peer_id"] != peer_id_solicitante
    ]

    resposta = []
    for peer in peers_disponiveis:
        blocos_do_p = distribuidor.obter_blocos_peer(peer["peer_id"])
        resposta.append({
            "peer_id": peer["peer_id"],
            "ip": peer["ip"],
            "porta": peer["porta"],
            "blocks": blocos_do_p
        })

    return jsonify({"peers": resposta})


@app.route('/remover_peer', methods=['POST'])
def remover_peer():
    data = request.get_json()
    peer_id = data.get('peer_id')
    if gerenciador_peers.obter_peer(peer_id):
        gerenciador_peers.remover_peer(peer_id)
        distribuidor.remover_peer(peer_id)
        print(f"Peer {peer_id} removido do tracker.")
        return jsonify({"message": "Peer removido com sucesso!"}), 200
    return jsonify({"message": "Peer não encontrado."}), 404


@app.route('/status')
def status():
    return jsonify(distribuidor.obter_estatisticas_blocos())


if __name__ == '__main__':
    print("\n==================================================")
    print("           MINIBIT TRACKER")
    print("==================================================")
    print("Gerenciador de Peers iniciado")
    print(f"Distribuidor iniciado com {distribuidor.total_blocos} blocos totais")
    print("Configurações do Tracker:")
    print("- Porta: 5000")
    print("- Host: 0.0.0.0 (todas as interfaces)")
    print("\nEndpoints disponíveis:")
    print("- POST /registrar_peer     - Registra novo peer")
    print("- GET  /listar_peers       - Lista peers disponíveis")
    print("- GET  /status             - Status do tracker")
    print("- POST /remover_peer       - Remove peer")
    print("\nPara testar o tracker:")
    print("curl http://localhost:5000/status")
    print("\nPressione Ctrl+C para parar o servidor")
    print("==================================================")

    app.run(host='0.0.0.0', port=5000, debug=True)
