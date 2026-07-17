#!/usr/bin/env python3
import asyncio
import aiohttp
from collections import Counter
import sys
import os
import argparse
import json
import datetime
from urllib.parse import urlparse
import time
import signal

class AsyncScanner:
    def __init__(self, base_url, wordlist_file, timeout=5, rate_limit=0, 
                 headers=None, cookies=None, max_concurrent=50, verbose=False):
        self.base_url = base_url
        self.wordlist_file = wordlist_file
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.max_concurrent = max_concurrent
        self.verbose = verbose
        self.results = []
        self.errors = []
        self.semaphore = None
        self.total_paths = 0
        self.processed = 0
        self.stats = {
            'total': 0,
            'success': 0,
            'errors': 0,
            'timeouts': 0,
            'status_codes': Counter(),
            'sizes': []
        }
        self.errores_mostrados = set()
        self.last_request_time = 0  # Para controlar rate limit
        self.rate_limit_lock = asyncio.Lock()  # Para sincronizar rate limit
        
    async def _rate_limit_wait(self):
        """Espera respetando el rate limit de manera sincronizada"""
        if self.rate_limit <= 0:
            return
        
        async with self.rate_limit_lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.rate_limit:
                await asyncio.sleep(self.rate_limit - time_since_last)
            self.last_request_time = time.time()
        
    async def fetch_url(self, session, path):
        """Realiza una petición asíncrona a una URL"""
        url = f"{self.base_url}{path}" if self.base_url.endswith('/') else f"{self.base_url}/{path}"
        
        # Control de rate limit ANTES de hacer la petición
        await self._rate_limit_wait()
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                content = await response.read()
                size = len(content)
                
                result = {
                    'url': url,
                    'status': response.status,
                    'size': size,
                    'success': response.status < 400
                }
                
                self.results.append(result)
                self.stats['total'] += 1
                self.stats['status_codes'][response.status] += 1
                self.stats['sizes'].append(size)
                
                if response.status < 400:
                    self.stats['success'] += 1
                    if self.verbose:
                        print(f"✅ [{self.processed}/{self.total_paths}] {url} -> {response.status} ({size} bytes)")
                    else:
                        print(f"✅ {url} -> {response.status} ({size} bytes)")
                else:
                    if response.status not in self.errores_mostrados:
                        if self.verbose:
                            print(f"❌ {url} -> {response.status}")
                        else:
                            print(f"❌ {url} -> {response.status}")
                        self.errores_mostrados.add(response.status)
                
                self.processed += 1
                return result
                
        except asyncio.TimeoutError:
            self.stats['timeouts'] += 1
            self.stats['total'] += 1
            self.processed += 1
            print(f"⏰ Timeout: {url}")
            return {'url': url, 'error': 'timeout', 'success': False}
        except aiohttp.ClientConnectorError:
            self.stats['errors'] += 1
            self.stats['total'] += 1
            self.processed += 1
            if "connection_error" not in self.errores_mostrados:
                print(f"🔌 Conexión fallida: {url}")
                self.errores_mostrados.add("connection_error")
            return {'url': url, 'error': 'connection_error', 'success': False}
        except aiohttp.ClientResponseError as e:
            self.stats['errors'] += 1
            self.stats['total'] += 1
            self.processed += 1
            if e.status not in self.errores_mostrados:
                print(f"❌ {url} -> {e.status}")
                self.errores_mostrados.add(e.status)
            return {'url': url, 'error': str(e), 'success': False}
        except Exception as e:
            self.stats['errors'] += 1
            self.stats['total'] += 1
            self.processed += 1
            if "RequestException" not in self.errores_mostrados:
                print(f"⚠️  Error en {url}: {str(e)}")
                self.errores_mostrados.add("RequestException")
            return {'url': url, 'error': str(e), 'success': False}
    
    async def scan(self):
        """Ejecuta el escaneo de manera asíncrona"""
        # Leer wordlist
        try:
            with open(self.wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                paths = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ Wordlist no encontrada: {self.wordlist_file}")
            return []
        
        self.total_paths = len(paths)
        self.processed = 0
        
        # Configurar semáforo para controlar concurrencia
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Configurar headers
        headers = {}
        for key, value in self.headers.items():
            headers[str(key)] = str(value)
        
        headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'es-ES,es;q=0.9'
        })
        
        # Configurar cookies
        cookies = {}
        for key, value in self.cookies.items():
            cookies[str(key)] = str(value)
        
        connector = aiohttp.TCPConnector(limit=self.max_concurrent * 2)
        
        print(f"\n🔍 Escaneando: {self.base_url}")
        print(f"📋 Wordlist: {self.wordlist_file}")
        print(f"⏱️  Timeout: {self.timeout}s")
        if self.rate_limit > 0:
            print(f"⏳ Rate Limit: {self.rate_limit}s entre peticiones")
        else:
            print(f"⏳ Rate Limit: Sin límite")
        print(f"🔢 Conexiones concurrentes: {self.max_concurrent}")
        print(f"📡 Headers: {len(headers)} configurados")
        if cookies:
            print(f"🍪 Cookies: {len(cookies)} configuradas")
        print("-" * 50)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(headers=headers, cookies=cookies, 
                                        connector=connector) as session:
            
            # Crear y ejecutar tareas con control de concurrencia
            async def bounded_fetch(path):
                async with self.semaphore:
                    return await self.fetch_url(session, path)
            
            # Crear todas las tareas pero con límite de concurrencia
            tasks = [asyncio.create_task(bounded_fetch(path)) for path in paths]
            
            # Usar asyncio.gather con limitación
            results = []
            for i in range(0, len(tasks), self.max_concurrent):
                batch = tasks[i:i + self.max_concurrent]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)
                
                # Actualizar progreso
                percentage = ((i + len(batch)) / self.total_paths) * 100
                sys.stdout.write(f"\r📊 Progreso: {min(i + len(batch), self.total_paths)}/{self.total_paths} peticiones completadas ({percentage:.1f}%)")
                sys.stdout.flush()
            
            elapsed_time = time.time() - start_time
            print(f"\n⏱️  Tiempo total: {elapsed_time:.2f} segundos")
            if elapsed_time > 0:
                print(f"📊 Velocidad: {self.total_paths/elapsed_time:.1f} peticiones/segundo")
            
            return results
    
    def get_statistics(self):
        """Obtiene estadísticas del escaneo"""
        successful = [r for r in self.results if r.get('success', False)]
        
        # Análisis de tamaños
        sizes = [r.get('size', 0) for r in successful]
        size_counter = Counter(sizes)
        
        most_common_size = None
        if sizes:
            most_common_size = size_counter.most_common(1)[0][0]
        
        unique_results = [r for r in successful if r.get('size', 0) != most_common_size] if most_common_size else successful
        
        return {
            'total_requests': self.stats['total'],
            'successful': len(successful),
            'errors': self.stats['errors'],
            'timeouts': self.stats['timeouts'],
            'status_codes': dict(self.stats['status_codes']),
            'size_analysis': {
                'most_common': most_common_size,
                'unique_results': len(unique_results),
                'total_sizes': len(size_counter),
                'size_distribution': dict(size_counter)
            },
            'unique_results': unique_results,
            'all_results': successful
        }

