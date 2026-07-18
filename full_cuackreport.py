#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import os
import statistics
from datetime import datetime
from collections import Counter, defaultdict
from urllib.parse import urlparse, urljoin, parse_qs
import math
import hashlib
from itertools import groupby
import sys

# --- Configuración ---
REPORT_FILE = "cuackrecon_megareport.html"
target_url = os.environ.get('target_url', 'No especificado')
MAX_ITEMS_TO_SHOW = 30
# --- Fin Configuración ---

class TreeBuilder:
    """Construye estructuras de árbol para rutas y endpoints"""
    
    @staticmethod
    def build_path_tree(paths, max_depth=30):
        """Construye un árbol jerárquico de rutas"""
        tree = {}
        
        for path in paths:  # Limitar para rendimiento
            if not path or path.startswith('http'):
                continue
                
            # Limpiar path
            clean_path = path.strip()
            if clean_path.startswith('./'):
                clean_path = clean_path[2:]
            if clean_path.startswith('/'):
                clean_path = clean_path[1:]
            
            parts = [p for p in clean_path.split('/') if p and p != '..']
            
            if not parts:
                continue
                
            current = tree
            for i, part in enumerate(parts[:max_depth]):
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        return tree
    
    @staticmethod
    def tree_to_html(tree, prefix="", is_last=True, depth=0):
        """Convierte un árbol a HTML con formato visual - Versión con enlaces clicables"""
        html = []
        items = list(tree.items())
        
        # Obtener la URL base del entorno o usar la del reporte
        base_url = sys.argv[1]
        
        # Si no hay URL base, intentar obtenerla del archivo alive.txt
        if not base_url and os.path.exists('logs/alive.txt'):
            try:
                with open('logs/alive.txt', 'r') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        base_url = first_line.split(' ')[0] if ' ' in first_line else first_line
                        base_url = base_url.rstrip('/')
            except:
                pass
        
        # Si no hay URL base, usar un marcador de posición
        if not base_url:
            base_url = "#"
        
        for i, (key, value) in enumerate(items):
            is_last_item = (i == len(items) - 1)
            
            # Determinar el prefijo visual
            if depth == 0:
                indent = ""
                connector = "📁 "
            else:
                if is_last:
                    indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
                else:
                    indent = "│&nbsp;&nbsp;&nbsp;&nbsp;" * depth
                
                if is_last_item:
                    connector = "└── "
                else:
                    connector = "├── "
            
            # Construir la ruta completa para el enlace
            # Reconstruir la ruta completa desde el nodo actual
            path_parts = []
            
            # Necesitamos construir la ruta completa desde el nodo actual
            # Para eso, pasamos el prefijo acumulado
            def get_path_from_node(tree, target_key, current_path=""):
                for k, v in tree.items():
                    new_path = current_path + "/" + k if current_path else k
                    if k == target_key:
                        return new_path
                    if v:
                        result = get_path_from_node(v, target_key, new_path)
                        if result:
                            return result
                return None
            
            # Esta es una versión simplificada - construimos la ruta relativa
            # desde el nodo actual
            full_path = "/" + key if depth == 0 else "/" + key
            
            # Intentar construir la ruta completa (esto es simplificado)
            # Para un enfoque más preciso, necesitaríamos pasar el path acumulado
            # desde la raíz
            link_url = f"{base_url}{full_path}"
            
            # Ícono según tipo
            if value:
                icon = "📂 "
            else:
                icon = "📄 "
            
            # Si tiene hijos, recursión con enlace en el directorio
            if value:
                html.append(f'<div style="font-family: monospace; font-size: 0.9em; padding: 2px 0;">')
                # El directorio es un enlace
                html.append(f'{indent}{connector}{icon}<a href="{link_url}" target="_blank" style="color: #63b3ed; text-decoration: none; font-weight: bold; cursor: pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'"><strong>{key}</strong>/</a>')
                html.append('</div>')
                
                # Recursión para hijos - necesitamos pasar el path acumulado
                # Para esto, modificamos la recursión para pasar el path actual
                child_html = TreeBuilder.tree_to_html_with_path(
                    value, 
                    prefix + ("" if is_last_item else "│   "), 
                    is_last_item,
                    depth + 1,
                    full_path  # Pasamos el path actual
                )
                html.append(child_html)
            else:
                # Hoja (archivo) - también es un enlace
                html.append(f'<div style="font-family: monospace; font-size: 0.9em; padding: 2px 0;">')
                html.append(f'{indent}{connector}{icon}<a href="{link_url}" target="_blank" style="color: #68d391; text-decoration: none; cursor: pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{key}</a>')
                html.append('</div>')
        
        return "\n".join(html)
    

    @staticmethod
    def tree_to_html_with_path(tree, prefix="", is_last=True, depth=0, current_path=""):
        """Versión recursiva que mantiene el path acumulado para generar enlaces correctos"""
        html = []
        items = list(tree.items())
        
        # Obtener la URL base
        base_url = sys.argv[1]
        
        if not base_url and os.path.exists('logs/alive.txt'):
            try:
                with open('logs/alive.txt', 'r') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        base_url = first_line.split(' ')[0] if ' ' in first_line else first_line
                        base_url = base_url.rstrip('/')
            except:
                pass
        if not base_url:
            base_url = "#"
        
        for i, (key, value) in enumerate(items):
            is_last_item = (i == len(items) - 1)
            
            # Construir el path completo para este nodo
            # Si current_path está vacío o es solo "/", usamos solo la key
            if current_path == "/" or not current_path:
                full_path = "/" + key
            else:
                full_path = current_path + "/" + key
            
            link_url = f"{base_url}{full_path}"
            
            # Determinar el prefijo visual
            if depth == 0:
                indent = ""
                connector = "📁 "
            else:
                if is_last:
                    indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
                else:
                    indent = "│&nbsp;&nbsp;&nbsp;&nbsp;" * depth
                
                if is_last_item:
                    connector = "└── "
                else:
                    connector = "├── "
            
            # Ícono según tipo
            if value:
                icon = "📂 "
            else:
                icon = "📄 "
            
            # Si tiene hijos, recursión
            if value:
                html.append(f'<div style="font-family: monospace; font-size: 0.9em; padding: 2px 0;">')
                html.append(f'{indent}{connector}{icon}<a href="{link_url}" target="_blank" style="color: #63b3ed; text-decoration: none; font-weight: bold; cursor: pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'"><strong>{key}</strong>/</a>')
                html.append('</div>')
                
                # Recursión pasando el nuevo path
                child_html = TreeBuilder.tree_to_html_with_path(
                    value, 
                    prefix + ("" if is_last_item else "│   "), 
                    is_last_item,
                    depth + 1,
                    full_path
                )
                html.append(child_html)
            else:
                # Hoja (archivo)
                html.append(f'<div style="font-family: monospace; font-size: 0.9em; padding: 2px 0;">')
                html.append(f'{indent}{connector}{icon}<a href="{link_url}" target="_blank" style="color: #68d391; text-decoration: none; cursor: pointer;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{key}</a>')
                html.append('</div>')
        
        return "\n".join(html)

    @staticmethod
    def get_tree_stats(tree):
        """Obtiene estadísticas del árbol"""
        def count_nodes(node):
            count = len(node)
            for child in node.values():
                if child:
                    count += count_nodes(child)
            return count
        
        def get_depth(node, current_depth=0):
            if not node:
                return current_depth
            max_depth = current_depth
            for child in node.values():
                if child:
                    child_depth = get_depth(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
            return max_depth
        
        return {
            'total_nodes': count_nodes(tree),
            'max_depth': get_depth(tree),
            'total_dirs': len(tree)
        }

class StatisticalAnalyzer:
    """Clase para análisis estadístico avanzado"""
    
    def __init__(self):
        self.stats = {
            'response_codes': Counter(),
            'path_lengths': [],
            'url_depth': Counter(),
            'file_extensions': Counter(),
            'parameter_patterns': Counter(),
            'tech_stack': Counter(),
            'severity_distribution': Counter(),
            'time_series': defaultdict(list),
            'http_methods': Counter(),
            'endpoint_categories': Counter(),
            'path_patterns': Counter()
        }
    
    def analyze_urls(self, urls):
        """Analiza estadísticas de URLs"""
        if not urls or len(urls) == 0:
            return {}
        
        depths = []
        extensions = []
        path_patterns = []
        
        for url in urls[:1000]:
            if not url:
                continue
                
            try:
                parsed = urlparse(url)
                
                # Profundidad
                path_parts = [p for p in parsed.path.split('/') if p]
                depth = len(path_parts)
                depths.append(depth)
                self.stats['url_depth'][depth] += 1
                
                # Extensiones
                if '.' in parsed.path:
                    ext = parsed.path.split('.')[-1].lower()
                    if ext and len(ext) < 10:
                        extensions.append(ext)
                        self.stats['file_extensions'][ext] += 1
                
                # Parámetros
                if parsed.query:
                    params = parse_qs(parsed.query)
                    for param_name in params.keys():
                        self.stats['parameter_patterns'][param_name] += 1
                
                # Patrones de ruta
                if len(path_parts) >= 2:
                    pattern = f"/{path_parts[0]}/..."
                    path_patterns.append(pattern)
                    self.stats['path_patterns'][pattern] += 1
                    
            except Exception:
                continue
        
        self.stats['path_lengths'] = depths
        
        return {
            'total_urls': len(urls),
            'unique_urls': len(set(urls)),
            'avg_depth': statistics.mean(depths) if depths else 0,
            'max_depth': max(depths) if depths else 0,
            'min_depth': min(depths) if depths else 0,
            'std_depth': statistics.stdev(depths) if len(depths) > 1 else 0,
            'median_depth': statistics.median(depths) if depths else 0,
            'extensions': dict(self.stats['file_extensions'].most_common(15)),
            'parameters': dict(self.stats['parameter_patterns'].most_common(15)),
            'path_patterns': dict(self.stats['path_patterns'].most_common(10))
        }
    
    def analyze_endpoints(self, endpoints):
        """Analiza endpoints para extraer patrones y categorías"""
        if not endpoints:
            return {}
        
        categories = {
            'api': 0,
            'admin': 0,
            'auth': 0,
            'config': 0,
            'data': 0,
            'file': 0,
            'user': 0,
            'system': 0,
            'other': 0
        }
        
        methods = Counter()
        
        for endpoint in endpoints[:500]:
            endpoint_lower = endpoint.lower()
            
            # Categorizar
            if '/api/' in endpoint_lower or endpoint_lower.startswith('api'):
                categories['api'] += 1
            elif 'admin' in endpoint_lower:
                categories['admin'] += 1
            elif 'login' in endpoint_lower or 'auth' in endpoint_lower or 'sign' in endpoint_lower:
                categories['auth'] += 1
            elif 'config' in endpoint_lower or 'setting' in endpoint_lower:
                categories['config'] += 1
            elif 'data' in endpoint_lower or 'export' in endpoint_lower:
                categories['data'] += 1
            elif 'file' in endpoint_lower or 'upload' in endpoint_lower or 'download' in endpoint_lower:
                categories['file'] += 1
            elif 'user' in endpoint_lower or 'profile' in endpoint_lower:
                categories['user'] += 1
            elif 'system' in endpoint_lower or 'server' in endpoint_lower:
                categories['system'] += 1
            else:
                categories['other'] += 1
            
            # Detectar métodos HTTP implícitos
            if any(word in endpoint_lower for word in ['get', 'list', 'fetch']):
                methods['GET'] += 1
            elif any(word in endpoint_lower for word in ['post', 'create', 'add', 'new']):
                methods['POST'] += 1
            elif any(word in endpoint_lower for word in ['put', 'update', 'edit', 'modify']):
                methods['PUT'] += 1
            elif any(word in endpoint_lower for word in ['delete', 'remove', 'destroy']):
                methods['DELETE'] += 1
        
        return {
            'total': len(endpoints),
            'categories': dict(categories),
            'methods': dict(methods.most_common()),
            'unique_patterns': len(set([e.split('/')[1] if '/' in e else e for e in endpoints if e]))
        }
    
    def calculate_risk_score(self, findings):
        """Calcula un score de riesgo basado en hallazgos"""
        if not findings:
            return {
                'total_score': 0,
                'severity_distribution': {},
                'weighted_average': 0
            }
        
        risk_weights = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 2,
            'info': 1
        }
        
        score = 0
        severity_count = Counter()
        
        for finding in findings:
            severity = finding.get('severidad', 'info').lower()
            severity_count[severity] += 1
            score += risk_weights.get(severity, 1)
        
        return {
            'total_score': score,
            'severity_distribution': dict(severity_count),
            'weighted_average': score / len(findings) if findings else 0
        }
    
    def get_vulnerability_trends(self, nuclei_data):
        """Analiza tendencias de vulnerabilidades"""
        trends = {
            'by_severity': Counter(),
            'by_category': Counter(),
            'by_template': Counter(),
            'by_tag': Counter(),
            'by_year': Counter()
        }
        
        for finding in nuclei_data:
            severity = finding.get('severidad', 'info').lower()
            trends['by_severity'][severity] += 1
            
            # Categorización avanzada
            name = finding.get('nombre', '').lower()
            tags = finding.get('tags', [])
            
            # Por categoría
            if 'xss' in name:
                trends['by_category']['XSS (Cross-Site Scripting)'] += 1
            elif 'sql' in name:
                trends['by_category']['SQL Injection'] += 1
            elif 'path traversal' in name or 'directory traversal' in name:
                trends['by_category']['Path Traversal'] += 1
            elif 'misconfig' in name or 'misconfiguration' in name:
                trends['by_category']['Misconfiguration'] += 1
            elif 'exposure' in name or 'disclosure' in name:
                trends['by_category']['Information Exposure'] += 1
            elif 'csrf' in name:
                trends['by_category']['CSRF'] += 1
            elif 'rce' in name or 'command' in name:
                trends['by_category']['RCE'] += 1
            elif 'ssrf' in name:
                trends['by_category']['SSRF'] += 1
            else:
                trends['by_category']['Other'] += 1
            
            # Por año
            year_match = re.search(r'20\d{2}', name)
            if year_match:
                trends['by_year'][year_match.group()] += 1
            
            # Por tags
            for tag in tags[:5]:
                if tag and len(tag) > 2:
                    trends['by_tag'][tag.lower()] += 1
            
            trends['by_template'][name[:40]] += 1
        
        return trends
def build_master_tree(all_sources):
    """Construye un árbol maestro combinando múltiples fuentes de paths"""
    tree = {}
    
    # Combinar todas las rutas de diferentes fuentes
    all_paths = []
    
    # 1. URLs históricas
    if 'historical' in all_sources:
        all_paths.extend(all_sources['historical'])
    
    # 2. URLs de Katana
    if 'katana' in all_sources:
        all_paths.extend(all_sources['katana'])
    
    # 3. Endpoints de JavaScript
    if 'endpoints' in all_sources:
        all_paths.extend(all_sources['endpoints'])
    
    # 4. Directorios de FFUF
    if 'ffuf' in all_sources:
        all_paths.extend(all_sources['ffuf'])
    
    # 5. Hosts activos
    if 'alive' in all_sources:
        all_paths.extend(all_sources['alive'])
    
    # 6. Escaneo personalizado
    if 'custom' in all_sources:
        all_paths.extend(all_sources['custom'])
    
    # Construir árbol con todas las rutas
    for path in all_paths[:10000]:  # Límite para rendimiento
        if not path:
            continue
        
        # Limpiar y extraer path
        if path.startswith('http'):
            try:
                parsed = urlparse(path)
                clean_path = parsed.path
            except:
                continue
        else:
            clean_path = path
        
        # Limpiar path
        clean_path = clean_path.strip()
        if clean_path.startswith('./'):
            clean_path = clean_path[2:]
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]
        
        # Eliminar query strings y fragmentos
        if '?' in clean_path:
            clean_path = clean_path.split('?')[0]
        if '#' in clean_path:
            clean_path = clean_path.split('#')[0]
        
        parts = [p for p in clean_path.split('/') if p and p != '..' and p != '.']
        
        if not parts:
            continue
            
        current = tree
        for part in parts[:50]:  # Profundidad máxima 50
            if part not in current:
                current[part] = {}
            current = current[part]
    
    return tree

def safe_len(data):
    """Obtiene la longitud de forma segura"""
    if data is None:
        return 0
    if isinstance(data, list):
        if not data:
            return 0
        if data and isinstance(data[0], str) and data[0] in ["Archivo no encontrado.", "No se encontraron URLs"]:
            return 0
        return len(data)
    if isinstance(data, dict):
        return len(data.get('results', []))
    return 0

def is_error_or_empty(data):
    """Verifica si los datos contienen un error o están vacíos"""
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

def parse_nmap(filepath):
    """Analiza el archivo de salida de nmap con estadísticas avanzadas"""
    results = {
        "open_ports": [],
        "filtered_ports": [],
        "os_info": "No detectado",
        "port_stats": {},
        "service_distribution": Counter()
    }
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
            # Extraer puertos abiertos con servicios
            open_ports_match = re.findall(r'(\d+)/tcp\s+open\s+(\S+)', content)
            for port, service in open_ports_match:
                results["open_ports"].append(f"{port} ({service})")
                results["service_distribution"][service] += 1
            
            # Extraer puertos filtrados
            filtered_ports_match = re.findall(r'(\d+)/tcp\s+filtered\s+(\S+)', content)
            for port, service in filtered_ports_match:
                results["filtered_ports"].append(f"{port} ({service})")
            
            # Estadísticas de puertos
            if results["open_ports"]:
                ports = [int(p.split()[0]) for p in results["open_ports"] if p.split()[0].isdigit()]
                if ports:
                    results["port_stats"] = {
                        'total': len(ports),
                        'min': min(ports),
                        'max': max(ports),
                        'avg': sum(ports) / len(ports),
                        'common_ports': [p for p in ports if p in [80, 443, 8080, 8443, 22, 21, 25, 53]]
                    }
            
            # Sistema operativo
            os_match = re.search(r'OS details:\s+(.*?)(?:\n|$)', content)
            if os_match:
                results["os_info"] = os_match.group(1)
            
            # Tiempo de escaneo
            time_match = re.search(r'Scanning completed in ([\d.]+) seconds', content)
            if time_match:
                results["scan_time"] = float(time_match.group(1))
                
    except FileNotFoundError:
        results["error"] = f"Archivo {filepath} no encontrado."
    return results

def parse_whatweb(filepath):
    """Analiza el archivo de salida de whatweb con estadísticas"""
    results = {
        "technologies": [],
        "title": "No encontrado",
        "server": "No detectado",
        "ip": "No detectado",
        "country": "No detectado",
        "tech_categories": Counter(),
        "tech_versions": {}
    }
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            content = re.sub(r'\x1b\[[0-9;]*m', '', content)
            
            # Extraer información básica
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
            
            # Extraer tecnologías con versiones
            tech_matches = re.findall(r'\[([^\]]+)\]', content)
            excluded = ["200 OK", results["title"], results["server"], results["ip"], results["country"]]
            
            for tech in tech_matches:
                tech_clean = re.sub(r'\x1b\[[0-9;]*m', '', tech)
                if tech_clean not in excluded and tech_clean not in results["technologies"] and len(tech_clean) > 1:
                    results["technologies"].append(tech_clean)
                    
                    # Categorizar tecnologías
                    tech_lower = tech_clean.lower()
                    if any(x in tech_lower for x in ['js', 'javascript', 'react', 'vue', 'angular', 'jquery']):
                        results["tech_categories"]["Frontend Framework"] += 1
                    elif any(x in tech_lower for x in ['php', 'node', 'python', 'ruby', 'java', 'asp', 'net']):
                        results["tech_categories"]["Backend Language"] += 1
                    elif any(x in tech_lower for x in ['nginx', 'apache', 'tomcat', 'iis', 'caddy']):
                        results["tech_categories"]["Web Server"] += 1
                    elif any(x in tech_lower for x in ['mysql', 'postgres', 'mongo', 'redis', 'mariadb', 'oracle']):
                        results["tech_categories"]["Database"] += 1
                    elif any(x in tech_lower for x in ['bootstrap', 'tailwind', 'foundation', 'material']):
                        results["tech_categories"]["UI Framework"] += 1
                    elif any(x in tech_lower for x in ['wordpress', 'drupal', 'joomla', 'shopify']):
                        results["tech_categories"]["CMS"] += 1
                    elif any(x in tech_lower for x in ['aws', 'cloudflare', 'azure', 'gcp']):
                        results["tech_categories"]["Cloud/CDN"] += 1
                    else:
                        results["tech_categories"]["Other"] += 1
                    
                    # Extraer versiones
                    version_match = re.search(r'([\w.-]+)/([\d.]+)', tech_clean)
                    if version_match:
                        tech_name = version_match.group(1)
                        tech_version = version_match.group(2)
                        results["tech_versions"][tech_name] = tech_version
                        
    except FileNotFoundError:
        results["error"] = f"Archivo {filepath} no encontrado."
    return results

def parse_ffuf_json(filepath, param_mode=False):
    """Analiza archivo JSON de ffuf con estadísticas"""
    results = []
    stats = {
        'status_codes': Counter(),
        'total_found': 0,
        'interesting_findings': 0
    }
    
    try:
        if not os.path.exists(filepath):
            return results, stats
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
            for entry in data.get("results", []):
                fuZZ_value = entry.get("input", {}).get("FUZZ", "")
                status = entry.get("status", 0)
                url = entry.get("url", "")
                length = entry.get("length", 0)
                words = entry.get("words", 0)
                lines = entry.get("lines", 0)
                
                if not fuZZ_value or not status:
                    continue
                
                # Manejar status como int o str
                if isinstance(status, str) and status.isdigit():
                    status_int = int(status)
                elif isinstance(status, int):
                    status_int = status
                else:
                    status_int = 0
                
                if status_int == 0:
                    continue
                
                stats['status_codes'][status_int] += 1
                stats['total_found'] += 1
                
                is_interesting = status_int not in [200, 301, 302, 404]
                if is_interesting:
                    stats['interesting_findings'] += 1
                
                results.append({
                    "path": fuZZ_value,
                    "status": status_int,
                    "url": url,
                    "length": length,
                    "words": words,
                    "lines": lines,
                    "is_interesting": is_interesting,
                    "is_fp": status_int == 200
                })
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"[!] Error parseando {filepath}: {e}")
        return [], stats
    
    # Ordenar y limitar
    if results:
        results.sort(key=lambda x: (x.get('is_interesting', False), x.get('status', 999)))
        limit = 30 if param_mode else 50
        results = results[:limit]
    
    return results, stats

