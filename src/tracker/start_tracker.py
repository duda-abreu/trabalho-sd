import sys
import os

# Adiciona o diretório src ao path para importar os módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def main():
    """Função principal para iniciar o tracker"""
    print("=" * 50)
    print("           MINIBIT TRACKER")
    print("=" * 50)
    print()
    
    try:
        # Importa e executa o servidor do tracker
        from tracker_server import app
        
        print("Configurações do Tracker:")
        print("- Porta: 5000")
        print("- Host: 0.0.0.0 (todas as interfaces)")
        print("- Modo Debug: Ativado")
        print()
        print("Endpoints disponíveis:")
        print("- POST /registrar_peer    - Registra novo peer")
        print("- GET  /listar_peers      - Lista peers disponíveis")
        print("- GET  /status           - Status do tracker")
        print("- POST /desconectar_peer - Remove peer")
        print()
        print("Para testar o tracker:")
        print("curl http://localhost:5000/status")
        print()
        print("Pressione Ctrl+C para parar o servidor")
        print("=" * 50)
        
        # Inicia o servidor Flask
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n\nTracker interrompido pelo usuário")
        print("Encerrando servidor...")
        
    except ImportError as e:
        print(f"Erro ao importar módulos: {e}")
        print("Certifique-se de que Flask está instalado:")
        print("pip install flask")
        
    except Exception as e:
        print(f"Erro inesperado: {e}")
        
    finally:
        print("Tracker finalizado.")

if __name__ == "__main__":
    main()