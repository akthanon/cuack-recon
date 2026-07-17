#!/bin/bash
# -*- coding: utf-8 -*-
# ==============================================
# CuackRecon - Instalador de Herramientas
# Versión: 3.4 - Kali Linux PEP 668 Compatible (Fix)
# ==============================================

set -e  # Detener en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Variables
INSTALL_DIR="/opt/cuackrecon"
TOOLS_DIR="$INSTALL_DIR/tools"
LOGS_DIR="$INSTALL_DIR/logs"
CONFIG_DIR="$INSTALL_DIR/config"
REPORT_DIR="$INSTALL_DIR/reports"
VENV_DIR="$INSTALL_DIR/venv"

# ==============================================
# FUNCIONES DE UTILIDAD
# ==============================================

print_header() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║          🦆 C U A C K R E C O N   I N S T A L L E R       ║"
    echo "║                                                            ║"
    echo "║          Versión 3.4 - Kali Linux PEP 668 Compatible       ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}▶ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_info() {
    echo -e "${MAGENTA}ℹ ${1}${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ==============================================
# FUNCIONES DE INSTALACIÓN
# ==============================================

install_dependencies() {
    print_step "Instalando dependencias del sistema..."
    
    # Detectar sistema operativo
    if [[ -f /etc/debian_version ]]; then
        print_info "Sistema Debian/Ubuntu/Kali detectado"
        sudo apt-get update -qq
        
        # Para Kali Linux
        if grep -q "Kali" /etc/os-release 2>/dev/null; then
            print_info "Kali Linux detectado - instalando paquetes específicos"
            sudo apt-get install -y \
                python3 python3-pip python3-venv python3-full \
                git curl wget \
                build-essential libssl-dev zlib1g-dev \
                libffi-dev libbz2-dev libreadline-dev \
                libsqlite3-dev libncurses-dev \
                libnss3-dev liblzma-dev libexpat1-dev \
                jq nmap whatweb \
                chromium \
                unzip \
                npm \
                nodejs
        else
            sudo apt-get install -y \
                python3 python3-pip python3-venv \
                git curl wget \
                build-essential libssl-dev zlib1g-dev \
                libffi-dev libbz2-dev libreadline-dev \
                libsqlite3-dev libncurses-dev \
                libnss3-dev liblzma-dev libexpat1-dev \
                jq nmap whatweb \
                chromium \
                unzip \
                npm \
                nodejs
        fi
        
    elif [[ -f /etc/redhat-release ]]; then
        print_info "Sistema RHEL/CentOS/Fedora detectado"
        sudo yum install -y \
            python3 python3-pip python3-virtualenv \
            git curl wget \
            gcc make openssl-devel \
            zlib-devel bzip2-devel readline-devel \
            sqlite-devel ncurses-devel gdbm-devel \
            libnss3-devel liblzma-devel expat-devel \
            jq nmap whatweb \
            chromium \
            unzip \
            npm \
            nodejs
    elif [[ -f /etc/arch-release ]]; then
        print_info "Sistema Arch Linux detectado"
        sudo pacman -S --noconfirm \
            python python-pip python-virtualenv \
            git curl wget \
            gcc make openssl \
            zlib bzip2 readline sqlite \
            ncurses gdbm nss lzma expat \
            jq nmap whatweb \
            chromium \
            unzip \
            npm \
            nodejs
    else
        print_warning "Sistema operativo no reconocido. Instalando paquetes comunes..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y python3 python3-pip git curl wget jq nmap whatweb unzip chromium npm nodejs
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-pip git curl wget jq nmap whatweb unzip chromium npm nodejs
        fi
    fi
    
    print_success "Dependencias del sistema instaladas"
}