def parse_nuclei_advanced(filepath):
    """Análisis avanzado de Nuclei"""
    findings = []
    stats = {
        'severity': Counter(),
        'templates': Counter(),
        'categories': Counter(),
        'high_severity_count': 0,
        'total_findings': 0
    }
    
    try:
        if not os.path.exists(filepath):
            return findings, stats
        
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
                        tags = info.get("tags", [])
                        if isinstance(tags, str):
                            tags = tags.split(',')
                        
                        # Estadísticas
                        stats['severity'][severity] += 1
                        stats['templates'][template_name] += 1
                        stats['total_findings'] += 1
                        
                        if severity.lower() in ['critical', 'high']:
                            stats['high_severity_count'] += 1
                        
                        # Categorizar
                        for tag in tags[:3]:
                            if tag.lower() in ['cve', 'vulnerability', 'security']:
                                stats['categories']['Security'] += 1
                            elif tag.lower() in ['cloud', 'aws', 'azure', 'gcp']:
                                stats['categories']['Cloud'] += 1
                            elif tag.lower() in ['config', 'misconfiguration']:
                                stats['categories']['Misconfiguration'] += 1
                            elif tag.lower() in ['exposure', 'info-leak']:
                                stats['categories']['Information Exposure'] += 1
                        
                        findings.append({
                            "nombre": name,
                            "severidad": severity,
                            "descripcion": description[:300],
                            "url_afectada": matched,
                            "template": template_name,
                            "tags": tags[:5]
                        })
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    
    return findings, stats

