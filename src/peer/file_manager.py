import os
import hashlib

class FileManager:
    @staticmethod
    def save_block(block_name: str, data: bytes, folder: str = "blocks"):
        """Salva bloco com verificação de integridade"""
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, block_name)
        
        # Verifica hash (SHA-256)
        checksum = hashlib.sha256(data).hexdigest()
        with open(filepath + ".sha256", "w") as f:
            f.write(checksum)
        
        with open(filepath, "wb") as f:
            f.write(data)

    @staticmethod
    def validate_block(block_name: str, data: bytes) -> bool:
        """Valida integridade do bloco"""
        checksum = hashlib.sha256(data).hexdigest()
        try:
            with open(f"blocks/{block_name}.sha256", "r") as f:
                return f.read().strip() == checksum
        except FileNotFoundError:
            return False