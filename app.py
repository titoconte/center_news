import os
import json
import sys
import subprocess
from flask import Flask, render_template, jsonify, request, Response

# Inicialização do servidor Flask
app = Flask(__name__, template_folder="templates")

# Diretório base e arquivo de configuração
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    """
    Carrega o arquivo de configuração config.json.
    Se não existir, retorna um esqueleto básico padrão.
    """
    if not os.path.exists(CONFIG_FILE):
        return {"telegram_bot_token": "", "channels": {}}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao ler arquivo de configuração: {e}")
        return {"telegram_bot_token": "", "channels": {}}

def save_config(config_data):
    """
    Salva novos dados no arquivo config.json.
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao salvar arquivo de configuração: {e}")
        return False

@app.route("/")
def index():
    """
    Rota principal do painel administrativo.
    Renderiza a interface estática do Dashboard.
    """
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Endpoint REST que retorna as configurações ativas do config.json.
    """
    config = load_config()
    return jsonify(config)

@app.route("/api/config", methods=["POST"])
def update_config():
    """
    Endpoint REST que recebe novos dados em formato JSON
    e atualiza o arquivo config.json local.
    """
    new_config = request.get_json()
    if not new_config:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400
        
    success = save_config(new_config)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Falha ao gravar configurações"}), 500

@app.route("/api/run-scraper", methods=["POST"])
def run_scraper_trigger():
    """
    Disparador rápido do scraper. Retorna sucesso imediato informando
    que o fluxo de logs pode ser iniciado.
    """
    return jsonify({"success": True, "message": "Scraper pronto para iniciar logs."})

@app.route("/api/stream-logs")
def stream_logs():
    """
    Cria uma conexão Server-Sent Events (SSE) em tempo real que:
    1. Executa o scraper.py local em um subprocesso de terminal Python.
    2. Lê a saída do terminal de forma assíncrona (Thread + Queue) não bloqueante.
    3. Envia comentários keep-alive periódicos para evitar queda de timeout do navegador.
    4. Finaliza enviando marcadores especiais de término ou erro.
    """
    import queue
    from threading import Thread
    
    def enqueue_output(out, q):
        for line in iter(out.readline, ''):
            q.put(line)
        out.close()

    def generate_log_lines():
        scraper_path = os.path.join(BASE_DIR, "scraper.py")
        print(f"[SERVIDOR] Disparando subprocesso python -u {scraper_path}")
        
        try:
            process = subprocess.Popen(
                [sys.executable, "-u", scraper_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=BASE_DIR
            )
            
            # Cria a fila e inicia a Thread de leitura do terminal do scraper
            q = queue.Queue()
            t = Thread(target=enqueue_output, args=(process.stdout, q))
            t.daemon = True  # Permite encerramento automático com o processo principal
            t.start()
            
            # Loop de leitura resiliente a timeouts de inatividade
            while True:
                try:
                    # Tenta obter uma linha de log com timeout de 2 segundos
                    line = q.get(timeout=2)
                    yield f"data: {line.strip()}\n\n"
                except queue.Empty:
                    # Se a fila está vazia, verifica se o processo terminou
                    if process.poll() is not None:
                        # O processo encerrou. Esvazia as linhas finais pendentes na fila
                        while not q.empty():
                            line = q.get_nowait()
                            yield f"data: {line.strip()}\n\n"
                        break
                    # Envia um comentário keep-alive no formato do protocolo SSE (ignorado pela UI)
                    # Isso avisa o navegador que a conexão TCP continua 100% ativa
                    yield ": keep-alive\n\n"
            
            return_code = process.wait()
            if return_code == 0:
                print("[SERVIDOR] Processo concluído com código de sucesso 0")
                yield "data: __FINISHED__\n\n"
            else:
                print(f"[SERVIDOR] Processo concluído com código de erro {return_code}")
                yield f"data: __ERROR__: Scraper finalizou com código {return_code}\n\n"
                
        except Exception as e:
            print(f"[SERVIDOR] Falha inesperada ao executar scraper: {e}")
            yield f"data: __ERROR__: Falha do servidor ao rodar script: {str(e)}\n\n"

    # Retorna a stream contínua no formato mime-type text/event-stream do HTML5 SSE
    return Response(generate_log_lines(), mimetype="text/event-stream")

if __name__ == "__main__":
    # Roda localmente na porta 5000 para acesso via localhost ou rede Wi-Fi
    print("=" * 60)
    print("Servidor de Curadoria Instagram Iniciado em http://localhost:5000")
    print("Acesse no seu navegador no PC ou Celular (na mesma rede Wi-Fi)")
    print("=" * 60)
    # Desativamos o modo debug (debug=False) para evitar que o recarregador automático (watchdog) do Flask
    # reinicie o servidor de forma fantasma ao ler bibliotecas do Python (comum em instalações Windows Store).
    app.run(host="0.0.0.0", port=5000, debug=False)