def extract_all_paths_from_data(historical_urls, katana_urls, linkfinder_endpoints, 
                                alive_data, ffuf_dirs, custom_scan):
    """Extrae y combina todas las rutas de diferentes fuentes"""
    all_paths = []
    
    # Función auxiliar para limpiar y extraer path
    def extract_path(url):
        if not url:
            return None
        if url.startswith('http'):
            try:
                parsed = urlparse(url)
                return parsed.path
            except:
                return None
        return url
    
    # Extraer de cada fuente
    for source_name, source_data in [
        ('historical', historical_urls),
        ('katana', katana_urls),
        ('endpoints', linkfinder_endpoints),
        ('alive', [h for h in alive_data if h.startswith('http')]),
        ('ffuf', [e['path'] for e in ffuf_dirs if e.get('path')]),
        ('custom', [e.get('url', '') for e in custom_scan if e.get('url')])
    ]:
        for item in source_data[:2000]:  # Límite por fuente
            path = extract_path(item)
            if path and path not in ['/', '']:
                all_paths.append(path)
    
    return all_paths

def analyze_depth_by_source(all_sources):
    """Analiza la profundidad de cada fuente"""
    depth_stats = {}
    
    for source_name, paths in all_sources.items():
        depths = []
        for path in paths[:1000]:
            if path:
                clean_path = path
                if path.startswith('http'):
                    try:
                        clean_path = urlparse(path).path
                    except:
                        continue
                depth = len([p for p in clean_path.split('/') if p and p != '..'])
                depths.append(depth)
        
        if depths:
            depth_stats[source_name] = {
                'avg': statistics.mean(depths),
                'max': max(depths),
                'min': min(depths),
                'count': len(depths)
            }
    
    return depth_stats

