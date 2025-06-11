from flask import Flask, request, jsonify
import random
from tracker.block_distributor import DistribuidorBlocos

app = Flask(__name__)

# Instâncias dos gerenciadores
distribuidor = DistribuidorBlocos(total_blocos=20) # Ajuste conforme necessário
peers_ativos = {} # Dicionário: peer_id -> {'ip': '...', 'porta': ...}


@app.route('/registrar_peer', methods=['POST'])
def registrar_peer():
    data = request.get_json()
    peer_id = data.get('peer_id')
    ip = data.get('ip')
    porta = data.get('porta')
    
    blocos_do_peer = data.get('blocks', []) 

    # Usa peers_ativos e distribuidor diretamente
    if peer_id not in peers_ativos: 
        print(f"Novo peer registrado: {peer_id} em {ip}:{porta}")
        peers_ativos[peer_id] = {'ip': ip, 'porta': porta}
        
        # Gera blocos iniciais aleatórios e atualiza o distribuidor
        blocos_iniciais_distribuidos = distribuidor.distribuir_blocos_iniciais(peer_id)
        # Mescla os blocos iniciais com os que o peer já informou (se for re-registro)
        distribuidor.atualizar_blocos_peer(peer_id, list(set(blocos_iniciais_distribuidos) | set(blocos_do_peer)))
    else:

        peers_ativos[peer_id]['ip'] = ip
        peers_ativos[peer_id]['porta'] = porta
        distribuidor.atualizar_blocos_peer(peer_id, blocos_do_peer) # Atualiza com os blocos informados pelo peer
        blocos_iniciais_distribuidos = [] 

    peers_para_retornar = []
    for p_id, p_info in peers_ativos.items():
        blocos_do_p = distribuidor.obter_blocos_peer(p_id) 
        peers_para_retornar.append({
            "peer_id": p_id,
            "ip": p_info['ip'],
            "porta": p_info['porta'],
            "blocks": blocos_do_p 
        })

    return jsonify({
        "message": "Peer registrado com sucesso!",
        "peers": peers_para_retornar,
        "blocos_iniciais": blocos_iniciais_distribuidos
    })

@app.route('/listar_peers')
def listar_peers():
    data = request.get_json(silent=True) # silent=True para não gerar erro se não houver JSON no GET
    peer_id_solicitante = request.args.get('peer_id')
    
    if data and 'blocks' in data and peer_id_solicitante:
        # Atualiza os blocos do peer solicitante se ele enviou essa informação
        distribuidor.atualizar_blocos_peer(peer_id_solicitante, data['blocks'])
            
    peers_excluindo_solicitante = [
        p_id for p_id in peers_ativos.keys() 
        if p_id != peer_id_solicitante and distribuidor.obter_blocos_peer(p_id) 
    ]

    # Implementa a regra: menos de 5 peers retorna todos, 5 ou mais retorna subconjunto aleatório
    if len(peers_excluindo_solicitante) < 5:
        selected_peers_ids = peers_excluindo_solicitante
    else:
        selected_peers_ids = random.sample(peers_excluindo_solicitante, min(5, len(peers_excluindo_solicitante)))
    
    peers_para_retornar = []
    for p_id in selected_peers_ids:
        p_info = peers_ativos[p_id]
        blocos_do_p = distribuidor.obter_blocos_peer(p_id)
        peers_para_retornar.append({
            "peer_id": p_id,
            "ip": p_info['ip'],
            "porta": p_info['porta'],
            "blocks": blocos_do_p 
        })

    return jsonify({"peers": peers_para_retornar})

@app.route('/remover_peer', methods=['POST'])
def remover_peer():
    data = request.get_json()
    peer_id = data.get('peer_id')
    if peer_id in peers_ativos:
        del peers_ativos[peer_id]
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