import requests
import json
import time

# Configurações do tracker
TRACKER_URL = "http://localhost:5000"

def testar_status():
    """Testa endpoint de status"""
    print("=== TESTANDO STATUS ===")
    try:
        response = requests.get(f"{TRACKER_URL}/status")
        if response.status_code == 200:
            dados = response.json()
            print(f"✓ Status OK: {dados}")
            return True
        else:
            print(f"✗ Erro no status: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Erro ao conectar: {e}")
        return False

def testar_registrar_peer(peer_id, porta=8000):
    """Testa registro de peer"""
    print(f"\n=== REGISTRANDO PEER {peer_id} ===")
    dados = {
        "peer_id": peer_id,
        "ip": "127.0.0.1",
        "porta": porta
    }
    
    try:
        response = requests.post(f"{TRACKER_URL}/registrar_peer", json=dados)
        if response.status_code == 200:
            resultado = response.json()
            print(f"✓ Peer {peer_id} registrado com sucesso")
            print(f"  Blocos iniciais: {resultado['blocos_iniciais']}")
            return True
        else:
            print(f"✗ Erro ao registrar: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def testar_listar_peers(peer_id):
    """Testa listagem de peers"""
    print(f"\n=== LISTANDO PEERS PARA {peer_id} ===")
    try:
        response = requests.get(f"{TRACKER_URL}/listar_peers?peer_id={peer_id}")
        if response.status_code == 200:
            resultado = response.json()
            print(f"✓ Peers encontrados: {len(resultado['peers'])}")
            for peer in resultado['peers']:
                print(f"  - {peer['peer_id']} ({peer['ip']}:{peer['porta']})")
            return True
        else:
            print(f"✗ Erro ao listar: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def testar_desconectar_peer(peer_id):
    """Testa desconexão de peer"""
    print(f"\n=== DESCONECTANDO PEER {peer_id} ===")
    dados = {"peer_id": peer_id}
    
    try:
        response = requests.post(f"{TRACKER_URL}/desconectar_peer", json=dados)
        if response.status_code == 200:
            resultado = response.json()
            print(f"✓ Peer {peer_id} desconectado: {resultado['mensagem']}")
            return True
        else:
            print(f"✗ Erro ao desconectar: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("INICIANDO TESTES DO TRACKER MINIBIT")
    print("=" * 40)
    
    # Verifica se tracker está rodando
    if not testar_status():
        print("\n✗ Tracker não está rodando!")
        print("Execute: python iniciar_tracker.py")
        return
    
    # Registra alguns peers para teste
    peers_teste = ["peer_001", "peer_002", "peer_003", "peer_004", "peer_005", "peer_006"]
    
    # Registra os peers
    for i, peer_id in enumerate(peers_teste):
        porta = 8000 + i
        testar_registrar_peer(peer_id, porta)
        time.sleep(0.5)  # Pequena pausa entre registros
    
    # Testa listagem para cada peer
    for peer_id in peers_teste:
        testar_listar_peers(peer_id)
        time.sleep(0.5)
    
    # Testa status final
    print("\n=== STATUS FINAL ===")
    testar_status()
    
    # Desconecta alguns peers
    for peer_id in peers_teste[:3]:
        testar_desconectar_peer(peer_id)
    
    # Status após desconexões
    print("\n=== STATUS APÓS DESCONEXÕES ===")
    testar_status()
    
    print("\n" + "=" * 40)
    print("TESTES CONCLUÍDOS!")

if __name__ == "__main__":
    main()