def normalize_url(url):
    """Normaliza la URL agregando http:// si no tiene protocolo"""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url

def validate_url(url):
    """Valida que la URL sea correcta"""
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except:
        return False

def save_results_json(resultados, base_url, wordlist_file, output_file, stats):
    """Guarda los resultados en un archivo JSON"""
    timestamp = datetime.datetime.now().isoformat()
    
    # Preparar resultados detallados
    results_list = []
    for res in resultados:
        if res.get('success', False):
            results_list.append({
                "url": res['url'],
                "status_code": res['status'],
                "size_bytes": res['size'],
                "size_kb": round(res['size'] / 1024, 2)
            })
    
    # Preparar datos para JSON
    data = {
        "metadata": {
            "timestamp": timestamp,
            "target_url": base_url,
            "wordlist": wordlist_file,
            "total_results": len(results_list),
            "unique_results": stats['size_analysis']['unique_results'],
            "most_common_size": stats['size_analysis']['most_common'],
            "status_codes": stats['status_codes']
        },
        "results": results_list,
        "unique_results": [
            {
                "url": r['url'],
                "status_code": r['status'],
                "size_bytes": r['size'],
                "size_kb": round(r['size'] / 1024, 2)
            } for r in stats['unique_results']
        ],
        "summary": {
            "total_requests": stats['total_requests'],
            "successful": stats['successful'],
            "errors": stats['errors'],
            "timeouts": stats['timeouts'],
            "status_code_distribution": stats['status_codes'],
            "size_analysis": stats['size_analysis']
        }
    }
    
    # Guardar JSON
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en: {output_file}")
        return True
    except Exception as e:
        print(f"\n❌ Error al guardar JSON: {e}")
        return False

