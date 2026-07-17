#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import os
from datetime import datetime
from collections import Counter, defaultdict
from urllib.parse import urlparse

# --- Configuración ---
REPORT_FILE = "cuackrecon_report.md"
TARGET_URL = os.environ.get('TARGET_URL', 'No especificado')
MAX_PARAMS_TO_SHOW = 15
MAX_DIRS_TO_SHOW = 25
MAX_URLS_TO_SHOW = 20
# --- Fin Configuración ---


def safe_len(data):
    """Obtiene la longitud de forma segura, manejando listas vacías o None."""
    if data is None:
        return 0
    if isinstance(data, list):
        if not data:
            return 0
        # Si el primer elemento es un error o "Archivo no encontrado."
        if data and isinstance(data[0], str) and data[0] in ["Archivo no encontrado.", "No se encontraron URLs"]:
            return 0
        return len(data)
    return 0


def is_error_or_empty(data):
    """Verifica si los datos contienen un error o están vacíos."""
    if data is None:
        return True
    if isinstance(data, list):
        if not data:
            return True
        if data and isinstance(data[0], str) and data[0] in ["Archivo no encontrado.", "No se encontraron URLs"]:
            return True
        if data and isinstance(data[0], dict) and "error" in data[0]:
            return True
        return False
    if isinstance(data, dict) and "error" in data:
        return True
    return False


