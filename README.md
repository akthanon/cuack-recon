# 🦆 CuackRecon

**CuackRecon** es un conjunto de herramientas de reconocimiento web para Bug Bounty, diseñado para automatizar y optimizar el proceso de enumeración y descubrimiento de activos.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Herramientas Incluidas](#-herramientas-incluidas)
- [Estructura de Directorios](#-estructura-de-directorios)
- [Checkpoints y Reanudación](#-checkpoints-y-reanudación)
- [Ejemplos de Configuración](#-ejemplos-de-configuración)
- [Contribuciones](#-contribuciones)
- [Licencia](#-licencia)
- [Advertencias](#-advertencias)

## ✨ Características

- **Reconocimiento completo** automatizado con múltiples herramientas
- **Sistema de checkpoints** para reanudar escaneos interrumpidos
- **Rate limiting** configurable para evitar bloqueos
- **Modo automático e interactivo** para control total
- **Soporte de autenticación** (cookies, Bearer tokens, headers personalizados)
- **Reportes detallados** en HTML y Markdown
- **Visualización jerárquica** de directorios y endpoints
- **Análisis estadístico** de resultados
- **Detección de bloqueos** y reintentos automáticos
- **Scope management** para limitar el escaneo a dominios específicos

## 📁 Estructura del Proyecto

```
cuackrecon/
├── cuack-recon.sh          # Script principal de reconocimiento
├── cuack-install.sh        # Instalador de herramientas y dependencias
├── cuacktest.py            # Escáner de directorios/archivos paralelizado
├── cuackreport.py          # Generador de reportes Markdown
├── full_cuackreport.py     # Generador de reportes HTML con análisis avanzado
├── config.yaml             # Archivo de configuración de ejemplo
├── weblist.txt             # Wordlist por defecto para fuzzing
├── checkpoints/            # Directorio de puntos de control
├── logs/                   # Logs y resultados de herramientas
├── reports/                # Reportes generados
└── tools/                  # Herramientas instaladas
```

## 🔧 Requisitos Previos

- **Sistema operativo:** Linux (Kali Linux recomendado)
- **Bash** 4.0+
- **Python 3.8+**
- **Go** 1.18+
- **Herramientas base:** git, curl, wget, jq, nmap, whatweb

## 📦 Instalación

### Instalación Automática (Recomendada)

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/cuackrecon.git
cd cuackrecon

# Dar permisos de ejecución
chmod +x cuack-install.sh cuack-recon.sh

# Ejecutar el instalador
./cuack-install.sh
```

El instalador:
1. Instala todas las dependencias del sistema
2. Crea un entorno virtual de Python
3. Instala las herramientas Go necesarias
4. Descarga wordlists y templates
5. Configura la estructura de directorios

### Instalación Manual

```bash
# Instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl wget nmap whatweb jq unzip

# Instalar herramientas Go
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/ffuf/ffuf/v2@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
go install -v github.com/tomnomnom/waybackurls@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/tomnomnom/assetfinder@latest

# Crear directorios
mkdir -p logs reports checkpoints
```

## ⚙️ Configuración

### Archivo de Configuración (config.yaml)

```yaml
# URL objetivo
target_url: "https://ejemplo.com"

# Wordlists
wordlist_self: "weblist.txt"
wordlist_ffuf: "weblist.txt"
paramater_names: "weblist.txt"

# Autenticación
cookies: "session=xyz123; token=abc456"
bearer_token: "Bearer eyJhbGciOiJIUzI1NiIs..."
extra_headers: "X-Forwarded-For: 127.0.0.1"
user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Rate Limiting
rate_limit: 50  # peticiones por minuto
ffuf_threads: 30

# Scope
scope:
  - "ejemplo.com"
  - "*.ejemplo.com"
exclude:
  - "admin.ejemplo.com"
  - "test.ejemplo.com"

# Pasos a ejecutar
steps:
  - basic
  - subdomains
  - historical
  - active
  - crawling
  - js_recon
  - enumeration
  - vulnerabilities
  - report

# Katana configuration
katana_depth: 3

# FFUF configuration
ffuf_threads: 100
```

### Variables de Entorno

```bash
export TARGET_URL="https://ejemplo.com"
export COOKIES="session=xyz123"
export BEARER_TOKEN="Bearer token123"
```

## 🚀 Uso

### Ejecutar un Escaneo Completo

```bash
# Usando archivo de configuración
./cuack-recon.sh -c config.yaml

# Usando URL directa
./cuack-recon.sh -u https://ejemplo.com -y

# Con autenticación
./cuack-recon.sh -u https://ejemplo.com --cookies "session=xyz123" --bearer "Bearer token123"
```

### Opciones Disponibles

| Opción | Descripción |
|--------|-------------|
| `-c, --config FILE` | Archivo de configuración (YAML) |
| `-u, --url URL` | URL objetivo |
| `--cookies COOKIES` | Cookies en formato `nombre1=valor1; nombre2=valor2` |
| `--bearer TOKEN` | Bearer token de autenticación |
| `--headers HEADERS` | Headers adicionales |
| `--wordlist FILE` | Wordlist para ffuf (default: weblist.txt) |
| `--params FILE` | Wordlist para parámetros (default: weblist.txt) |
| `--user-agent UA` | User-Agent personalizado |
| `--rate-limit NUM` | Peticiones por minuto (default: 50) |
| `--max-retries NUM` | Número de reintentos (default: 3) |
| `-v, --verbose` | Modo verbose |
| `-y, --yes` | Auto-aprobar autorización |
| `--resume` | Reanudar desde el último checkpoint |
| `-h, --help` | Mostrar ayuda |

### Reanudar un Escaneo

```bash
# Reanudar desde el último checkpoint
./cuack-recon.sh --resume
```

### Ejecutar Herramientas Individuales

```bash
# Escaneo con cuacktest.py
python3 cuacktest.py https://ejemplo.com -w weblist.txt -r 0.5

# Generar reporte
python3 cuackreport.py

# Generar reporte avanzado
python3 full_cuackreport.py
```

## 🛠️ Herramientas Incluidas

### Escaneo Pasivo
- **Subfinder**: Enumeración de subdominios
- **Assetfinder**: Enumeración adicional de subdominios
- **Gau**: Recopilación de URLs históricas
- **Waybackurls**: URLs del archivo Wayback Machine
- **WhatWeb**: Fingerprinting de tecnologías

### Escaneo Activo
- **Nmap**: Escaneo de puertos y servicios
- **HTTPX**: Verificación de hosts activos
- **Katana**: Crawling web avanzado
- **FFUF**: Fuzzing de directorios y parámetros
- **Nuclei**: Escaneo de vulnerabilidades

### Análisis de JavaScript
- **LinkFinder**: Extracción de endpoints de archivos JS
- **Katana JS**: Extracción de archivos JavaScript

### Custom
- **cuacktest.py**: Escáner paralelizado de directorios/archivos
- **cuackreport.py**: Generador de reportes Markdown
- **full_cuackreport.py**: Generador de reportes HTML avanzados

## 📂 Estructura de Directorios

```
cuackrecon/
├── logs/                          # Logs de todas las herramientas
│   ├── nmap.txt                   # Resultados de Nmap
│   ├── whatweb.txt                # Resultados de WhatWeb
│   ├── subdomains.txt             # Subdominios encontrados
│   ├── historical_urls.txt        # URLs históricas
│   ├── alive.txt                  # Hosts activos
│   ├── katana.txt                 # URLs del crawling
│   ├── js_files.txt               # Archivos JavaScript
│   ├── endpoints_from_js.txt      # Endpoints extraídos
│   ├── ffuf_directories.json      # Resultados de FFUF directorios
│   ├── ffuf_parameters.json       # Resultados de FFUF parámetros
│   ├── nuclei_*.json              # Resultados de Nuclei
│   └── scan_results*.json         # Resultados de cuacktest
├── reports/                       # Reportes generados
│   ├── cuackrecon_report.md       # Reporte Markdown
│   ├── cuackrecon_megareport.html # Reporte HTML avanzado
│   └── cuackrecon_full_report.md  # Reporte completo
└── checkpoints/                   # Puntos de control
    ├── last_step.txt              # Último paso completado
    ├── completed_steps.txt        # Pasos completados
    └── config.env                 # Configuración guardada
```

## 💾 Checkpoints y Reanudación

El sistema de checkpoints permite:
- Guardar el progreso después de cada paso
- Reanudar escaneos interrumpidos (Ctrl+C)
- Evitar re-ejecutar pasos ya completados
- Preservar resultados parciales

### Uso de Checkpoints

```bash
# Iniciar un escaneo (se guardarán checkpoints automáticamente)
./cuack-recon.sh -c config.yaml

# Si se interrumpe (Ctrl+C), se guarda el estado
# Para reanudar:
./cuack-recon.sh --resume
```

## 📝 Ejemplos de Configuración

### Configuración Básica

```yaml
target_url: "https://ejemplo.com"
rate_limit: 30
steps:
  - basic
  - report
```

### Configuración Completa con Autenticación

```yaml
target_url: "https://api.ejemplo.com"
cookies: "session=xyz123; token=abc456"
bearer_token: "Bearer eyJhbGciOiJIUzI1NiIs..."
rate_limit: 20
scope:
  - "api.ejemplo.com"
  - "*.ejemplo.com"
steps:
  - subdomains
  - historical
  - active
  - crawling
  - enumeration
  - vulnerabilities
  - report
```

### Configuración para Escaneo Rápido

```yaml
target_url: "https://ejemplo.com"
rate_limit: 100
ffuf_threads: 50
steps:
  - basic
  - active
  - report
```

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz un fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de tus cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## ⚠️ Advertencias

- **Autorización:** Asegúrate de tener permiso explícito para escanear el objetivo.
- **Rate Limiting:** Respeta los límites del programa de Bug Bounty.
- **Uso Ético:** Utiliza estas herramientas solo en sistemas que tengas autorización para probar.
- **Responsabilidad:** El autor no se hace responsable del uso indebido de estas herramientas.

---

**🦆 CuackRecon - Reconocimiento web automatizado para Bug Bounty**