def generate_advanced_report():
    """Genera un megareporte interactivo en HTML con análisis estadístico"""
    print("[+] Generando MEGAREPORTE con análisis avanzado...")

    # Obtener target_url
    global target_url
    base_url = sys.argv[1]

    if target_url == 'No especificado':
        if os.path.exists('logs/alive.txt'):
            try:
                with open('logs/alive.txt', 'r') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        target_url = first_line.split(' ')[0] if ' ' in first_line else first_line
            except:
                pass

    # Verificar que exista la carpeta logs
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("[!] Carpeta 'logs' creada. Asegúrate de tener los archivos de resultados.")

    # Parsear todos los archivos
    print("[+] Analizando nmap...")
    nmap_data = parse_nmap("logs/nmap.txt")
    
    print("[+] Analizando whatweb...")
    whatweb_data = parse_whatweb("logs/whatweb.txt")
    
    # URLs históricas
    historical_urls = []
    try:
        with open("logs/historical_urls.txt", 'r') as f:
            historical_urls = [line.strip() for line in f if line.strip()]
    except:
        pass
    
    # Hosts activos
    alive_data = []
    try:
        with open("logs/alive.txt", 'r') as f:
            for line in f:
                if line.strip():
                    alive_data.append(line.strip())
    except:
        pass
    
    # Katana
    katana_urls = []
    try:
        with open("logs/katana.txt", 'r') as f:
            katana_urls = [line.strip() for line in f if line.strip()]
    except:
        pass
    
    # JS files
    js_files = []
    try:
        with open("logs/js_files.txt", 'r') as f:
            js_files = [line.strip() for line in f if line.strip() and '.js' in line]
    except:
        pass
    
    # LinkFinder - Obtener todos los endpoints
    linkfinder_endpoints = []
    try:
        with open("logs/endpoints_from_js.txt", 'r') as f:
            content = f.read()
            linkfinder_endpoints = [line.strip() for line in content.split('\n') 
                                  if line.strip() and not line.startswith('[') 
                                  and line.strip() not in ['No se encontraron endpoints', 'Archivo no encontrado.']]
    except:
        pass
    
    # FFUF
    print("[+] Analizando ffuf...")
    ffuf_dirs, ffuf_stats = parse_ffuf_json("logs/ffuf_directories.json", param_mode=False)
    ffuf_params, ffuf_param_stats = parse_ffuf_json("logs/ffuf_parameters.json", param_mode=True)
    
    # Nuclei avanzado
    print("[+] Analizando nuclei...")
    nuclei_data, nuclei_stats = parse_nuclei_advanced("logs/nuclei_full.json")
    
    # Escaneo personalizado
    custom_scan = []
    try:
        with open("logs/scan_results_unique.txt", 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    parts = line.split(' | ')
                    if len(parts) >= 3:
                        custom_scan.append({
                            "url": parts[0],
                            "status": parts[1].replace('Status: ', ''),
                            "size": parts[2].replace('Tamaño: ', '').replace(' bytes', '')
                        })
    except:
        pass

    # Inicializar analizador estadístico
    analyzer = StatisticalAnalyzer()
    
    # Análisis estadístico de URLs
    all_urls = historical_urls + katana_urls + [host for host in alive_data if host.startswith('http')]
    url_stats = analyzer.analyze_urls(all_urls)
    
    # Análisis de endpoints
    endpoint_stats = analyzer.analyze_endpoints(linkfinder_endpoints)
    
    # Análisis de vulnerabilidades
    vuln_trends = analyzer.get_vulnerability_trends(nuclei_data)
    
    # Cálculo de riesgo
    risk_analysis = analyzer.calculate_risk_score(nuclei_data)
    
    # Construir árbol de rutas
    tree_builder = TreeBuilder()
    
    # Árbol de endpoints de JS
    endpoint_tree = tree_builder.build_path_tree(linkfinder_endpoints)
    endpoint_tree_html = tree_builder.tree_to_html(endpoint_tree)
    endpoint_tree_stats = tree_builder.get_tree_stats(endpoint_tree)
    
    # Árbol de directorios de ffuf
    dir_paths = [entry['path'] for entry in ffuf_dirs if entry.get('path')]
    dir_tree = tree_builder.build_path_tree(dir_paths)
    dir_tree_html = tree_builder.tree_to_html(dir_tree)
    dir_tree_stats = tree_builder.get_tree_stats(dir_tree)
    
    # Árbol de URLs históricas
    hist_tree = tree_builder.build_path_tree(historical_urls)
    hist_tree_html = tree_builder.tree_to_html(hist_tree)
    hist_tree_stats = tree_builder.get_tree_stats(hist_tree)
    
    # ============ NUEVO: ÁRBOL MAESTRO COMBINADO ============
    print("[+] Construyendo árbol maestro combinado...")
    
    # Preparar todas las fuentes
    all_sources = {
        'historical': historical_urls,
        'katana': katana_urls,
        'endpoints': linkfinder_endpoints,
        'alive': [host for host in alive_data if host.startswith('http')],
        'ffuf': [entry['path'] for entry in ffuf_dirs if entry.get('path')],
        'custom': [entry.get('url', '') for entry in custom_scan if entry.get('url')]
    }
    
    # Función optimizada para construir el árbol maestro
    def build_master_tree_optimized(sources, max_depth=50, max_paths=20000):
        """Construye un árbol maestro combinando múltiples fuentes - VERSIÓN OPTIMIZADA"""
        tree = {}
        processed = 0
        
        # Combinar todas las rutas de diferentes fuentes
        all_paths = []
        for source_name, paths in sources.items():
            if paths:
                # Limitar por fuente para rendimiento
                source_paths = paths[:5000]  # 5000 por fuente
                all_paths.extend(source_paths)
                print(f"    - {source_name}: {len(source_paths)} rutas")
        
        print(f"[+] Procesando {len(all_paths)} rutas totales...")
        
        # Construir árbol
        for path in all_paths[:max_paths]:
            if not path:
                continue
            
            processed += 1
            if processed % 1000 == 0:
                print(f"    Procesadas {processed} rutas...")
            
            # Extraer y limpiar path
            if path.startswith('http'):
                try:
                    parsed = urlparse(path)
                    clean_path = parsed.path
                except:
                    continue
            else:
                clean_path = path
            
            # Limpiar path
            clean_path = clean_path.strip()
            if clean_path.startswith('./'):
                clean_path = clean_path[2:]
            if clean_path.startswith('/'):
                clean_path = clean_path[1:]
            
            # Eliminar query strings y fragmentos
            if '?' in clean_path:
                clean_path = clean_path.split('?')[0]
            if '#' in clean_path:
                clean_path = clean_path.split('#')[0]
            
            # Filtrar partes vacías
            parts = [p for p in clean_path.split('/') if p and p != '..' and p != '.']
            
            if not parts:
                continue
                
            current = tree
            for part in parts[:max_depth]:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        print(f"[+] Árbol construido con {processed} rutas procesadas")
        return tree
    
    # Construir el árbol maestro
    master_tree = build_master_tree_optimized(all_sources)
    master_tree_stats = TreeBuilder.get_tree_stats(master_tree)
    master_tree_html = TreeBuilder.tree_to_html_with_path(master_tree)
    
    # Estadísticas del árbol maestro
    total_paths = sum(len(v) for v in all_sources.values())
    print(f"[+] Árbol maestro construido:")
    print(f"    - Total de rutas en fuentes: {total_paths:,}")
    print(f"    - Nodos en el árbol: {master_tree_stats.get('total_nodes', 0):,}")
    print(f"    - Profundidad máxima: {master_tree_stats.get('max_depth', 0)}")
    print(f"    - Directorios raíz: {master_tree_stats.get('total_dirs', 0)}")
    
    # Análisis de profundidad por fuente
    depth_by_source = analyze_depth_by_source(all_sources)
    
    # Estadísticas adicionales
    total_urls_found = len(set(all_urls))
    
    # Calcular dominios únicos de forma segura
    unique_domains = 0
    domains_set = set()
    for url in all_urls:
        if url and url.startswith('http'):
            try:
                parsed = urlparse(url)
                if parsed.netloc:
                    domains_set.add(parsed.netloc)
            except (ValueError, AttributeError):
                try:
                    domain = url.split('/')[2] if '://' in url else url.split('/')[0]
                    if domain:
                        domains_set.add(domain)
                except:
                    pass
    unique_domains = len(domains_set)
    
    print("[+] Generando HTML...")
    
    # --- Generar HTML ---
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CuackRecon MegaReport - Análisis Exhaustivo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #2d3748;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            padding: 40px;
        }
        h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3em;
            margin-bottom: 10px;
        }
        h2 {
            color: #4a5568;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            font-size: 1.8em;
        }
        h3 {
            color: #4a5568;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        h4 {
            color: #4a5568;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .header-info {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0 30px 0;
        }
        .stat-card {
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
            transition: transform 0.3s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card .number {
            font-size: 2.5em;
            font-weight: bold;
            display: block;
        }
        .stat-card .label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .stat-card.primary { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .stat-card.success { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
        .stat-card.warning { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .stat-card.danger { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-card.dark { background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); }
        .stat-card.purple { background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%); }
        .stat-card.orange { background: linear-gradient(135deg, #f6d365 0%, #fda085 100%); }
        
        .risk-meter {
            background: #edf2f7;
            border-radius: 20px;
            height: 30px;
            overflow: hidden;
            margin: 15px 0;
        }
        .risk-meter .fill {
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #ecc94b, #f56565);
            transition: width 1s ease;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            color: white;
            font-weight: bold;
            font-size: 0.8em;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }
        tr:hover {
            background: #f7fafc;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-critical { background: #fc8181; color: white; }
        .badge-high { background: #f6ad55; color: white; }
        .badge-medium { background: #fbd38d; color: #1a202c; }
        .badge-low { background: #68d391; color: white; }
        .badge-info { background: #63b3ed; color: white; }
        
        .tech-tag {
            display: inline-block;
            padding: 2px 10px;
            margin: 2px;
            border-radius: 12px;
            font-size: 0.8em;
            background: #ebf8ff;
            color: #2b6cb0;
            border: 1px solid #bee3f8;
        }
        
        .code-block {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
            margin: 10px 0;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .grid-3 {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .container { padding: 20px; }
            .grid-2, .grid-3 { grid-template-columns: 1fr; }
            h1 { font-size: 2em; }
            .stats-grid { grid-template-columns: 1fr 1fr; }
        }
        
        .section-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
        }
        
        .finding-highlight {
            background: #fff5f5;
            border-left: 4px solid #fc8181;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        
        .progress-bar {
            height: 8px;
            background: #edf2f7;
            border-radius: 4px;
            overflow: hidden;
            margin: 5px 0;
        }
        .progress-bar .fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s;
        }
        
        .summary-box {
            background: #f7fafc;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
        }
        
        .scrollable-container {
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 15px;
            background: #fafbfc;
        }
        
        .scrollable-container::-webkit-scrollbar {
            width: 8px;
        }
        .scrollable-container::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        .scrollable-container::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 10px;
        }
        .scrollable-container::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        
        .timestamp {
            color: #718096;
            font-size: 0.9em;
        }
        
        .footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            color: #718096;
        }
        
        .tree-container {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            padding: 10px;
            background: #1a202c;
            color: #e2e8f0;
            border-radius: 8px;
            overflow-x: auto;
        }
        
        .tree-container .dir {
            color: #63b3ed;
        }
        .tree-container .file {
            color: #68d391;
        }
        
        .tree-stats {
            display: flex;
            gap: 20px;
            margin: 10px 0;
            flex-wrap: wrap;
        }
        .tree-stats .stat-item {
            background: #edf2f7;
            padding: 8px 15px;
            border-radius: 8px;
            font-size: 0.9em;
        }
        .tree-stats .stat-item strong {
            color: #4a5568;
        }
        
        .endpoint-category {
            display: inline-block;
            padding: 2px 8px;
            margin: 2px;
            border-radius: 10px;
            font-size: 0.75em;
            font-weight: 600;
        }
        .endpoint-category.api { background: #bee3f8; color: #2b6cb0; }
        .endpoint-category.admin { background: #fc8181; color: #742a2a; }
        .endpoint-category.auth { background: #fbd38d; color: #744210; }
        .endpoint-category.config { background: #d69e2e; color: #744210; }
        .endpoint-category.data { background: #68d391; color: #22543d; }
        .endpoint-category.file { background: #9ae6b4; color: #22543d; }
        .endpoint-category.user { background: #b794f4; color: #44337a; }
        .endpoint-category.system { background: #fc8181; color: #742a2a; }
        .endpoint-category.other { background: #e2e8f0; color: #4a5568; }
    </style>
</head>
<body>
<div class="container">
""")
        
        # Título y cabecera
        f.write(f"""
    <div class="header-info">
        <h1>🔍 CuackRecon MegaReport</h1>
        <p style="font-size: 1.2em; opacity: 0.95;">Análisis Exhaustivo de Reconocimiento con Visualización Jerárquica</p>
        <p><strong>Objetivo:</strong> {target_url}</p>
        <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Versión:</strong> 3.0 (MegaReport con Árbol Maestro)</p>
    </div>
""")
        
        # 1. DASHBOARD - Resumen Ejecutivo
        f.write("""
    <h2>📊 Dashboard Ejecutivo</h2>
    <div class="stats-grid">
""")
        
        # Obtener risk_score de forma segura
        if isinstance(risk_analysis, dict):
            risk_score = risk_analysis.get('total_score', 0)
        else:
            risk_score = risk_analysis if isinstance(risk_analysis, int) else 0
        
        f.write(f"""
        <div class="stat-card primary">
            <span class="number">{total_urls_found:,}</span>
            <span class="label">URLs Encontradas</span>
        </div>
        <div class="stat-card purple">
            <span class="number">{unique_domains}</span>
            <span class="label">Dominios Únicos</span>
        </div>
        <div class="stat-card warning">
            <span class="number">{safe_len(nmap_data['open_ports'])}</span>
            <span class="label">Puertos Abiertos</span>
        </div>
        <div class="stat-card danger">
            <span class="number">{nuclei_stats['high_severity_count']}</span>
            <span class="label">Vulnerabilidades Críticas/Altas</span>
        </div>
        <div class="stat-card dark">
            <span class="number">{len(whatweb_data['technologies'])}</span>
            <span class="label">Tecnologías Detectadas</span>
        </div>
        <div class="stat-card orange">
            <span class="number">{len(linkfinder_endpoints):,}</span>
            <span class="label">Endpoints en JS</span>
        </div>
        <div class="stat-card success">
            <span class="number">{safe_len(custom_scan)}</span>
            <span class="label">Hallazgos Personalizados</span>
        </div>
        <div class="stat-card primary">
            <span class="number">{master_tree_stats.get('total_nodes', 0):,}</span>
            <span class="label">Nodos en Árbol Maestro</span>
        </div>
""")
        
        f.write("""
    </div>
""")
        
        # Risk Meter
        risk_percentage = min((risk_score / 100) * 100, 100) if risk_score > 0 else 0
        
        if isinstance(risk_analysis, dict):
            weighted_avg = risk_analysis.get('weighted_average', 0)
        else:
            weighted_avg = 0
        
        f.write(f"""
    <div class="section-card">
        <h3>🎯 Puntuación de Riesgo General</h3>
        <div class="risk-meter">
            <div class="fill" style="width: {risk_percentage:.1f}%;">
                {risk_percentage:.1f}%
            </div>
        </div>
        <p style="font-size: 0.9em; color: #718096;">
            Puntuación: {risk_score} puntos | 
            Promedio ponderado: {weighted_avg:.2f} | 
            Basado en {nuclei_stats['total_findings']} hallazgos de Nuclei
        </p>
    </div>
""")
        
        # ============ ÁRBOL MAESTRO ============
        f.write("""
    <h2>🌳 Árbol Maestro de Directorios (Combinado)</h2>
    <div class="section-card">
        <div class="summary-box">
            <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                <div><strong>📊 Total de rutas analizadas:</strong> """ + str(total_paths) + """</div>
                <div><strong>🌿 Nodos en el árbol:</strong> """ + str(master_tree_stats.get('total_nodes', 0)) + """</div>
                <div><strong>📏 Profundidad máxima:</strong> """ + str(master_tree_stats.get('max_depth', 0)) + """</div>
                <div><strong>📂 Directorios raíz:</strong> """ + str(master_tree_stats.get('total_dirs', 0)) + """</div>
            </div>
        </div>
        
        <h4>📊 Desglose de Fuentes</h4>
        <div class="grid-3">
""")
        
        # Mostrar estadísticas por fuente
        fuentes_stats = {
            'URLs Históricas': len(historical_urls),
            'Crawling (Katana)': len(katana_urls),
            'Endpoints JS': len(linkfinder_endpoints),
            'Hosts Activos': len(alive_data),
            'Directorios FFUF': len(ffuf_dirs),
            'Escaneo Custom': len(custom_scan)
        }
        
        for nombre, count in fuentes_stats.items():
            if count > 0:
                pct = (count / total_paths) * 100 if total_paths > 0 else 0
                f.write(f"""
                <div class="summary-box" style="text-align: center;">
                    <div style="font-size: 1.5em; font-weight: bold;">{count:,}</div>
                    <div style="color: #718096;">{nombre}</div>
                    <div class="progress-bar">
                        <div class="fill" style="width: {pct}%; background: #667eea;"></div>
                    </div>
                </div>
        """)
        
        f.write("""
        </div>
""")
        
        # Profundidad por fuente
        if depth_by_source:
            f.write("""
        <h4>📏 Profundidad por Fuente</h4>
        <div class="grid-3">
""")
            for source, stats in depth_by_source.items():
                source_display = {
                    'historical': 'URLs Históricas',
                    'katana': 'Crawling (Katana)',
                    'endpoints': 'Endpoints JS',
                    'alive': 'Hosts Activos',
                    'ffuf': 'Directorios FFUF',
                    'custom': 'Escaneo Custom'
                }.get(source, source)
                
                f.write(f"""
            <div class="summary-box">
                <div><strong>{source_display}</strong></div>
                <div>📊 Rutas: {stats['count']}</div>
                <div>📈 Profundidad media: {stats['avg']:.1f}</div>
                <div>📈 Profundidad máxima: {stats['max']}</div>
                <div>📉 Profundidad mínima: {stats['min']}</div>
            </div>
            """)
            f.write("""
        </div>
""")
        
        f.write("""
        <h4>🌳 Estructura Completa del Sitio</h4>
        <div class="tree-stats">
            <div class="stat-item"><strong>📁 Directorios:</strong> """ + str(master_tree_stats.get('total_dirs', 0)) + """</div>
            <div class="stat-item"><strong>📄 Archivos/Endpoints:</strong> """ + str(master_tree_stats.get('total_nodes', 0) - master_tree_stats.get('total_dirs', 0)) + """</div>
            <div class="stat-item"><strong>🔽 Profundidad máxima:</strong> """ + str(master_tree_stats.get('max_depth', 0)) + """</div>
            <div class="stat-item"><strong>📊 Ratio archivos/directorios:</strong> """ + 
            f"{(master_tree_stats.get('total_nodes', 0) - master_tree_stats.get('total_dirs', 0)) / max(master_tree_stats.get('total_dirs', 1), 1):.2f}" + """</div>
        </div>
        <div class="scrollable-container" style="max-height: 700px; background: #1a202c; border-radius: 10px;">
            <div class="tree-container">
""" + master_tree_html + """
            </div>
        </div>
    </div>
""")
        
        # 2. ESTADÍSTICAS AVANZADAS
        f.write("""
    <h2>📈 Análisis Estadístico Avanzado</h2>
    <div class="grid-2">
        <div class="section-card">
            <h3>📐 URLs Analizadas</h3>
""")
        
        if url_stats:
            f.write(f"""
            <div class="summary-box">
                <p><strong>Total de URLs:</strong> {url_stats.get('total_urls', 0):,}</p>
                <p><strong>URLs Únicas:</strong> {url_stats.get('unique_urls', 0):,}</p>
                <p><strong>Profundidad Media:</strong> {url_stats.get('avg_depth', 0):.2f}</p>
                <p><strong>Profundidad Máxima:</strong> {url_stats.get('max_depth', 0)}</p>
                <p><strong>Profundidad Mínima:</strong> {url_stats.get('min_depth', 0)}</p>
                <p><strong>Mediana de Profundidad:</strong> {url_stats.get('median_depth', 0)}</p>
                <p><strong>Desviación Estándar:</strong> {url_stats.get('std_depth', 0):.2f}</p>
            </div>
""")
        
        # Extensiones más comunes
        if url_stats and url_stats.get('extensions'):
            f.write("""
            <h4>📁 Extensiones de Archivo Más Comunes</h4>
            <div style="margin: 10px 0;">
""")
            for ext, count in list(url_stats.get('extensions', {}).items())[:10]:
                pct = (count / max(url_stats.get('total_urls', 1), 1)) * 100
                f.write(f"""
                <div>
                    <span style="font-weight: 600;">.{ext}</span>
                    <span style="float: right;">{count}</span>
                    <div class="progress-bar">
                        <div class="fill" style="width: {min(pct * 2, 100)}%; background: #667eea;"></div>
                    </div>
                </div>
""")
            f.write("</div>")
        
        f.write("""
        </div>
        <div class="section-card">
            <h3>🛡️ Análisis de Vulnerabilidades</h3>
""")
        
        # Distribución de severidad
        if vuln_trends.get('by_severity'):
            f.write("""
            <h4>Distribución por Severidad</h4>
            <div style="margin: 10px 0;">
""")
            severity_colors = {'critical': '#fc8181', 'high': '#f6ad55', 'medium': '#fbd38d', 'low': '#68d391', 'info': '#63b3ed'}
            total_sev = sum(vuln_trends['by_severity'].values())
            for severity, count in sorted(vuln_trends['by_severity'].items(), 
                                        key=lambda x: ['critical', 'high', 'medium', 'low', 'info'].index(x[0]) if x[0] in ['critical', 'high', 'medium', 'low', 'info'] else 5):
                pct = (count / total_sev) * 100 if total_sev > 0 else 0
                color = severity_colors.get(severity, '#a0aec0')
                f.write(f"""
                <div>
                    <span class="badge badge-{severity}">{severity}</span>
                    <span style="float: right;">{count}</span>
                    <div class="progress-bar">
                        <div class="fill" style="width: {pct}%; background: {color};"></div>
                    </div>
                </div>
""")
            f.write("</div>")
        
        # Categorías de vulnerabilidades
        if vuln_trends.get('by_category'):
            f.write("""
            <h4>Categorías de Vulnerabilidades</h4>
            <div style="margin: 10px 0;">
""")
            for category, count in vuln_trends['by_category'].most_common(10):
                f.write(f"""
                <div>
                    <span>{category}</span>
                    <span style="float: right;">{count}</span>
                    <div class="progress-bar">
                        <div class="fill" style="width: {min((count / max(vuln_trends['by_category'].values())) * 100, 100)}%; background: #764ba2;"></div>
                    </div>
                </div>
""")
            f.write("</div>")
        
        f.write("""
        </div>
    </div>
""")
        
        # 3. TECNOLOGÍAS
        f.write("""
    <h2>🏷️ Análisis de Tecnologías</h2>
    <div class="grid-2">
        <div class="section-card">
            <h3>Tecnologías Detectadas</h3>
            <div style="margin: 10px 0;">
""")
        
        if whatweb_data.get('technologies'):
            for tech in whatweb_data['technologies'][:20]:
                f.write(f'<span class="tech-tag">{tech}</span> ')
            if len(whatweb_data['technologies']) > 20:
                f.write(f'<span class="tech-tag">+{len(whatweb_data["technologies"]) - 20} más</span>')
        
        f.write("""
            </div>
            <div style="margin-top: 15px;">
                <p><strong>Servidor:</strong> """ + whatweb_data.get('server', 'No detectado') + """</p>
                <p><strong>Título:</strong> """ + whatweb_data.get('title', 'No encontrado') + """</p>
                <p><strong>País:</strong> """ + whatweb_data.get('country', 'No detectado') + """</p>
            </div>
        </div>
        <div class="section-card">
            <h3>Categorías de Tecnologías</h3>
""")
        
        if whatweb_data.get('tech_categories'):
            for category, count in whatweb_data['tech_categories'].most_common(10):
                pct = (count / max(whatweb_data['tech_categories'].values())) * 100 if whatweb_data['tech_categories'] else 0
                f.write(f"""
                <div>
                    <span>{category}</span>
                    <span style="float: right;">{count}</span>
                    <div class="progress-bar">
                        <div class="fill" style="width: {pct}%; background: #43e97b;"></div>
                    </div>
                </div>
""")
        else:
            f.write("<p>No se detectaron categorías.</p>")
        
        f.write("""
        </div>
    </div>
""")
        
        # 4. PUERTOS Y SERVICIOS
        if nmap_data.get('open_ports'):
            f.write("""
    <h2>🔌 Análisis de Puertos</h2>
    <div class="grid-2">
        <div class="section-card">
            <h3>Puertos Abiertos</h3>
            <div class="scrollable-container">
                <ul style="list-style: none; padding: 0; margin: 0;">
""")
            for port in nmap_data['open_ports']:
                f.write(f'<li style="padding: 5px 0; border-bottom: 1px solid #e2e8f0;">🔓 {port}</li>')
            f.write("""
                </ul>
            </div>
        </div>
        <div class="section-card">
            <h3>Estadísticas de Puertos</h3>
""")
            if nmap_data.get('port_stats'):
                stats = nmap_data['port_stats']
                f.write(f"""
                <p><strong>Total de Puertos:</strong> {stats.get('total', 0)}</p>
                <p><strong>Puerto Mínimo:</strong> {stats.get('min', 'N/A')}</p>
                <p><strong>Puerto Máximo:</strong> {stats.get('max', 'N/A')}</p>
                <p><strong>Promedio:</strong> {stats.get('avg', 0):.1f}</p>
                <p><strong>Puertos Comunes:</strong> {', '.join(map(str, stats.get('common_ports', [])))}</p>
""")
            if nmap_data.get('scan_time'):
                f.write(f"<p><strong>Tiempo de Escaneo:</strong> {nmap_data['scan_time']:.2f} segundos</p>")
            f.write("""
            <p><strong>Sistema Operativo:</strong> """ + nmap_data.get('os_info', 'No detectado') + """</p>
        </div>
    </div>
""")
        
        # 5. FFUF - Análisis de Directorios y Parámetros
        f.write("""
    <h2>🔍 Análisis de Fuerza Bruta (FFUF)</h2>
    <div class="grid-2">
        <div class="section-card">
            <h3>📁 Directorios/Archivos</h3>
""")
        
        if ffuf_stats.get('total_found', 0) > 0:
            f.write(f"""
            <div class="summary-box">
                <p><strong>Total de directorios/archivos encontrados:</strong> {ffuf_stats['total_found']}</p>
                <p><strong>Hallazgos interesantes:</strong> {ffuf_stats.get('interesting_findings', 0)}</p>
            </div>
""")
            if ffuf_stats.get('status_codes'):
                f.write("<h4>Códigos de Estado</h4>")
                for status, count in ffuf_stats['status_codes'].most_common(10):
                    pct = (count / ffuf_stats['total_found']) * 100 if ffuf_stats['total_found'] > 0 else 0
                    color = '#fc8181' if status >= 400 else '#68d391' if status < 300 else '#fbd38d'
                    f.write(f"""
                    <div>
                        <span>{status}</span>
                        <span style="float: right;">{count}</span>
                        <div class="progress-bar">
                            <div class="fill" style="width: {pct}%; background: {color};"></div>
                        </div>
                    </div>
""")
            
            f.write("""
            <h4>Hallazgos Relevantes</h4>
            <div class="scrollable-container">
                <table>
                    <thead>
                        <tr>
                            <th>Ruta</th>
                            <th>Estado</th>
                            <th>Tamaño</th>
                        </tr>
                    </thead>
                    <tbody>
""")
            for entry in ffuf_dirs[:50]:
                if entry.get('is_interesting', False):
                    f.write(f"""
                        <tr>
                            <td><span style="font-weight: 600;">{entry['path']}</span></td>
                            <td><span class="badge badge-high">{entry['status']}</span></td>
                            <td>{entry.get('length', 'N/A')}</td>
                        </tr>
""")
            f.write("""
                    </tbody>
                </table>
            </div>
""")
        else:
            f.write("<p>No se encontraron directorios o archivos.</p>")
        
        f.write("""
        </div>
        <div class="section-card">
            <h3>🔑 Parámetros</h3>
""")
        
        if ffuf_param_stats.get('total_found', 0) > 0:
            f.write(f"""
            <div class="summary-box">
                <p><strong>Total de parámetros encontrados:</strong> {ffuf_param_stats['total_found']}</p>
                <p><strong>Parámetros interesantes:</strong> {ffuf_param_stats.get('interesting_findings', 0)}</p>
            </div>
""")
            if ffuf_params:
                f.write("""
            <div class="scrollable-container">
                <table>
                    <thead>
                        <tr>
                            <th>Parámetro</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
""")
                for entry in ffuf_params[:30]:
                    if entry.get('is_interesting', False):
                        f.write(f"""
                        <tr>
                            <td><span style="font-weight: 600;">{entry['path']}</span></td>
                            <td><span class="badge badge-high">{entry['status']}</span></td>
                        </tr>
""")
                f.write("""
                    </tbody>
                </table>
            </div>
""")
        else:
            f.write("<p>No se encontraron parámetros.</p>")
        
        f.write("""
        </div>
    </div>
""")
        
        # 6. ÁRBOL DE ENDPOINTS DE JAVASCRIPT
        if linkfinder_endpoints:
            f.write("""
    <h2>🔎 Visualización Jerárquica de Endpoints en JavaScript</h2>
    <div class="section-card">
        <div class="summary-box">
            <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                <div><strong>Total de endpoints:</strong> """ + str(len(linkfinder_endpoints)) + """</div>
                <div><strong>Nodos en el árbol:</strong> """ + str(endpoint_tree_stats.get('total_nodes', 0)) + """</div>
                <div><strong>Profundidad máxima:</strong> """ + str(endpoint_tree_stats.get('max_depth', 0)) + """</div>
                <div><strong>Directorios raíz:</strong> """ + str(endpoint_tree_stats.get('total_dirs', 0)) + """</div>
            </div>
        </div>
        
        <h4>📊 Análisis de Endpoints</h4>
        <div class="grid-3">
""")
            
            # Categorías de endpoints
            if endpoint_stats.get('categories'):
                f.write("""
            <div>
                <h5>Categorías</h5>
""")
                for category, count in sorted(endpoint_stats['categories'].items(), key=lambda x: x[1], reverse=True)[:8]:
                    if count > 0:
                        pct = (count / endpoint_stats['total']) * 100 if endpoint_stats['total'] > 0 else 0
                        color_class = category if category in ['api', 'admin', 'auth', 'config', 'data', 'file', 'user', 'system'] else 'other'
                        f.write(f"""
                    <div>
                        <span class="endpoint-category {color_class}">{category}</span>
                        <span style="float: right;">{count} ({pct:.1f}%)</span>
                        <div class="progress-bar">
                            <div class="fill" style="width: {pct}%; background: #667eea;"></div>
                        </div>
                    </div>
""")
                f.write("""
            </div>
""")
            
            # Métodos HTTP detectados
            if endpoint_stats.get('methods'):
                f.write("""
            <div>
                <h5>Métodos HTTP Detectados</h5>
""")
                for method, count in endpoint_stats['methods'].items():
                    pct = (count / endpoint_stats['total']) * 100 if endpoint_stats['total'] > 0 else 0
                    f.write(f"""
                    <div>
                        <span style="font-weight: 600;">{method}</span>
                        <span style="float: right;">{count}</span>
                        <div class="progress-bar">
                            <div class="fill" style="width: {pct}%; background: #43e97b;"></div>
                        </div>
                    </div>
""")
                f.write("""
            </div>
""")
            
            f.write("""
            <div>
                <h5>Estadísticas</h5>
                <div class="summary-box">
                    <p><strong>Patrones únicos:</strong> """ + str(endpoint_stats.get('unique_patterns', 0)) + """</p>
                    <p><strong>Ratio de categorización:</strong> """ + 
                    f"{((sum(v for k,v in endpoint_stats.get('categories', {}).items() if k != 'other') / endpoint_stats['total']) * 100 if endpoint_stats['total'] > 0 else 0):.1f}%" + """</p>
                </div>
            </div>
        </div>
        
        <h4>🌳 Árbol de Endpoints</h4>
        <div class="tree-stats">
            <div class="stat-item"><strong>📁 Directorios:</strong> """ + str(endpoint_tree_stats.get('total_dirs', 0)) + """</div>
            <div class="stat-item"><strong>📄 Archivos/Endpoints:</strong> """ + str(endpoint_tree_stats.get('total_nodes', 0) - endpoint_tree_stats.get('total_dirs', 0)) + """</div>
            <div class="stat-item"><strong>🔽 Profundidad máxima:</strong> """ + str(endpoint_tree_stats.get('max_depth', 0)) + """</div>
        </div>
        <div class="scrollable-container" style="max-height: 600px; background: #1a202c; border-radius: 10px;">
            <div class="tree-container">
""" + endpoint_tree_html + """
            </div>
        </div>
    </div>
""")
        
        # 7. ÁRBOL DE DIRECTORIOS (FFUF)
        if dir_paths:
            f.write("""
    <h2>📂 Árbol de Directorios y Archivos (FFUF)</h2>
    <div class="section-card">
        <div class="summary-box">
            <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                <div><strong>Total de rutas:</strong> """ + str(len(dir_paths)) + """</div>
                <div><strong>Nodos en el árbol:</strong> """ + str(dir_tree_stats.get('total_nodes', 0)) + """</div>
                <div><strong>Profundidad máxima:</strong> """ + str(dir_tree_stats.get('max_depth', 0)) + """</div>
            </div>
        </div>
        <div class="scrollable-container" style="max-height: 500px; background: #1a202c; border-radius: 10px;">
            <div class="tree-container">
""" + dir_tree_html + """
            </div>
        </div>
    </div>
""")
        
        # 8. ÁRBOL DE URLs HISTÓRICAS
        if historical_urls:
            f.write("""
    <h2>📜 Árbol de URLs Históricas</h2>
    <div class="section-card">
        <div class="summary-box">
            <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                <div><strong>Total de URLs:</strong> """ + str(len(historical_urls)) + """</div>
                <div><strong>Nodos en el árbol:</strong> """ + str(hist_tree_stats.get('total_nodes', 0)) + """</div>
                <div><strong>Profundidad máxima:</strong> """ + str(hist_tree_stats.get('max_depth', 0)) + """</div>
            </div>
        </div>
        <div class="scrollable-container" style="max-height: 500px; background: #1a202c; border-radius: 10px;">
            <div class="tree-container">
""" + hist_tree_html + """
            </div>
        </div>
    </div>
""")
        
        # 9. VULNERABILIDADES - Análisis detallado
        if nuclei_data:
            f.write("""
    <h2>⚠️ Hallazgos de Nuclei - Análisis Detallado</h2>
    <div class="section-card">
""")
            
            # Hallazgos críticos/altos
            critical_high = [h for h in nuclei_data if h.get('severidad', '').lower() in ['critical', 'high']]
            if critical_high:
                f.write(f"""
                <div class="finding-highlight">
                    <h3 style="margin: 0; color: #e53e3e;">🚨 Hallazgos Críticos/Altos ({len(critical_high)})</h3>
                </div>
                <div class="scrollable-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Hallazgo</th>
                                <th>Severidad</th>
                                <th>URL Afectada</th>
                            </tr>
                        </thead>
                        <tbody>
""")
                for finding in critical_high[:30]:
                    f.write(f"""
                            <tr>
                                <td><strong>{finding.get('nombre', 'N/A')}</strong></td>
                                <td><span class="badge badge-{finding.get('severidad', 'info')}">{finding.get('severidad', 'info')}</span></td>
                                <td style="font-size: 0.9em; color: #718096;">{finding.get('url_afectada', 'N/A')}</td>
                            </tr>
""")
                if len(critical_high) > 30:
                    f.write(f"""
                            <tr>
                                <td colspan="3" style="color: #718096; text-align: center;">... y {len(critical_high) - 30} hallazgos críticos/altos más</td>
                            </tr>
""")
                f.write("""
                        </tbody>
                    </table>
                </div>
""")
            
            # Resumen de vulnerabilidades
            f.write("""
            <div style="margin-top: 20px;">
                <h3>Resumen de Hallazgos</h3>
                <div class="summary-box">
""")
            
            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                count = vuln_trends['by_severity'].get(severity, 0)
                if count > 0:
                    emoji = "🔴" if severity == "critical" else "🟠" if severity == "high" else "🟡" if severity == "medium" else "🔵" if severity == "low" else "⚪"
                    f.write(f"<p>{emoji} <strong>{severity.capitalize()}:</strong> {count}</p>")
            
            f.write(f"""
                    <p><strong>Total de hallazgos únicos:</strong> {len(nuclei_data)}</p>
                </div>
            </div>
""")
            f.write("</div>")
        
        # 10. ANÁLISIS DE ARCHIVOS JS
        if js_files:
            f.write("""
    <h2>📦 Archivos JavaScript Encontrados</h2>
    <div class="section-card">
        <div class="summary-box">
            <p><strong>Total de archivos JS:</strong> """ + str(len(js_files)) + """</p>
        </div>
        <div class="scrollable-container">
            <ul style="list-style: none; padding: 0; margin: 0;">
""")
            for js in js_files:
                f.write(f'<li style="padding: 5px 0; border-bottom: 1px solid #e2e8f0;">📄 {js}</li>')
            f.write("""
            </ul>
        </div>
    </div>
""")
        
        # 11. CRAWLING - Análisis de URLs
        if katana_urls:
            f.write("""
    <h2>🕷️ Análisis de Crawling</h2>
    <div class="grid-2">
        <div class="section-card">
            <h3>Estadísticas de Crawling</h3>
            <div class="summary-box">
                <p><strong>URLs Encontradas:</strong> """ + str(len(katana_urls)) + """</p>
                <p><strong>URLs Únicas:</strong> """ + str(len(set(katana_urls))) + """</p>
            </div>
        </div>
        <div class="section-card">
            <h3>URLs Principales</h3>
            <div class="scrollable-container">
                <ul style="list-style: none; padding: 0; margin: 0;">
""")
            for url in katana_urls[:50]:
                f.write(f'<li style="padding: 3px 0; font-size: 0.9em;">🌐 {url}</li>')
            if len(katana_urls) > 50:
                f.write(f'<li style="color: #718096;">... y {len(katana_urls) - 50} más</li>')
            f.write("""
                </ul>
            </div>
        </div>
    </div>
""")
        
        # 12. HOSTS ACTIVOS
        if alive_data:
            f.write("""
    <h2>🌐 Hosts Activos Encontrados</h2>
    <div class="section-card">
        <div class="summary-box">
            <p><strong>Total de hosts activos:</strong> """ + str(len(alive_data)) + """</p>
        </div>
        <div class="scrollable-container">
            <ul style="list-style: none; padding: 0; margin: 0;">
""")
            for host in alive_data:
                f.write(f'<li style="padding: 5px 0; border-bottom: 1px solid #e2e8f0;">✅ {host}</li>')
            f.write("""
            </ul>
        </div>
    </div>
""")
        
        # 13. ESCANEO PERSONALIZADO
        if custom_scan:
            f.write("""
    <h2>🎯 Escaneo Personalizado</h2>
    <div class="section-card">
        <div class="summary-box">
            <p><strong>Resultados únicos encontrados:</strong> """ + str(len(custom_scan)) + """</p>
        </div>
        <div class="scrollable-container">
            <table>
                <thead>
                    <tr>
                        <th>URL</th>
                        <th>Estado</th>
                        <th>Tamaño</th>
                    </tr>
                </thead>
                <tbody>
""")
            for entry in custom_scan[:50]:
                status_int = int(entry.get('status', 0)) if entry.get('status', '0').isdigit() else 0
                status_color = '#fc8181' if status_int >= 400 else '#68d391' if status_int < 300 else '#fbd38d'
                f.write(f"""
                    <tr>
                        <td><span style="font-weight: 600;">{entry['url']}</span></td>
                        <td><span style="padding: 2px 10px; border-radius: 12px; background: {status_color}; color: white;">{entry['status']}</span></td>
                        <td>{entry['size']} bytes</td>
                    </tr>
""")
            f.write("""
                </tbody>
            </table>
        </div>
    </div>
""")
        
        # 14. RECOMENDACIONES Y CONCLUSIONES
        f.write("""
    <h2>💡 Recomendaciones Estratégicas</h2>
    <div class="grid-2">
        <div class="section-card" style="border-left: 4px solid #fc8181;">
            <h3 style="color: #e53e3e;">🔴 Prioridad Alta</h3>
            <ul style="padding-left: 20px;">
                <li style="margin: 10px 0;"><strong>Vulnerabilidades Críticas:</strong> Revisar inmediatamente los """ + str(nuclei_stats['high_severity_count']) + """ hallazgos de severidad crítica/alta</li>
                <li style="margin: 10px 0;"><strong>Endpoints Críticos:</strong> Analizar endpoints de administración, API y autenticación encontrados en JavaScript (""" + str(endpoint_stats.get('categories', {}).get('admin', 0)) + """ administrativos, """ + str(endpoint_stats.get('categories', {}).get('api', 0)) + """ API)</li>
                <li style="margin: 10px 0;"><strong>Exposiciones:</strong> Verificar exposiciones de información sensible en las URLs históricas y endpoints</li>
            </ul>
        </div>
        <div class="section-card" style="border-left: 4px solid #fbd38d;">
            <h3 style="color: #d69e2e;">🟡 Prioridad Media</h3>
            <ul style="padding-left: 20px;">
                <li style="margin: 10px 0;"><strong>Fuerza Bruta:</strong> Investigar los """ + str(ffuf_stats.get('interesting_findings', 0)) + """ directorios y parámetros con códigos de estado no 200</li>
                <li style="margin: 10px 0;"><strong>Tecnologías:</strong> Revisar las """ + str(len(whatweb_data.get('technologies', []))) + """ tecnologías detectadas por vulnerabilidades conocidas</li>
                <li style="margin: 10px 0;"><strong>Archivos JS:</strong> Analizar en detalle los """ + str(len(js_files)) + """ archivos JavaScript (vistos en el árbol de endpoints)</li>
            </ul>
        </div>
    </div>
    <div class="section-card" style="border-left: 4px solid #68d391;">
        <h3 style="color: #38a169;">🟢 Prioridad Baja</h3>
        <ul style="padding-left: 20px;">
            <li style="margin: 10px 0;"><strong>Documentación:</strong> Documentar todos los hallazgos para futuras pruebas y referencias</li>
            <li style="margin: 10px 0;"><strong>Monitoreo:</strong> Repetir escaneos periódicamente para detectar nuevos cambios</li>
            <li style="margin: 10px 0;"><strong>Pruebas Manuales:</strong> Realizar pruebas manuales con herramientas como Burp Suite para validar hallazgos</li>
        </ul>
    </div>
""")
        
        # Pie de página
        f.write("""
    <div class="footer">
        <p><strong>CuackRecon MegaReport v3.0 - Análisis con Visualización Jerárquica</strong></p>
        <p>Generado automáticamente el """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        <p style="font-size: 0.8em; margin-top: 10px;">
            <span style="display: inline-block; margin: 0 10px;">📊 Análisis Estadístico Avanzado</span>
            <span style="display: inline-block; margin: 0 10px;">🌳 Visualización en Árbol Maestro</span>
            <span style="display: inline-block; margin: 0 10px;">🔬 Data-Driven Security Assessment</span>
        </p>
    </div>
</div>
</body>
</html>
""")
    
    print(f"[+] MegaReport generado: {REPORT_FILE}")
    if os.path.exists(REPORT_FILE):
        print(f"[+] Tamaño del reporte: {os.path.getsize(REPORT_FILE) / 1024:.2f} KB")
    print("[+] ¡Análisis completado exitosamente!")

if __name__ == "__main__":
    generate_advanced_report()
