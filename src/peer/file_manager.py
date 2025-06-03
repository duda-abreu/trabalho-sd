import os

class FileManager:
    @staticmethod
    def save_block(block_name, data, output_dir="downloads"):
        """Salva bloco em disco"""
        os.makedirs(output_dir, exist_ok=True)
        with open(f"{output_dir}/{block_name}", "wb") as f:
            f.write(data)

    @staticmethod
    def load_block(block_name, input_dir="downloads"):
        """Carrega bloco do disco"""
        try:
            with open(f"{input_dir}/{block_name}", "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None