create_virtualenv() {
    print_step "Creando entorno virtual de Python..."
    
    # Eliminar entorno virtual existente si hay problemas
    if [[ -d "$VENV_DIR" ]]; then
        print_info "Eliminando entorno virtual existente..."
        rm -rf "$VENV_DIR"
    fi
    
    # Crear el entorno virtual con python3
    print_info "Creando entorno virtual en $VENV_DIR..."
    
    # Usar python3 -m venv directamente
    python3 -m venv "$VENV_DIR" 2>&1
    
    # Verificar que se creó correctamente
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        print_success "Entorno virtual creado exitosamente"
    else
        print_error "Error creando entorno virtual. Intentando con virtualenv..."
        
        # Intentar con virtualenv si está instalado
        if check_command virtualenv; then
            virtualenv "$VENV_DIR"
            if [[ -f "$VENV_DIR/bin/activate" ]]; then
                print_success "Entorno virtual creado con virtualenv"
            else
                print_error "No se pudo crear el entorno virtual"
                exit 1
            fi
        else
            print_error "No se pudo crear el entorno virtual. Instalando virtualenv..."
            pip3 install --user virtualenv
            ~/.local/bin/virtualenv "$VENV_DIR"
            
            if [[ -f "$VENV_DIR/bin/activate" ]]; then
                print_success "Entorno virtual creado con virtualenv"
            else
                print_error "No se pudo crear el entorno virtual"
                exit 1
            fi
        fi
    fi
    
    # Crear archivo de activación simplificado
    cat > "$INSTALL_DIR/activate.sh" << 'EOF'
#!/bin/bash
# Activar el entorno virtual de CuackRecon
if [[ -f "/opt/cuackrecon/venv/bin/activate" ]]; then
    source /opt/cuackrecon/venv/bin/activate
    echo "✅ Entorno virtual de CuackRecon activado"
    echo "📦 Python: $(which python3)"
    echo "📦 Pip: $(which pip)"
else
    echo "❌ No se encontró el entorno virtual"
    echo "Ejecuta: python3 -m venv /opt/cuackrecon/venv"
fi
EOF
    chmod +x "$INSTALL_DIR/activate.sh"
    
    print_success "Entorno virtual configurado"
}

install_python_packages() {
    print_step "Instalando paquetes de Python..."
    
    # Verificar que existe el entorno virtual
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        print_error "El entorno virtual no existe. Creándolo..."
        create_virtualenv
    fi
    
    # Activar entorno virtual
    print_info "Activando entorno virtual..."
    source "$VENV_DIR/bin/activate"
    
    # Verificar que está activado
    if [[ -z "$VIRTUAL_ENV" ]]; then
        print_error "No se pudo activar el entorno virtual"
        exit 1
    fi
    
    print_success "Entorno virtual activado: $VIRTUAL_ENV"
    
    # Actualizar pip en el entorno virtual
    print_info "Actualizando pip..."
    pip install --upgrade pip setuptools wheel
    
    # Instalar paquetes principales
    print_info "Instalando paquetes de Python (esto puede tomar un momento)..."
    
    PACKAGES=(
        jsbeautifier
	requests
        beautifulsoup4
        lxml
        json5
        pyyaml
        jinja2
        markdown
        colorama
        tqdm
        pandas
        numpy
        matplotlib
        seaborn
        wordcloud
        plotly
        flask
        dash
        selenium
        playwright
        httpx
        aiohttp
        python-dotenv
        click
        typer
        rich
        tabulate
        terminaltables
        jupyter
        notebook
        nbconvert
        openpyxl
        xlsxwriter
        sqlalchemy
        dnspython
        whois
        shodan
        censys
        python-nmap
        pyopenssl
        cryptography
        waybackpy
        arjun
        websocket-client
        urllib3
        certifi
        charset-normalizer
        idna
    )
    
    for package in "${PACKAGES[@]}"; do
        print_info "Instalando $package..."
        pip install --no-cache-dir "$package" 2>/dev/null || print_warning "Error instalando $package"
    done
    
    # Instalar playwright browsers
    print_info "Instalando navegadores de playwright..."
    playwright install 2>/dev/null || true
    
    # Desactivar entorno virtual
    deactivate
    
    print_success "Paquetes de Python instalados en $VENV_DIR"
    print_info "Para activar el entorno virtual: source $INSTALL_DIR/activate.sh"
}