def save_unique_txt(unique_results, base_url, output_file):
    """Guarda los resultados únicos en un archivo TXT"""
    try:
        txt_file = output_file.replace('.json', '_unique.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"# Resultados únicos - {base_url}\n")
            f.write(f"# Escaneado: {datetime.datetime.now().isoformat()}\n")
            f.write(f"# Total únicos: {len(unique_results)}\n\n")
            
            for res in unique_results:
                f.write(f"{res['url']} | Status: {res['status_code']} | Tamaño: {res['size_bytes']} bytes ({res['size_kb']} KB)\n")
        
        print(f"📝 Resultados únicos guardados en: {txt_file}")
        return True
    except Exception as e:
        print(f"⚠️  No se pudo guardar archivo TXT: {e}")
        return False

async def main_async():
    parser = argparse.ArgumentParser(description='Escáner de directorios/archivos web (versión paralelizada)')
    parser.add_argument('url', nargs='?', help='URL objetivo (ej: https://ejemplo.com o ejemplo.com)')
    parser.add_argument('-w', '--wordlist', default='weblist.txt', help='Archivo de wordlist (default: weblist.txt)')
    parser.add_argument('-t', '--timeout', type=int, default=5, help='Timeout en segundos (default: 5)')
    parser.add_argument('-H', '--header', action='append', help='Headers adicionales (ej: "X-Custom: value")')
    parser.add_argument('-c', '--cookie', action='append', help='Cookies adicionales (ej: "nombre=valor")')
    parser.add_argument('-u', '--user-agent', default='Mozilla/5.0', help='User-Agent personalizado')
    parser.add_argument('-a', '--auth', help='Token de autorización (Bearer)')
    parser.add_argument('-o', '--output', default='scan_results.json', help='Archivo de salida JSON (default: scan_results.json)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mostrar resultados detallados en consola')
    parser.add_argument('--no-save', action='store_true', help='No guardar resultados en JSON')
    parser.add_argument('-r', '--rate-limit', type=float, default=0, 
                       help='Tiempo de espera entre peticiones en segundos (ej: 0.5 para medio segundo)')
    parser.add_argument('-m', '--max-concurrent', type=int, default=50, 
                       help='Máximo de conexiones concurrentes (default: 50)')
    
    args = parser.parse_args()
    
    # Configurar URL base
    if args.url:
        base_url = normalize_url(args.url)
        if not validate_url(base_url):
            print(f"Error: URL inválida '{args.url}'")
            sys.exit(1)
    else:
        base_url = "https://juiceshop.cuackerman.uk/"
        print(f"⚠️  No se proporcionó URL, usando ejemplo: {base_url}")
        print("💡 Para especificar una URL: python cuacktest_async.py https://ejemplo.com")
    
    # Verificar wordlist
    wordlist_file = args.wordlist
    if not os.path.exists(wordlist_file):
        print(f"Error: Archivo de wordlist '{wordlist_file}' no encontrado")
        print("Creando wordlist de ejemplo...")
        with open(wordlist_file, 'w') as f:
            f.write("admin\nlogin\napi\ntest\ndev\nbackup\nconfig\nassets\ncss\njs\nimages\n")
        print(f"✅ Creado '{wordlist_file}' con entradas de ejemplo")
    
    # Configurar headers
    headers = {}
    
    if args.user_agent:
        headers["User-Agent"] = args.user_agent
    
    if args.auth:
        headers["Authorization"] = f"Bearer {args.auth}"
    
    if args.header:
        for h in args.header:
            try:
                key, value = h.split(':', 1)
                headers[key.strip()] = value.strip()
            except ValueError:
                print(f"⚠️  Header inválido: {h} (formato: 'Clave: Valor')")
    
    # Configurar cookies
    cookies = {}
    if args.cookie:
        for c in args.cookie:
            try:
                key, value = c.split('=', 1)
                cookies[key.strip()] = value.strip()
            except ValueError:
                print(f"⚠️  Cookie inválida: {c} (formato: 'nombre=valor')")
    
    # Crear scanner
    scanner = AsyncScanner(
        base_url=base_url,
        wordlist_file=wordlist_file,
        timeout=args.timeout,
        rate_limit=args.rate_limit,
        headers=headers,
        cookies=cookies,
        max_concurrent=args.max_concurrent,
        verbose=args.verbose
    )
    
    # Ejecutar escaneo
    try:
        await scanner.scan()
    except KeyboardInterrupt:
        print("\n\n🛑 Escaneo interrumpido por el usuario")
        # Mostrar resultados parciales
        if scanner.results:
            print(f"\n📊 Resultados parciales: {len(scanner.results)} peticiones completadas")
        sys.exit(0)
    
    print("\n" + "=" * 50)
    
    # Obtener estadísticas
    stats = scanner.get_statistics()
    
    # Mostrar resumen
    if stats['successful'] > 0:
        print(f"\n📊 Resumen:")
        print(f"  ✅ Respuestas exitosas: {stats['successful']}")
        print(f"  ❌ Errores: {stats['errors']}")
        print(f"  ⏰ Timeouts: {stats['timeouts']}")
        print(f"  📊 Códigos de estado: {stats['status_codes']}")
        
        # Análisis de tamaños
        if stats['size_analysis']['most_common'] is not None:
            print(f"\n📏 Análisis de tamaños:")
            print(f"  Tamaño mayoritario: {stats['size_analysis']['most_common']} bytes")
            print(f"  Resultados únicos: {stats['size_analysis']['unique_results']}")
            
            # Mostrar resultados únicos
            if stats['unique_results']:
                print(f"\n🔍 Resultados potencialmente interesantes ({len(stats['unique_results'])}):")
                for res in stats['unique_results'][:10]:  # Mostrar primeros 10
                    print(f"  ➜ {res['url']} | Status: {res['status']} | Tamaño: {res['size']} bytes")
                if len(stats['unique_results']) > 10:
                    print(f"  ... y {len(stats['unique_results']) - 10} más")
            else:
                print(f"\n⚠️  Todos los resultados tienen el mismo tamaño")
                print("  Esto podría indicar que todas las páginas devuelven la misma respuesta")
    else:
        print("\n⚠️  No se encontraron respuestas exitosas")
    
    # Guardar resultados
    if not args.no_save and stats['successful'] > 0:
        # Guardar JSON
        output_file = args.output
        save_results_json(scanner.results, base_url, wordlist_file, output_file, stats)
        
        # Guardar TXT con resultados únicos
        if stats['unique_results']:
            # Convertir unique_results al formato esperado por save_unique_txt
            unique_for_txt = [
                {
                    'url': r['url'],
                    'status_code': r['status'],
                    'size_bytes': r['size'],
                    'size_kb': round(r['size'] / 1024, 2)
                } for r in stats['unique_results']
            ]
            save_unique_txt(unique_for_txt, base_url, output_file)
    elif not args.no_save:
        print("\n⚠️  No se guardaron resultados (no hay respuestas exitosas)")
    else:
        print("\n⚠️  Resultados NO guardados (opción --no-save activada)")

def main():
    """Función principal que ejecuta el loop asyncio"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n🛑 Escaneo interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