def extract_domain(url):
    """Extrae el dominio de una URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        return domain
    except:
        return url


def summarize_urls(urls, max_show=MAX_URLS_TO_SHOW):
    """Resume una lista de URLs mostrando solo las más importantes."""
    if is_error_or_empty(urls):
        return {"count": 0, "summary": [], "has_more": False, "error": "No se encontraron URLs"}
    
    # Filtrar URLs duplicadas y vacías
    clean_urls = [u for u in urls if u and u.strip()]
    if not clean_urls:
        return {"count": 0, "summary": [], "has_more": False, "error": "No se encontraron URLs"}
    
    unique_urls = list(dict.fromkeys(clean_urls))
    
    # Clasificar URLs por tipo
    categorized = defaultdict(list)
    for url in unique_urls[:200]:  # Procesar máximo 200 para rendimiento
        url_lower = url.lower()
        if any(ext in url_lower for ext in ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.ttf', '.eot']):
            categorized['recursos'].append(url)
        elif any(path in url_lower for path in ['/admin', '/api', '/v1', '/v2', '/graphql', '/rest', '/user', '/login', '/register', '/config', '/settings']):
            categorized['criticos'].append(url)
        elif any(path in url_lower for path in ['/static', '/assets', '/img', '/images', '/css', '/js']):
            categorized['estaticos'].append(url)
        else:
            categorized['otros'].append(url)
    
    # Seleccionar las más importantes
    important_urls = []
    important_urls.extend(categorized['criticos'][:10])
    important_urls.extend(categorized['recursos'][:5])
    important_urls.extend(categorized['estaticos'][:3])
    important_urls.extend(categorized['otros'][:5])
    
    # Limitar a max_show
    important_urls = important_urls[:max_show]
    has_more = len(unique_urls) > len(important_urls)
    
    return {
        "count": len(unique_urls),
        "summary": important_urls,
        "has_more": has_more,
        "categorized": {
            "criticos": len(categorized['criticos']),
            "recursos": len(categorized['recursos']),
            "estaticos": len(categorized['estaticos']),
            "otros": len(categorized['otros'])
        }
    }


def parse_nmap(filepath):
    """Analiza el archivo de salida de nmap."""
    results = {
        "open_ports": [],
        "filtered_ports": [],
        "os_info": "No detectado",
    }
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            open_ports_match = re.findall(r'(\d+)/tcp\s+open\s+(\S+)', content)
            for port, service in open_ports_match:
                results["open_ports"].append(f"{port} ({service})")
            filtered_ports_match = re.findall(r'(\d+)/tcp\s+filtered\s+(\S+)', content)
            for port, service in filtered_ports_match:
                results["filtered_ports"].append(f"{port} ({service})")
            os_match = re.search(r'OS details:\s+(.*?)(?:\n|$)', content)
            if os_match:
                results["os_info"] = os_match.group(1)
    except FileNotFoundError:
        results["error"] = f"Archivo {filepath} no encontrado."
    return results


def parse_whatweb(filepath):
    """Analiza el archivo de salida de whatweb."""
    results = {
        "technologies": [],
        "title": "No encontrado",
        "server": "No detectado",
        "ip": "No detectado",
        "country": "No detectado",
    }
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            # Limpiar caracteres de color ANSI
            content = re.sub(r'\x1b\[[0-9;]*m', '', content)
            
            title_match = re.search(r'Title\[([^\]]+)\]', content)
            if title_match:
                results["title"] = title_match.group(1)
            server_match = re.search(r'HTTPServer\[([^\]]+)\]', content)
            if server_match:
                results["server"] = server_match.group(1)
            ip_match = re.search(r'IP\[([^\]]+)\]', content)
            if ip_match:
                results["ip"] = ip_match.group(1)
            country_match = re.search(r'Country\[([^\]]+)\]', content)
            if country_match:
                results["country"] = country_match.group(1)
            
            # Extraer tecnologías limpiando caracteres ANSI
            tech_matches = re.findall(r'\[([^\]]+)\]', content)
            excluded = ["200 OK", results["title"], results["server"], results["ip"], results["country"]]
            for tech in tech_matches:
                tech_clean = re.sub(r'\x1b\[[0-9;]*m', '', tech)
                if tech_clean not in excluded and tech_clean not in results["technologies"] and len(tech_clean) > 1:
                    results["technologies"].append(tech_clean)
    except FileNotFoundError:
        results["error"] = f"Archivo {filepath} no encontrado."
    return results


def parse_historical_urls(filepath):
    """Lee y limpia el archivo de URLs históricas."""
    urls = []
    try:
        with open(filepath, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and line.strip() != "No se encontraron URLs"]
        if not urls:
            urls = []
    except FileNotFoundError:
        urls = []
    return urls


def parse_alive(filepath):
    """Analiza el archivo de hosts activos de httpx."""
    results = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = re.split(r' \[|\] ', line)
                    if len(parts) >= 3:
                        url = parts[0]
                        status = parts[1] if len(parts) > 1 else "N/A"
                        title = parts[2] if len(parts) > 2 else "N/A"
                        tech = parts[3] if len(parts) > 3 else "N/A"
                        results.append({
                            "url": url,
                            "status": status,
                            "title": title,
                            "technologies": tech
                        })
    except FileNotFoundError:
        results = [{"error": f"Archivo {filepath} no encontrado."}]
    return results


def parse_katana(filepath):
    """Lee las URLs del archivo de katana."""
    urls = []
    try:
        with open(filepath, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('No se encontraron')]
        if not urls:
            urls = []
    except FileNotFoundError:
        urls = []
    return urls


def parse_js_files(filepath):
    """Lee los archivos JavaScript encontrados."""
    js_files = []
    try:
        with open(filepath, 'r') as f:
            js_files = [line.strip() for line in f if line.strip() and '.js' in line]
        if not js_files:
            js_files = ["No se encontraron archivos JS"]
    except FileNotFoundError:
        js_files = ["Archivo no encontrado."]
    return js_files


def parse_linkfinder(filepath):
    """Lee los endpoints extraídos de JavaScript por LinkFinder."""
    endpoints = []
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith('http') and not line.startswith('//'):
                    if line.startswith('/') or line.startswith('./') or line.startswith('.'):
                        endpoints.append(line)
        if not endpoints:
            endpoints = ["No se encontraron endpoints"]
    except FileNotFoundError:
        endpoints = ["Archivo no encontrado."]
    return endpoints


def parse_ffuf_json(filepath, param_mode=False):
    """Analiza el archivo JSON de salida de ffuf, filtrando falsos positivos."""
    results = []
    try:
        if not os.path.exists(filepath):
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            for entry in data.get("results", []):
                fuZZ_value = entry.get("input", {}).get("FUZZ", "")
                status = entry.get("status", "")
                url = entry.get("url", "")
                length = entry.get("length", 0)
                
                if not fuZZ_value or not status:
                    continue
                
                # Solo mostrar si no es un error de conexión
                if status != "0" and status != "000":
                    results.append({
                        "path": fuZZ_value,
                        "status": status,
                        "url": url,
                        "length": length,
                        "is_interesting": status != 200
                    })
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return []
    
    # Ordenar: primero los interesantes (status != 200), luego por status
    if results:
        results.sort(key=lambda x: (not x.get('is_interesting', False), x.get('status', 999)))
        
        # Limitar resultados
        limit = MAX_PARAMS_TO_SHOW if param_mode else MAX_DIRS_TO_SHOW
        results = results[:limit]
    
    return results


def parse_nuclei(filepath, tag_type="all"):
    """Analiza archivos de salida de nuclei (JSONL)."""
    findings = []
    try:
        if not os.path.exists(filepath):
            return []
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        template_name = data.get("template", "")
                        info = data.get("info", {})
                        name = info.get("name", "Sin nombre")
                        severity = info.get("severity", "info")
                        description = info.get("description", "Sin descripción")
                        matched = data.get("matched-at", "")
                        
                        # Evitar duplicados por nombre
                        if not any(f.get('nombre') == name for f in findings):
                            if tag_type == "tech":
                                tags = info.get("tags", [])
                                tech_tag = None
                                if isinstance(tags, str):
                                    tags = tags.split(',')
                                for tag in tags:
                                    if tag.lower() in ["cloudflare", "angular", "node", "express", "nginx", "apache", "react", "vue"]:
                                        tech_tag = tag
                                        break
                                findings.append({
                                    "nombre": name,
                                    "tecnologia": tech_tag or "N/A",
                                    "severidad": severity,
                                    "descripcion": description[:200]
                                })
                            else:
                                findings.append({
                                    "nombre": name,
                                    "severidad": severity,
                                    "descripcion": description[:200],
                                    "url_afectada": matched
                                })
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return findings


def parse_custom_scan_unique(filepath):
    """Analiza el archivo de resultados únicos de cuacktest.py."""
    results = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(' | ')
                    if len(parts) >= 3:
                        url = parts[0]
                        status = parts[1].replace('Status: ', '')
                        size = parts[2].replace('Tamaño: ', '').replace(' bytes', '')
                        results.append({
                            "url": url,
                            "status": status,
                            "size": size
                        })
        if not results:
            results = [{"error": "No se encontraron resultados"}]
    except FileNotFoundError:
        results = [{"error": f"Archivo {filepath} no encontrado."}]
    return results


def generate_report():
    """Genera el informe completo en Markdown."""
    print("[+] Generando informe de reconocimiento...")

    # Obtener TARGET_URL de variable de entorno o archivo
    global TARGET_URL
    TARGET_URL = os.environ.get('TARGET_URL', 'No especificado')
    
    # Intentar leer de config.yaml si existe
    if TARGET_URL == 'No especificado' and os.path.exists('config.yaml'):
        try:
            import yaml
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                TARGET_URL = config.get('target_url', 'No especificado')
        except:
            pass

    # Si no hay URL, intentar extraer de algún log
    if TARGET_URL == 'No especificado':
        # Intentar leer de alive.txt
        if os.path.exists('logs/alive.txt'):
            try:
                with open('logs/alive.txt', 'r') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        TARGET_URL = first_line.split(' ')[0] if ' ' in first_line else first_line
            except:
                pass
    """Genera el informe completo en Markdown."""
    print("[+] Generando informe de reconocimiento...")

    # Parsear todos los archivos
    nmap_data = parse_nmap("logs/nmap.txt")
    whatweb_data = parse_whatweb("logs/whatweb.txt")
    historical_urls = parse_historical_urls("logs/historical_urls.txt")
    alive_data = parse_alive("logs/alive.txt")
    katana_urls = parse_katana("logs/katana.txt")
    js_files = parse_js_files("logs/js_files.txt")
    linkfinder_endpoints = parse_linkfinder("logs/endpoints_from_js.txt")
    ffuf_dirs = parse_ffuf_json("logs/ffuf_directories.json", param_mode=False)
    ffuf_params = parse_ffuf_json("logs/ffuf_parameters.json", param_mode=True)
    nuclei_tech = parse_nuclei("logs/nuclei_tech.json", "tech")
    nuclei_exposure = parse_nuclei("logs/nuclei_exposure.json", "exposure")
    nuclei_misconfig = parse_nuclei("logs/nuclei_misconfig.json", "misconfig")
    nuclei_full = parse_nuclei("logs/nuclei_full.json", "full")
    custom_scan = parse_custom_scan_unique("logs/scan_results_unique.txt")

    # Escribir el informe en Markdown
    with open(REPORT_FILE, 'w') as f:
        # Cabecera
        f.write(f"# Informe de Reconocimiento - OWASP Juice Shop\n")
        f.write(f"**Fecha de generación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Objetivo:** {TARGET_URL}\n\n")
        f.write("---\n\n")

        # 1. Resumen Ejecutivo MEJORADO
        f.write("## 📊 Resumen Ejecutivo\n\n")
        f.write(f"Se ha realizado un análisis completo del objetivo **{TARGET_URL}**. \n\n")
        
        # Estadísticas en formato tabla - USANDO safe_len
        f.write("| Categoría | Hallazgos |\n")
        f.write("|-----------|-----------|\n")
        f.write(f"| Puertos abiertos | {len(nmap_data['open_ports'])} |\n")
        f.write(f"| Tecnologías detectadas | {len(whatweb_data['technologies'])} |\n")
        f.write(f"| Hosts activos | {safe_len(alive_data)} |\n")
        f.write(f"| URLs históricas | {safe_len(historical_urls)} |\n")
        f.write(f"| URLs por crawling | {safe_len(katana_urls)} |\n")
        f.write(f"| Archivos JavaScript | {safe_len(js_files)} |\n")
        f.write(f"| Endpoints en JS | {safe_len(linkfinder_endpoints)} |\n")
        f.write(f"| Directorios/archivos | {safe_len(ffuf_dirs)} |\n")
        f.write(f"| Parámetros relevantes | {safe_len(ffuf_params)} |\n")
        f.write(f"| Hallazgos Nuclei | {safe_len(nuclei_full)} |\n\n")
        
        # Tecnologías principales
        f.write("**Tecnologías clave detectadas:**\n\n")
        if whatweb_data['technologies']:
            tech_list = ', '.join(whatweb_data['technologies'][:10])
            f.write(f"- {tech_list}\n")
            if len(whatweb_data['technologies']) > 10:
                f.write(f"- *... y {len(whatweb_data['technologies']) - 10} más*\n")
        else:
            f.write("- No se detectaron tecnologías específicas\n")
        f.write("\n---\n\n")

        # 2. Escaneo de Puertos (Nmap)
        f.write("## 🔌 1. Escaneo de Puertos (Nmap)\n\n")
        if "error" in nmap_data:
            f.write(f"**Error:** {nmap_data['error']}\n\n")
        else:
            f.write(f"**Sistema Operativo:** {nmap_data['os_info']}\n\n")
            f.write("**Puertos abiertos:**\n\n")
            if nmap_data['open_ports']:
                for port in nmap_data['open_ports']:
                    f.write(f"- {port}\n")
            else:
                f.write("No se encontraron puertos abiertos.\n")
            f.write("\n")
            if nmap_data['filtered_ports']:
                f.write("**Puertos filtrados:**\n\n")
                for port in nmap_data['filtered_ports']:
                    f.write(f"- {port}\n")
                f.write("\n")
        f.write("---\n\n")

        # 3. Fingerprinting (WhatWeb)
        f.write("## 🏷️ 2. Fingerprinting (WhatWeb)\n\n")
        if "error" in whatweb_data:
            f.write(f"**Error:** {whatweb_data['error']}\n\n")
        else:
            f.write(f"**IP:** {whatweb_data['ip']}\n")
            f.write(f"**País:** {whatweb_data['country']}\n")
            f.write(f"**Servidor:** {whatweb_data['server']}\n")
            f.write(f"**Título:** {whatweb_data['title']}\n\n")
            f.write("**Tecnologías detectadas:**\n\n")
            if whatweb_data['technologies']:
                for tech in whatweb_data['technologies']:
                    f.write(f"- {tech}\n")
            else:
                f.write("No se detectaron tecnologías específicas.\n")
            f.write("\n")
        f.write("---\n\n")

        # 4. Hosts Activos (httpx)
        f.write("## 🌐 3. Hosts Activos (httpx)\n\n")
        if alive_data and isinstance(alive_data[0], dict) and "error" in alive_data[0]:
            f.write(f"**Error:** {alive_data[0]['error']}\n\n")
        else:
            f.write("| URL | Estado | Título | Tecnologías |\n")
            f.write("|-----|--------|--------|-------------|\n")
            show_hosts = alive_data[:10] if alive_data else []
            for host in show_hosts:
                f.write(f"| {host['url']} | {host['status']} | {host['title']} | {host['technologies']} |\n")
            if len(alive_data) > 10:
                f.write(f"\n*... y {len(alive_data) - 10} hosts más.*\n")
            f.write("\n")
        f.write("---\n\n")

        # 5. URLs Históricas - RESUMEN
        f.write("## 📜 4. URLs Históricas\n\n")
        hist_summary = summarize_urls(historical_urls, max_show=15)
        if hist_summary.get('error') or hist_summary['count'] == 0:
            f.write("No se encontraron URLs históricas.\n\n")
        else:
            f.write(f"Se encontraron **{hist_summary['count']}** URLs históricas.\n\n")
            
            # Mostrar categorías
            if 'categorized' in hist_summary:
                f.write("**Distribución por tipo:**\n\n")
                f.write(f"- 🔐 Rutas críticas (API, admin, etc.): {hist_summary['categorized']['criticos']}\n")
                f.write(f"- 🖼️ Recursos (js, css, imágenes): {hist_summary['categorized']['recursos']}\n")
                f.write(f"- 📁 Estáticos: {hist_summary['categorized']['estaticos']}\n")
                f.write(f"- 📄 Otros: {hist_summary['categorized']['otros']}\n\n")
            
            f.write("**Rutas más relevantes:**\n\n")
            for url in hist_summary['summary']:
                f.write(f"- `{url}`\n")
            
            if hist_summary.get('has_more'):
                f.write(f"\n*... y {hist_summary['count'] - len(hist_summary['summary'])} URLs más.*\n")
            f.write("\n")
        f.write("---\n\n")

        # 6. Crawling (Katana) - RESUMEN
        f.write("## 🕷️ 5. Crawling (Katana)\n\n")
        katana_summary = summarize_urls(katana_urls, max_show=15)
        if katana_summary.get('error') or katana_summary['count'] == 0:
            f.write("No se encontraron URLs durante el crawling.\n\n")
        else:
            f.write(f"Se encontraron **{katana_summary['count']}** URLs durante el crawling.\n\n")
            
            if 'categorized' in katana_summary:
                f.write("**Distribución por tipo:**\n\n")
                f.write(f"- 🔐 Rutas críticas: {katana_summary['categorized']['criticos']}\n")
                f.write(f"- 🖼️ Recursos: {katana_summary['categorized']['recursos']}\n")
                f.write(f"- 📁 Estáticos: {katana_summary['categorized']['estaticos']}\n")
                f.write(f"- 📄 Otros: {katana_summary['categorized']['otros']}\n\n")
            
            f.write("**Rutas principales:**\n\n")
            for url in katana_summary['summary']:
                f.write(f"- `{url}`\n")
            
            if katana_summary.get('has_more'):
                f.write(f"\n*... y {katana_summary['count'] - len(katana_summary['summary'])} URLs más.*\n")
            f.write("\n")
        f.write("---\n\n")

        # 7. Archivos JavaScript
        f.write("## 📦 6. Archivos JavaScript\n\n")
        if js_files and not is_error_or_empty(js_files):
            f.write(f"Se encontraron **{len(js_files)}** archivos JavaScript:\n\n")
            for js in js_files[:10]:  # Mostrar solo 10
                f.write(f"- `{js}`\n")
            if len(js_files) > 10:
                f.write(f"\n*... y {len(js_files) - 10} archivos más.*\n")
            f.write("\n")
        else:
            f.write("No se encontraron archivos JavaScript.\n\n")
        f.write("---\n\n")

        # 8. Endpoints en JavaScript (LinkFinder) - RESUMEN
        f.write("## 🔍 7. Endpoints en JavaScript (LinkFinder)\n\n")
        if linkfinder_endpoints and not is_error_or_empty(linkfinder_endpoints):
            f.write(f"Se extrajeron **{len(linkfinder_endpoints)}** endpoints de los archivos JavaScript.\n\n")
            f.write("**Endpoints más relevantes:**\n\n")
            
            # Filtrar endpoints importantes
            important_endpoints = []
            for endpoint in linkfinder_endpoints:
                if any(key in endpoint.lower() for key in ['admin', 'api', 'login', 'user', 'config', 'settings', 'upload', 'download']):
                    important_endpoints.append(endpoint)
            
            show_endpoints = important_endpoints[:15] if important_endpoints else linkfinder_endpoints[:15]
            
            for endpoint in show_endpoints:
                f.write(f"- `{endpoint}`\n")
            
            if len(linkfinder_endpoints) > 15:
                f.write(f"\n*... y {len(linkfinder_endpoints) - 15} endpoints más.*\n")
            f.write("\n")
        else:
            f.write("No se extrajeron endpoints de los archivos JavaScript.\n\n")
        f.write("---\n\n")

        # 9. Fuerza Bruta de Directorios (ffuf) - FILTRADO
        f.write("## 📁 8. Fuerza Bruta de Directorios/Archivos (ffuf)\n\n")
        if ffuf_dirs and isinstance(ffuf_dirs[0], dict) and "error" in ffuf_dirs[0]:
            f.write(f"**Error:** {ffuf_dirs[0]['error']}\n\n")
        elif not ffuf_dirs:
            f.write("No se encontraron directorios/archivos.\n\n")
        else:
            f.write(f"Se encontraron **{len(ffuf_dirs)}** directorios/archivos relevantes:\n\n")
            f.write("| Ruta | Estado | Tamaño (bytes) |\n")
            f.write("|------|--------|----------------|\n")
            for entry in ffuf_dirs:
                status_marker = "⚠️ " if entry['status'] != 200 else ""
                f.write(f"| {status_marker}{entry['path']} | {entry['status']} | {entry.get('length', 'N/A')} |\n")
            f.write("\n")
            f.write("*⚠️ = Estado diferente de 200 (potencialmente interesante)*\n\n")
        f.write("---\n\n")

        # 10. Fuerza Bruta de Parámetros (ffuf) - FILTRADO Y LIMITADO
        f.write("## 🔑 9. Fuerza Bruta de Parámetros (ffuf)\n\n")
        if ffuf_params and isinstance(ffuf_params[0], dict) and "error" in ffuf_params[0]:
            f.write(f"**Error:** {ffuf_params[0]['error']}\n\n")
        elif not ffuf_params:
            f.write("No se encontraron parámetros interesantes.\n\n")
        else:
            f.write(f"**Nota:** Se encontraron múltiples parámetros, pero muchos devuelven un código 200 (falsos positivos). ")
            f.write(f"Se muestran solo **{len(ffuf_params)}** parámetros con códigos de estado diferentes a 200 o con comportamientos atípicos:\n\n")
            
            f.write("| Parámetro | Estado | Tamaño (bytes) |\n")
            f.write("|-----------|--------|----------------|\n")
            for entry in ffuf_params:
                status_marker = "⚠️ " if entry['status'] != 200 else ""
                f.write(f"| {status_marker}{entry['path']} | {entry['status']} | {entry.get('length', 'N/A')} |\n")
            f.write("\n")
            f.write("*⚠️ = Estado diferente de 200 (potencialmente interesante)*\n\n")
        f.write("---\n\n")

        # 11. Escaneo de Vulnerabilidades (Nuclei) - RESUMEN
        f.write("## 🛡️ 10. Escaneo de Vulnerabilidades (Nuclei)\n\n")

        # Tecnologías
        f.write("### 10.1 Tecnologías Detectadas\n\n")
        if nuclei_tech and isinstance(nuclei_tech[0], dict) and "error" in nuclei_tech[0]:
            f.write(f"**Error:** {nuclei_tech[0]['error']}\n\n")
        elif not nuclei_tech:
            f.write("No se detectaron tecnologías.\n\n")
        else:
            f.write("| Tecnología | Severidad |\n")
            f.write("|------------|-----------|\n")
            for tech in nuclei_tech[:15]:  # Mostrar solo 15
                f.write(f"| {tech.get('tecnologia', 'N/A')} | {tech.get('severidad', 'info')} |\n")
            if len(nuclei_tech) > 15:
                f.write(f"\n*... y {len(nuclei_tech) - 15} más.*\n")
            f.write("\n")

        # Exposiciones
        f.write("### 10.2 Exposiciones\n\n")
        if nuclei_exposure and isinstance(nuclei_exposure[0], dict) and "error" in nuclei_exposure[0]:
            f.write(f"**Error:** {nuclei_exposure[0]['error']}\n\n")
        elif not nuclei_exposure:
            f.write("No se encontraron exposiciones.\n\n")
        else:
            f.write("| Hallazgo | Severidad | URL Afectada |\n")
            f.write("|----------|-----------|--------------|\n")
            for exp in nuclei_exposure[:10]:  # Mostrar solo 10
                f.write(f"| {exp.get('nombre', 'N/A')[:50]} | {exp.get('severidad', 'info')} | {exp.get('url_afectada', 'N/A')} |\n")
            if len(nuclei_exposure) > 10:
                f.write(f"\n*... y {len(nuclei_exposure) - 10} exposiciones más.*\n")
            f.write("\n")

        # Misconfiguraciones
        f.write("### 10.3 Misconfiguraciones\n\n")
        if nuclei_misconfig and isinstance(nuclei_misconfig[0], dict) and "error" in nuclei_misconfig[0]:
            f.write(f"**Error:** {nuclei_misconfig[0]['error']}\n\n")
        elif not nuclei_misconfig:
            f.write("No se encontraron misconfiguraciones.\n\n")
        else:
            f.write("| Hallazgo | Severidad |\n")
            f.write("|----------|-----------|\n")
            for mis in nuclei_misconfig[:10]:  # Mostrar solo 10
                f.write(f"| {mis.get('nombre', 'N/A')[:50]} | {mis.get('severidad', 'info')} |\n")
            if len(nuclei_misconfig) > 10:
                f.write(f"\n*... y {len(nuclei_misconfig) - 10} misconfiguraciones más.*\n")
            f.write("\n")

        # Escaneo Completo
        f.write("### 10.4 Escaneo Completo (Resumen)\n\n")
        if nuclei_full and isinstance(nuclei_full[0], dict) and "error" in nuclei_full[0]:
            f.write(f"**Error:** {nuclei_full[0]['error']}\n\n")
        elif not nuclei_full:
            f.write("No se encontraron hallazgos.\n\n")
        else:
            f.write(f"Se encontraron **{len(nuclei_full)}** hallazgos únicos en total.\n\n")
            
            # Contar por severidad
            severity_count = Counter()
            for h in nuclei_full:
                severity_count[h.get('severidad', 'info')] += 1
            
            f.write("**Distribución por severidad:**\n\n")
            for severity, count in sorted(severity_count.items(), key=lambda x: ['critical', 'high', 'medium', 'low', 'info'].index(x[0]) if x[0] in ['critical', 'high', 'medium', 'low', 'info'] else 5):
                if count > 0:
                    emoji = "🔴" if severity == "critical" else "🟠" if severity == "high" else "🟡" if severity == "medium" else "🔵" if severity == "low" else "⚪"
                    f.write(f"- {emoji} **{severity.capitalize()}**: {count}\n")
            f.write("\n")
            
            # Mostrar hallazgos críticos/altos
            critical_high = [h for h in nuclei_full if h.get('severidad', '').lower() in ['critical', 'high']]
            if critical_high:
                f.write("**Hallazgos Críticos/Altos:**\n\n")
                f.write("| Hallazgo | Severidad |\n")
                f.write("|----------|-----------|\n")
                for h in critical_high[:10]:
                    f.write(f"| {h.get('nombre', 'N/A')[:60]} | {h.get('severidad', 'info')} |\n")
                if len(critical_high) > 10:
                    f.write(f"\n*... y {len(critical_high) - 10} hallazgos críticos/altos más.*\n")
                f.write("\n")
            else:
                f.write("No se encontraron hallazgos críticos o altos.\n\n")
        f.write("---\n\n")

        # 12. Escaneo Personalizado (cuacktest.py)
        f.write("## 🎯 11. Escaneo Personalizado (cuacktest.py)\n\n")
        if custom_scan and isinstance(custom_scan[0], dict) and "error" in custom_scan[0]:
            f.write(f"**Error:** {custom_scan[0]['error']}\n\n")
        elif not custom_scan:
            f.write("No se encontraron resultados.\n\n")
        else:
            f.write(f"Se encontraron **{len(custom_scan)}** resultados únicos.\n\n")
            f.write("**Resultados más relevantes:**\n\n")
            f.write("| URL | Estado | Tamaño |\n")
            f.write("|-----|--------|--------|\n")
            for entry in custom_scan[:15]:  # Mostrar solo 15
                f.write(f"| {entry['url']} | {entry['status']} | {entry['size']} bytes |\n")
            if len(custom_scan) > 15:
                f.write(f"\n*... y {len(custom_scan) - 15} resultados más.*\n")
            f.write("\n")
        f.write("---\n\n")

        # Recomendaciones
        f.write("## 💡 Recomendaciones\n\n")
        f.write("### Prioridad Alta\n\n")
        f.write("1. **Revisar endpoints críticos** encontrados en JavaScript (API, admin, login, etc.)\n")
        f.write("2. **Analizar hallazgos críticos/altos** de Nuclei\n")
        f.write("3. **Verificar exposiciones** de información sensible\n\n")
        
        f.write("### Prioridad Media\n\n")
        f.write("1. **Investigar directorios** con códigos de estado no 200\n")
        f.write("2. **Revisar parámetros** con comportamientos atípicos\n")
        f.write("3. **Analizar tecnologías** detectadas por vulnerabilidades conocidas\n\n")
        
        f.write("### Prioridad Baja\n\n")
        f.write("1. **Documentar hallazgos** para futuras pruebas\n")
        f.write("2. **Actualizar herramientas** y repetir escaneos periódicamente\n")
        f.write("3. **Realizar pruebas manuales** con Burp Suite\n\n")

        f.write("---\n\n")
        f.write("*📝 Informe generado automáticamente por `cuackreport.py`*\n")

    print(f"[+] Informe generado: {REPORT_FILE}")


if __name__ == "__main__":
    # Si se ejecuta desde el script, pasar TARGET_URL como variable de entorno
    generate_report()