install_go_tools() {
    print_step "Instalando herramientas en Go..."
    
    # Verificar Go
    if ! check_command go; then
        print_warning "Go no está instalado. Instalando..."
        wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
        sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
        rm go1.21.5.linux-amd64.tar.gz
        export PATH=$PATH:/usr/local/go/bin
        echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
        print_success "Go instalado"
    fi
    
    # Configurar GOPATH
    export GOPATH=~/go
    export PATH=$PATH:$GOPATH/bin
    
    # Crear directorio para herramientas Go
    mkdir -p "$TOOLS_DIR/go"
    cd "$TOOLS_DIR/go"
    
    # Instalar herramientas
    tools=(
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
        "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
        "github.com/projectdiscovery/katana/cmd/katana@latest"
        "github.com/ffuf/ffuf/v2@latest"
        "github.com/tomnomnom/waybackurls@latest"
        "github.com/tomnomnom/unfurl@latest"
        "github.com/projectdiscovery/httpx/cmd/httpx@latest"
        "github.com/hahwul/dalfox/v2@latest"
        "github.com/gitleaks/gitleaks/v8@latest"
        "github.com/lc/gau/v2/cmd/gau@latest"
        "github.com/projectdiscovery/notify/cmd/notify@latest"
	"github.com/tomnomnom/assetfinder@latest"
    )
    
    for tool in "${tools[@]}"; do
        tool_name=$(echo "$tool" | awk -F'/' '{print $NF}' | sed 's/@.*//')
        print_info "Instalando $tool_name..."
        go install -v $tool 2>/dev/null || print_warning "Error instalando $tool_name"
    done
    
    # Copiar binarios a /usr/local/bin
    if [[ -d "$HOME/go/bin" ]]; then
        sudo cp $HOME/go/bin/* /usr/local/bin/ 2>/dev/null || true
        print_success "Binarios copiados a /usr/local/bin"
    fi
    
    print_success "Herramientas Go instaladas"
}

install_security_tools() {
    print_step "Instalando herramientas de seguridad adicionales..."
    
    mkdir -p "$TOOLS_DIR/security"
    cd "$TOOLS_DIR/security"
    
    # LinkFinder
    print_info "Instalando LinkFinder..."
    if [[ ! -d "LinkFinder" ]]; then
        git clone https://github.com/GerbenJavado/LinkFinder.git 2>/dev/null || true
        if [[ -d "LinkFinder" ]]; then
            cd LinkFinder
            # Usar el entorno virtual para instalar dependencias
            source "$VENV_DIR/bin/activate"
            pip install -r requirements.txt 2>/dev/null || true
            deactivate
            cd ..
        fi
    fi
    
    # Crear alias para LinkFinder usando el entorno virtual
    if [[ -f "LinkFinder/linkfinder.py" ]]; then
        sudo tee /usr/local/bin/linkfinder > /dev/null << 'EOF'
#!/bin/bash
source /opt/cuackrecon/venv/bin/activate
python3 /opt/cuackrecon/tools/security/LinkFinder/linkfinder.py "$@"
EOF
        sudo chmod +x /usr/local/bin/linkfinder
        print_success "LinkFinder instalado"
    fi
    
    # SQLMap
    print_info "Instalando SQLMap..."
    if [[ ! -d "sqlmap" ]]; then
        git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git 2>/dev/null || true
    fi
    
    if [[ -f "sqlmap/sqlmap.py" ]]; then
        sudo tee /usr/local/bin/sqlmap > /dev/null << 'EOF'
#!/bin/bash
python3 /opt/cuackrecon/tools/security/sqlmap/sqlmap.py "$@"
EOF
        sudo chmod +x /usr/local/bin/sqlmap
        print_success "SQLMap instalado"
    fi
    
    # Feroxbuster
    print_info "Instalando Feroxbuster..."
    if ! check_command feroxbuster; then
        curl -sL https://raw.githubusercontent.com/epi052/feroxbuster/main/install-nix.sh | bash 2>/dev/null || true
        print_success "Feroxbuster instalado"
    fi
    
    print_success "Herramientas de seguridad instaladas"
}

install_wordlists() {
    print_step "Instalando wordlists para fuzzing..."
    
    mkdir -p "$TOOLS_DIR/wordlists"
    cd "$TOOLS_DIR/wordlists"
    
    # SecLists
    print_info "Descargando SecLists (esto puede tomar un momento)..."
    if [[ ! -d "SecLists" ]]; then
        git clone --depth 1 https://github.com/danielmiessler/SecLists.git 2>/dev/null || true
    fi
    
    # Wordlists adicionales
    print_info "Descargando wordlists adicionales..."
    
    # API endpoints
    curl -s -L -o api-endpoints.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web_Content/api/api-endpoints.txt 2>/dev/null || true
    
    # Common
    curl -s -L -o common.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt 2>/dev/null || true
    
    # Directory list
    curl -s -L -o directory-list-2.3-medium.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt 2>/dev/null || true
    
    # Params
    curl -s -L -o params.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/burp-parameter-names.txt 2>/dev/null || true
    
    # Crear wordlist combinada
    print_info "Creando wordlist combinada..."
    if [[ -d "SecLists/Discovery/Web-Content" ]]; then
        find SecLists/Discovery/Web-Content -type f -name "*.txt" -exec cat {} \; 2>/dev/null | sort -u > all.txt 2>/dev/null || true
    fi
    
    # Wordlist personalizada para Kali
    if [[ -f "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt" ]]; then
        cp /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt kali-dirlist.txt 2>/dev/null || true
    fi
    
    print_success "Wordlists instaladas en $TOOLS_DIR/wordlists"
}

setup_directories() {
    print_step "Configurando estructura de directorios..."
    
    # Crear todos los directorios necesarios
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$TOOLS_DIR"
    sudo mkdir -p "$LOGS_DIR"
    sudo mkdir -p "$CONFIG_DIR"
    sudo mkdir -p "$REPORT_DIR"
    sudo mkdir -p "$INSTALL_DIR/scripts"
    
    # Cambiar propietario al usuario actual
    sudo chown -R $USER:$USER "$INSTALL_DIR" 2>/dev/null || true
    
    # Crear archivos de configuración por defecto
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# CuackRecon Configuration
target_url: ""
scan_depth: 3
max_concurrency: 50
timeout: 30

# Tools configuration
tools:
  nmap:
    enabled: true
    ports: "1-1000"
    arguments: "-sV -sC"
  
  whatweb:
    enabled: true
    arguments: "-a 3"
  
  nuclei:
    enabled: true
    templates: "critical,high,medium"
  
  ffuf:
    enabled: true
    wordlist: "/opt/cuackrecon/tools/wordlists/common.txt"
    threads: 50
  
  katana:
    enabled: true
    depth: 3
  
  linkfinder:
    enabled: true
  
  waybackurls:
    enabled: true

# Reporting
reporting:
  format: "html"
  output_dir: "/opt/cuackrecon/reports"
  include_visualizations: true
  max_items: 30
EOF
    
    print_success "Estructura de directorios creada"
}

install_nuclei_templates() {
    print_step "Instalando templates de Nuclei..."
    
    # Instalar templates de Nuclei
    if check_command nuclei; then
        nuclei -update-templates -ut 2>/dev/null || true
        print_success "Templates de Nuclei actualizados"
    else
        print_warning "Nuclei no está instalado, omitiendo actualización de templates"
    fi
}

create_scripts() {
    print_step "Creando scripts y lanzadores..."
    
    # Script principal de CuackRecon
    cat > "$INSTALL_DIR/cuackrecon.py" << 'EOF'
#!/usr/bin/env python3
# CuackRecon - Script principal
import os
import sys
from datetime import datetime

def main():
    print("🦆 CuackRecon - Herramienta de Reconocimiento")
    print("===============================================")
    print(f"Directorio: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    target = os.environ.get('TARGET_URL', 'No especificado')
    print(f"Objetivo: {target}")
    print("\nHerramientas disponibles:")
    
    tools = ['nmap', 'whatweb', 'nuclei', 'ffuf', 'katana', 'subfinder', 'httpx', 'linkfinder', 'sqlmap']
    for tool in tools:
        if os.system(f"command -v {tool} > /dev/null 2>&1") == 0:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool}")
    
    print("\nConfiguración en: /opt/cuackrecon/config/config.yaml")
    print("Logs en: /opt/cuackrecon/logs/")

if __name__ == "__main__":
    main()
EOF
    chmod +x "$INSTALL_DIR/cuackrecon.py"
    
    # Lanzador principal
    cat > "$INSTALL_DIR/launch.sh" << 'EOF'
#!/bin/bash
# CuackRecon Launcher

echo "🦆 CuackRecon - MegaReport Edition"
echo "===================================="
echo ""
echo "Selecciona una opción:"
echo "1) Activar entorno virtual"
echo "2) Ejecutar escaneo completo"
echo "3) Generar reporte"
echo "4) Ejecutar herramientas individuales"
echo "5) Ver logs"
echo "6) Ver wordlists"
echo "7) Información del sistema"
echo "8) Salir"
read -p "Opción: " option

case $option in
    1)
        /opt/cuackrecon/activate.sh
        ;;
    2)
        echo "Ejecutando escaneo completo..."
        export TARGET_URL=${TARGET_URL:-"https://ejemplo.com"}
        echo "Objetivo: $TARGET_URL"
        source /opt/cuackrecon/activate.sh
        python3 /opt/cuackrecon/cuackrecon.py
        ;;
    3)
        echo "Generando reporte..."
        source /opt/cuackrecon/activate.sh
        if [[ -f "/opt/cuackrecon/cuackrecon_megareport.py" ]]; then
            python3 /opt/cuackrecon/cuackrecon_megareport.py
        else
            echo "⚠️  No se encontró el generador de reportes"
            echo "Ejecuta primero el escaneo completo"
        fi
        ;;
    4)
        echo "Herramientas disponibles:"
        echo "----------------------------"
        for tool in nmap whatweb nuclei ffuf katana subfinder httpx waybackurls linkfinder sqlmap gau feroxbuster naabu; do
            if command -v $tool &> /dev/null; then
                version=$($tool -version 2>/dev/null | head -1 || echo "")
                echo "✅ $tool $version"
            else
                echo "❌ $tool"
            fi
        done
        echo "----------------------------"
        echo ""
        read -p "Herramienta: " tool
        if command -v $tool &> /dev/null; then
            echo "Ejecutando $tool..."
            $tool "$@"
        else
            echo "Herramienta no encontrada"
        fi
        ;;
    5)
        echo "Logs disponibles:"
        ls -la /opt/cuackrecon/logs/
        echo ""
        if [[ -d "/opt/cuackrecon/logs" ]]; then
            echo "Últimos logs:"
            tail -5 /opt/cuackrecon/logs/*.txt 2>/dev/null || echo "No hay logs"
        fi
        ;;
    6)
        echo "Wordlists disponibles:"
        ls -lh /opt/cuackrecon/tools/wordlists/ | grep -v "^d"
        echo ""
        echo "Tamaño total: $(du -sh /opt/cuackrecon/tools/wordlists/ 2>/dev/null | cut -f1)"
        ;;
    7)
        echo "=== Información del Sistema ==="
        echo "OS: $(uname -a)"
        echo "Python: $(python3 --version)"
        echo "Go: $(go version 2>/dev/null || echo 'No instalado')"
        echo "Entorno virtual: $VIRTUAL_ENV"
        echo "TARGET_URL: ${TARGET_URL:-'No definido'}"
        echo "Directorio: /opt/cuackrecon"
        ;;
    8)
        exit 0
        ;;
    *)
        echo "Opción inválida"
        ;;
esac
EOF
    chmod +x "$INSTALL_DIR/launch.sh"
    
    # Crear enlaces simbólicos
    sudo ln -sf "$INSTALL_DIR/launch.sh" /usr/local/bin/cuackrecon 2>/dev/null || true
    sudo ln -sf "$INSTALL_DIR/activate.sh" /usr/local/bin/cuackactivate 2>/dev/null || true
    
    print_success "Scripts y lanzadores creados"
    print_info "Para usar: cuackrecon (lanzador) o source cuackactivate (entorno virtual)"
}

# ==============================================
# FUNCIÓN PRINCIPAL
# ==============================================

main() {
    clear
    print_header
    
    # Verificar usuario
    if [[ $EUID -eq 0 ]]; then
        print_warning "No se recomienda ejecutar como root. Continuando..."
    fi
    
    # Preguntar si continuar
    echo -e "${YELLOW}Este instalador descargará e instalará múltiples herramientas de reconocimiento.${NC}"
    echo -e "${YELLOW}El proceso puede tomar varios minutos dependiendo de tu conexión.${NC}"
    echo -e "${YELLOW}Se instalará en: $INSTALL_DIR${NC}"
    echo -e "${YELLOW}Se usará un entorno virtual de Python para evitar conflictos con Kali.${NC}"
    echo ""
    read -p "¿Continuar con la instalación? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Instalación cancelada."
        exit 0
    fi
    
    # Instalación
    install_dependencies
    setup_directories
    create_virtualenv
    install_python_packages
    install_go_tools
    install_security_tools
    install_wordlists
    install_nuclei_templates
    create_scripts
    
    # Resumen final
    echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎉 INSTALACIÓN COMPLETADA EXITOSAMENTE${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}📁 Directorio de instalación:${NC} $INSTALL_DIR"
    echo -e "${BLUE}📂 Logs:${NC} $LOGS_DIR"
    echo -e "${BLUE}📊 Reportes:${NC} $REPORT_DIR"
    echo -e "${BLUE}🔧 Herramientas:${NC} $TOOLS_DIR"
    echo -e "${BLUE}🐍 Entorno virtual:${NC} $VENV_DIR"
    echo ""
    echo -e "${YELLOW}Para usar CuackRecon:${NC}"
    echo "1. Activar entorno virtual: source $INSTALL_DIR/activate.sh"
    echo "2. O usar el lanzador: cuackrecon"
    echo "3. Exportar objetivo: export TARGET_URL='https://ejemplo.com'"
    echo ""
    echo -e "${CYAN}⚠️  ¡No olvides tener permisos para escanear el objetivo!${NC}"
    echo -e "${CYAN}⚠️  El uso de estas herramientas debe ser ético y legal.${NC}"
    echo ""
    
    # Verificar instalación
    echo -e "${BLUE}Verificando herramientas instaladas:${NC}"
    tools=("nmap" "whatweb" "nuclei" "ffuf" "katana" "subfinder" "httpx" "waybackurls" "linkfinder" "sqlmap" "gau" "feroxbuster" "naabu")
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            echo -e "${GREEN}✓ $tool${NC}"
        else
            echo -e "${RED}✗ $tool${NC}"
        fi
    done
    echo ""
    
    # Probar activación del entorno virtual
    echo -e "${BLUE}Probando entorno virtual:${NC}"
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        echo -e "${GREEN}✓ Entorno virtual existe${NC}"
        echo -e "${GREEN}✓ Script de activación: $INSTALL_DIR/activate.sh${NC}"
    else
        echo -e "${RED}✗ Entorno virtual no encontrado${NC}"
        echo "Puedes crearlo manualmente: python3 -m venv $VENV_DIR"
    fi
    echo ""
    
    echo -e "${GREEN}¡Listo para usar! 🚀${NC}"
    echo -e "${YELLOW}Ejecuta 'cuackrecon' para comenzar${NC}"
}

# ==============================================
# EJECUTAR INSTALADOR
# ==============================================

main "$@"
