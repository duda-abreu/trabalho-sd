from flask import Flask, request, jsonify
import random
from tracker.peer_manager import GerenciadorPeers
from tracker.block_distributor import DistribuidorBlocos

app = Flask(__name__)

# Instâncias dos gerenciadores
gerenciador_peers = GerenciadorPeers()
distribuidor_blocos = DistribuidorBlocos()

@app.route('/registrar_peer', methods=['POST'])
def registrar_peer():
    """Registra um novo peer no tracker"""
    dados = request.json
    peer_id = dados.get('peer_id')
    ip = dados.get('ip', '127.0.0.1')
    porta = dados.get('porta', 8000)

    # Registra o peer
    gerenciador_peers.adicionar_peer(peer_id, ip, porta)

    # Distribui blocos iniciais
    blocos_iniciais = distribuidor_blocos.distribuir_blocos_iniciais(peer_id)

    # Retorna todos os peers (exceto ele mesmo)
    todos_peers = gerenciador_peers.listar_peers_ativos()
    peers_disponiveis = [p for p in todos_peers if p['peer_id'] != peer_id]

    print(f"Peer {peer_id} registrado com blocos: {blocos_iniciais}")

    return jsonify({
        'status': 'sucesso',
        'blocos_iniciais': blocos_iniciais,
        'peers': peers_disponiveis,
        'mensagem': f'Peer {peer_id} registrado com sucesso'
    })

@app.route('/listar_peers', methods=['GET'])
def listar_peers():
    """Lista peers disponíveis (exceto o solicitante)"""
    peer_id = request.args.get('peer_id')
    todos_peers = gerenciador_peers.listar_peers_ativos()
    resultado = [p for p in todos_peers if p['peer_id'] != peer_id]

    return jsonify({
        'peers': resultado,
        'total': len(resultado)
    })

@app.route('/status', methods=['GET'])
def status():
    peers_ativos = len(gerenciador_peers.listar_peers_ativos())
    total_blocos = distribuidor_blocos.total_blocos
    return jsonify({
        'peers_ativos': peers_ativos,
        'total_blocos': total_blocos,
        'status': 'ativo'
    })

@app.route('/desconectar_peer', methods=['POST'])
def desconectar_peer():
    dados = request.json
    peer_id = dados.get('peer_id')
    gerenciador_peers.remover_peer(peer_id)
    print(f"Peer {peer_id} se desconectou")
    return jsonify({
        'status': 'sucesso',
        'mensagem': f'Peer {peer_id} removido'
    })

if __name__ == '__main__':
    print("=== TRACKER MINIBIT INICIADO ===")
    print("Porta: 5000")
    print("Endpoints disponíveis:")
    print("- POST /registrar_peer")
    print("- GET /listar_peers")
    print("- GET /status")
    print("- POST /desconectar_peer")
    print("=====================================")
    
    app.run(host='0.0.0.0', port=5000, debug=True)