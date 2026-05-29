import os
import json
import time
import subprocess
from datetime import datetime, timedelta
import requests
import instaloader
import browser_cookie3
from deep_translator import GoogleTranslator

# Configurações de caminhos de arquivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DATABASE_FILE = os.path.join(BASE_DIR, "database.json")

def load_json(file_path):
    """
    Carrega e retorna o conteúdo de um arquivo JSON.
    Retorna um dicionário vazio caso o arquivo não exista ou ocorra erro.
    """
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar JSON de {file_path}: {e}")
        return {}

def save_json(file_path, data):
    """
    Salva dados estruturados em um arquivo JSON com formatação amigável (indentação).
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar JSON em {file_path}: {e}")

def get_instagram_session():
    """
    Obtém cookies do Instagram de navegadores instalados (Chrome, Edge, Firefox)
    para injetar no Instaloader. Isso evita login com usuário/senha e reduz bloqueios.
    """
    # max_connection_attempts=1 impede loops infinitos do Instaloader em caso de erros/redirects de rede
    L = instaloader.Instaloader(
        max_connection_attempts=1,
        download_pictures=False,
        download_videos=False,
        download_comments=False,
        download_geotags=False,
        save_metadata=False
    )
    
    # User-Agents correspondentes a cada navegador para que o Instagram não desconfie da assinatura HTTP
    user_agents = {
        'chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'edge': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
        'firefox': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
        'opera': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0'
    }
    
    print("[INFO] Tentando extrair cookies do Instagram dos navegadores locais...")
    browsers = ['firefox', 'chrome', 'edge', 'opera']
    cookies_loaded = False
    
    for browser in browsers:
        try:
            print(f"[INFO] Buscando cookies no navegador: {browser}")
            if browser == 'chrome':
                cookies = browser_cookie3.chrome(domain_name='instagram.com')
            elif browser == 'edge':
                cookies = browser_cookie3.edge(domain_name='instagram.com')
            elif browser == 'firefox':
                cookies = browser_cookie3.firefox(domain_name='instagram.com')
            elif browser == 'opera':
                cookies = browser_cookie3.opera(domain_name='instagram.com')
            
            # Atualiza os cookies da sessão de requests interna do Instaloader
            L.context._session.cookies.update(cookies)
            
            # Extrai o token CSRF dos cookies e o define no cabeçalho X-CSRFToken
            # e adiciona o header Referer de segurança (ambos obrigatórios para validar requisições GraphQL logadas)
            cookies_dict = requests.utils.dict_from_cookiejar(cookies)
            csrf_token = cookies_dict.get('csrftoken')
            
            # Define o User-Agent correspondente ao navegador de origem e os cabeçalhos de segurança
            ua = user_agents.get(browser, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
            headers = {
                'User-Agent': ua,
                'Referer': 'https://www.instagram.com/'
            }
            if csrf_token:
                headers['X-CSRFToken'] = csrf_token
                
            L.context._session.headers.update(headers)
            
            # Testa se a sessão está funcional de verdade usando L.test_login()
            print(f"[INFO] Validando sessão ativa no Instagram obtida do {browser.capitalize()}...")
            logged_username = L.test_login()
            
            if logged_username:
                print(f"[SUCESSO] Sessão ativa do Instagram (@{logged_username}) importada com sucesso do {browser.capitalize()}!")
                cookies_loaded = True
                break
            else:
                print(f"[AVISO] Cookies obtidos do {browser.capitalize()}, mas a sessão de login não está ativa/válida.")
                L.context._session.cookies.clear() # Limpa cookies para evitar erros de requisições malformadas
        except Exception as e:
            print(f"[AVISO] Não foi possível ler cookies do navegador {browser.capitalize()}: {e}")
            continue
            
    if not cookies_loaded:
        print("[AVISO] Nenhuma sessão logada ativa foi encontrada. O robô rodará de forma anônima.")
        print("[DICA] Certifique-se de estar logado no Instagram no seu navegador principal e reabra a aba do Instagram por lá!")
        # Define User-Agent padrão moderno
        L.context._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        })
        
    return L

def translate_text(text):
    """
    Traduz a legenda do post de inglês para português de forma automática e gratuita.
    Retorna o texto original se não precisar de tradução ou se ocorrer algum erro.
    """
    if not text:
        return ""
    try:
        # GoogleTranslator detecta automaticamente o idioma (source='auto') e traduz para pt
        translator = GoogleTranslator(source='auto', target='pt')
        translated = translator.translate(text)
        
        # Se a tradução retornar idêntica, pode ser que já estivesse em português
        if translated.strip().lower() == text.strip().lower():
            return text
            
        return translated
    except Exception as e:
        print(f"[AVISO] Falha ao traduzir texto: {e}")
        return text

def send_telegram_photo(token, chat_id, photo_url, caption):
    """
    Envia uma foto para o Telegram via API sendPhoto, com legenda HTML acoplada.
    """
    if not token or not chat_id or not photo_url:
        return False
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        res_data = response.json()
        return response.status_code == 200 and res_data.get("ok")
    except Exception as e:
        print(f"[AVISO] Falha ao enviar foto ao Telegram: {e}")
        return False

def send_telegram_video(token, chat_id, video_url, caption):
    """
    Envia um vídeo para o Telegram via API sendVideo, com legenda HTML acoplada.
    """
    if not token or not chat_id or not video_url:
        return False
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    payload = {
        "chat_id": chat_id,
        "video": video_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=25)
        res_data = response.json()
        return response.status_code == 200 and res_data.get("ok")
    except Exception as e:
        print(f"[AVISO] Falha ao enviar vídeo ao Telegram: {e}")
        return False

def send_telegram_message(token, chat_id, text):
    """
    Envia uma mensagem formatada para um canal específico do Telegram usando a API HTTP do Telegram.
    """
    if not token or not chat_id:
        print("[AVISO] Token do bot ou Chat ID não configurados. Envio ao Telegram ignorado.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_data = response.json()
        if response.status_code == 200 and res_data.get("ok"):
            print(f"[SUCESSO] Mensagem enviada para o chat {chat_id}")
            return True
        else:
            print(f"[ERRO] Erro na resposta do Telegram para {chat_id}: {res_data}")
            return False
    except Exception as e:
        print(f"[ERRO] Falha ao se conectar com a API do Telegram: {e}")
        return False

def sync_with_github():
    """
    Executa os comandos Git automáticos para registrar as atualizações locais 
    e fazer o push das configurações e base de dados para o repositório GitHub.
    """
    print("[INFO] Iniciando sincronização automática com o GitHub...")
    try:
        # 1. Adiciona os arquivos JSON locais no controle do git
        subprocess.run(["git", "add", "config.json", "database.json"], check=True, cwd=BASE_DIR)
        
        # 2. Faz o commit com timestamp atual
        commit_msg = f"auto: update configuration and database - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=BASE_DIR)
        
        # 3. Faz o push para o repositório remoto na branch atual
        # Primeiro, descobre o nome da branch atual
        branch_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True, cwd=BASE_DIR)
        current_branch = branch_res.stdout.strip()
        
        print(f"[INFO] Fazendo push na branch '{current_branch}'...")
        subprocess.run(["git", "push", "origin", current_branch], check=True, cwd=BASE_DIR)
        print("[SUCESSO] Sincronização e push no GitHub concluídos!")
    except subprocess.CalledProcessError as e:
        print(f"[AVISO] Sincronização com o Git falhou ou sem alterações a comitar: {e}")
    except Exception as e:
        print(f"[ERRO] Erro inesperado ao sincronizar com o GitHub: {e}")

def fetch_posts_via_api(session, username):
    """
    Busca posts recentes de um perfil usando a API nativa do Instagram Web (sem GraphQL).
    Retorna uma lista de posts simplificados com metadados de mídias e localização.
    """
    url = f"https://www.instagram.com/api/v1/feed/user/{username}/username/"
    headers = {
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    response = session.get(url, headers=headers, timeout=20)
    
    if response.status_code == 200:
        feed_data = response.json()
        posts = []
        items = feed_data.get('items', [])
        
        for item in items:
            shortcode = item.get('code')
            taken_at_timestamp = item.get('taken_at')
            date_utc = datetime.utcfromtimestamp(taken_at_timestamp)
            
            caption_text = ""
            caption_obj = item.get('caption')
            if caption_obj:
                caption_text = caption_obj.get('text', '')
                
            # Extrai fotos e vídeos de forma robusta (suporta imagens, vídeos e carrosséis)
            photo_url = None
            video_url = None
            media_type = item.get('media_type')
            
            if media_type == 8: # Carrossel
                carousel = item.get('carousel_media', [])
                if carousel:
                    first = carousel[0]
                    m_type = first.get('media_type')
                    if m_type == 1:
                        photo_url = first.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
                    elif m_type == 2:
                        video_url = first.get('video_versions', [{}])[0].get('url')
                        photo_url = first.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
            else:
                if media_type == 1: # Imagem
                    photo_url = item.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
                elif media_type == 2: # Vídeo
                    video_url = item.get('video_versions', [{}])[0].get('url')
                    photo_url = item.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
            
            # Localização
            location_name = ""
            location_obj = item.get('location')
            if location_obj:
                location_name = location_obj.get('name', '')
                
            posts.append({
                'shortcode': shortcode,
                'date_utc': date_utc,
                'caption': caption_text,
                'photo_url': photo_url,
                'video_url': video_url,
                'location_name': location_name
            })
        return posts
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

def run_scraper():
    """
    Função principal que gerencia o fluxo completo de scraping do Instagram,
    filtragem por palavras-chave, tradução e envio ao Telegram.
    """
    print("=" * 60)
    print(f"Iniciando Execução do Scraper: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Carrega arquivos de dados
    configs = load_json(CONFIG_FILE)
    db = load_json(DATABASE_FILE)
    
    bot_token = configs.get("telegram_bot_token")
    channels = configs.get("channels", {})
    
    if not bot_token:
        print("[ERRO] Token do Bot do Telegram não encontrado no config.json! Abortando scraper.")
        return
        
    # Inicializa banco de dados de processados se estiver vazio
    if "processed_posts" not in db:
        db["processed_posts"] = []
        
    processed_set = {post["shortcode"] for post in db["processed_posts"]}
    
    # Inicializa Instaloader com sessão ativa do navegador
    L = get_instagram_session()
    
    new_posts_counter = 0
    
    # Varre cada canal do Telegram configurado
    for channel_key, channel_info in channels.items():
        channel_name = channel_info.get("name")
        chat_id = channel_info.get("telegram_chat_id")
        include_caption = channel_info.get("include_caption", True)
        profiles = channel_info.get("profiles", [])
        
        # Novas Configurações Personalizadas por Canal
        post_images = channel_info.get("post_images", True)
        post_videos = channel_info.get("post_videos", True)
        translate_caption = channel_info.get("translate_caption", True)
        show_location = channel_info.get("show_location", False)
        scan_days = int(channel_info.get("scan_days", 2))
        
        print(f"\n[CANAL] Processando Tema: {channel_name} (Chave: {channel_key})")
        if not chat_id:
            print(f"[AVISO] Canal {channel_name} não possui Telegram Chat ID configurado. Pulando...")
            continue
            
        # Varre cada perfil do Instagram cadastrado neste canal
        for profile_item in profiles:
            username = profile_item.get("username")
            keywords = profile_item.get("keywords", [])
            
            if not username:
                continue
                
            print(f"  [PERFIL] Buscando posts recentes de @{username} via API nativa do Instagram...")
            try:
                # Obtém posts via chamada direta de API Web utilizando a sessão ativa do Firefox
                posts = fetch_posts_via_api(L.context._session, username)
                
                # Itera pelos posts obtidos
                post_count = 0
                for post in posts:
                    # Filtra posts muito antigos usando a janela de busca customizada (scan_days)
                    post_age = datetime.utcnow() - post['date_utc']
                    if post_age > timedelta(days=scan_days):
                        print(f"    [INFO] Chegou a posts com mais de {scan_days} dias de idade. Parando busca para @{username}.")
                        break
                        
                    shortcode = post['shortcode']
                    # 1. Verifica se já processou este post anteriormente
                    if shortcode in processed_set:
                        continue
                        
                    caption = post['caption'] or ""
                    post_url = f"https://www.instagram.com/p/{shortcode}/"
                    
                    # 2. Filtra por palavras-chave se configurado para o perfil
                    if keywords:
                        has_keyword = any(kw.lower() in caption.lower() for kw in keywords)
                        if not has_keyword:
                            continue
                            
                    # Formata data em string legível
                    date_str = post['date_utc'].strftime("%Y-%m-%d %H:%M:%S")
                    print(f"    [NOVO] Post detectado! Shortcode: {shortcode} - Publicado em: {date_str} (UTC)")
                    
                    # 3. Processa a legenda e faz tradução se necessário
                    formatted_caption = ""
                    if include_caption and caption:
                        if translate_caption:
                            # Faz a tradução se ativo no canal
                            print("    [TRADUÇÃO] Analisando legenda para tradução/formatação...")
                            translated_caption = translate_text(caption)
                            
                            if translated_caption.strip() != caption.strip():
                                formatted_caption = f"{translated_caption}\n\n<i>(Traduzido do Inglês)</i>"
                            else:
                                formatted_caption = translated_caption
                        else:
                            formatted_caption = caption
                            
                    # Localização opcional
                    location_text = ""
                    if show_location and post.get('location_name'):
                        location_text = f"\n📍 <b>Local:</b> {post['location_name']}"
                        
                    # 4. Formata a mensagem para o Telegram
                    if include_caption and formatted_caption:
                        message_text = (
                            f"<b>📢 NOVO POST: @{username}</b>{location_text}\n\n"
                            f"{formatted_caption}\n\n"
                            f"🔗 <a href='{post_url}'>Ver no Instagram</a>"
                        )
                    else:
                        message_text = (
                            f"<b>🥋 Jiu Jitsu - Novo Post: @{username}</b>{location_text}\n\n"
                            f"🔗 {post_url}"
                        )
                        
                    # 5. Envia as Mídias ou Texto para o Telegram
                    success = False
                    photo_url = post.get('photo_url')
                    video_url = post.get('video_url')
                    
                    # O Telegram limita a legenda em envios de fotos/vídeos a 1024 caracteres
                    # Para textos maiores, enviamos a foto primeiro e o texto em seguida
                    caption_to_send = message_text
                    long_caption_msg = None
                    if len(message_text) > 1024:
                        caption_to_send = f"<b>📢 NOVO POST: @{username}</b>{location_text}\n\n(Legenda completa enviada abaixo...)\n\n🔗 <a href='{post_url}'>Ver no Instagram</a>"
                        long_caption_msg = message_text
                        
                    if post_videos and video_url:
                        print("    [MÍDIA] Transmitindo vídeo para o Telegram...")
                        success = send_telegram_video(bot_token, chat_id, video_url, caption_to_send)
                        if not success:
                            # Fallback para foto
                            success = send_telegram_photo(bot_token, chat_id, photo_url, caption_to_send)
                    elif post_images and photo_url:
                        print("    [MÍDIA] Transmitindo imagem para o Telegram...")
                        success = send_telegram_photo(bot_token, chat_id, photo_url, caption_to_send)
                    else:
                        # Fallback de texto padrão
                        print("    [TEXTO] Transmitindo apenas texto/link para o Telegram...")
                        success = send_telegram_message(bot_token, chat_id, message_text)
                        
                    # Se falhar no envio de mídia (ex: link CDN expirou ou bloqueio do Telegram), tenta texto puro como fallback
                    if not success:
                        print("    [FALLBACK] Envio de mídia falhou. Tentando texto puro...")
                        success = send_telegram_message(bot_token, chat_id, message_text)
                        long_caption_msg = None # Já enviou o texto inteiro no fallback
                        
                    if success:
                        # Se enviou mídia com legenda cortada, manda a legenda inteira em seguida
                        if long_caption_msg:
                            send_telegram_message(bot_token, chat_id, long_caption_msg)
                            
                        # 6. Registra no banco de dados
                        db["processed_posts"].append({
                            "shortcode": shortcode,
                            "processed_at": datetime.now().strftime("%Y-%m-%d"),
                            "channel": channel_key
                        })
                        processed_set.add(shortcode)
                        new_posts_counter += 1
                        
                    time.sleep(3)
                    
                    post_count += 1
                    if post_count >= 5:
                        break
                        
                print(f"  [INFO] Concluído @{username}. Aguardando 15 segundos para o próximo perfil...")
                time.sleep(15)
                
            except Exception as e:
                err_msg = str(e)
                if "graphql/query" in err_msg or "Expecting value" in err_msg or "redirect" in err_msg.lower():
                    print(f"  [AVISO/BLOQUEIO] O Instagram exigiu verificação de segurança (desafio/login) na sua conta logada.")
                    print(f"  [AÇÃO RECOMENDADA] Abra o seu navegador Firefox (de onde o robô obteve a sessão), entre no Instagram.com e verifique se há alguma tela de 'Atividade Suspeita de Login' ou desafio de SMS/E-mail. Confirme a atividade clicando em 'FUI EU' para liberar os acessos do robô imediatamente!")
                else:
                    print(f"  [ERRO] Falha ao processar perfil @{username} via API: {e}")
                time.sleep(5)
                continue
                
    # 7. Janela deslizante: Limpa registros com mais de 30 dias no database
    print("\n[INFO] Fazendo manutenção preventiva no banco de dados local...")
    limit_date = datetime.now() - timedelta(days=30)
    cleaned_posts = []
    
    for item in db["processed_posts"]:
        try:
            processed_date = datetime.strptime(item["processed_at"], "%Y-%m-%d")
            if processed_date >= limit_date:
                cleaned_posts.append(item)
        except Exception:
            # Caso ocorra falha ao ler data antiga, mantém por segurança
            cleaned_posts.append(item)
            
    db["processed_posts"] = cleaned_posts
    save_json(DATABASE_FILE, db)
    print(f"[INFO] Manutenção concluída. Registros históricos ativos: {len(db['processed_posts'])}")
    
    print(f"\n[INFO] Execução finalizada! Total de novos posts enviados: {new_posts_counter}")
    
    # 8. Sincronização com o GitHub se ativo no config
    if configs.get("run_git_sync", False):
        sync_with_github()

if __name__ == "__main__":
    run_scraper()
