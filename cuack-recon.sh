#!/bin/bash
# ============================================================
# RECONOCIMIENTO AUTENTICADO - VERSIÓN MEJORADA PARA BUG BOUNTY
# ============================================================

# ============================================================
# VARIABLES DE CONFIGURACIÓN
# ============================================================

# Valores por defecto
CONFIG_FILE=""
TARGET_URL=""
TARGET_DOMAIN=""
WORDLIST_SELF="weblist.txt"
WORDLIST_FFUF="weblist.txt"
PARAMATER_NAMES="weblist.txt"
COOKIES=""
BEARER_TOKEN=""
EXTRA_HEADERS=""
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
VERBOSE=false
AUTO_MODE=false
AUTO_APPROVE=false
RESUME_MODE=false

# Rate Limiting
RATE_LIMIT=15 # peticiones por segundo
MAX_RETRIES=3
RETRY_DELAY=5
REQUEST_DELAY=0.5  # segundos entre peticiones
FFUF_THREADS=30  # <--- AÑADE ESTA LÍNEA

# Variables para detección de bloqueos
BLOCKED=false
BLOCK_COUNT=0
MAX_BLOCK_COUNT=3

# Scope
SCOPE_DOMAINS=()
EXCLUDE_DOMAINS=()

# URLs peligrosas a evitar en crawling
DANGEROUS_PATTERNS=(
    "delete"
    "remove"
    "drop"
    "truncate"
    "exec"
    "eval"
    "system"
    "shell"
    "cmd"
    "command"
    "admin"
    "root"
    "su"
    "chmod"
    "chown"
    "wget"
    "curl"
    "nc"
    "netcat"
    "bash"
    "sh"
    "python"
    "perl"
    "php"
    "jsp"
    "asp"
)

# Variables de checkpoint
CHECKPOINT_DIR="checkpoints"
CURRENT_STEP=""
COMPLETED_STEPS=()

# ============================================================
# PARENT MAP
# ============================================================

# Mapeo de sub-pasos a sus padres
declare -A PARENT_MAP=(
    # Basic
    ["nmap"]="basic"
    ["whatweb"]="basic"
    
    # Historical
    ["gau"]="historical"
    ["wayback"]="historical"
    ["unify"]="historical"
    
    # Active
    ["httpx_historical"]="active"
    ["httpx_main"]="active"
    
    # Crawling
    ["katana_full"]="crawling"
    ["katana_js"]="crawling"
    
    # JS Recon
    ["linkfinder"]="js_recon"
    
    # Enumeration
    ["cuacktest"]="enumeration"
    ["ffuf_dirs"]="enumeration"
    ["ffuf_params"]="enumeration"
    ["arjun"]="enumeration"
    
    # Subdomains
    ["subfinder"]="subdomains"
    ["assetfinder"]="subdomains"
    ["httpx_subdomains"]="subdomains"
    
    # Vulnerabilities
    ["nuclei_tech"]="vulnerabilities"
    ["nuclei_exposure"]="vulnerabilities"
    ["nuclei_misconfig"]="vulnerabilities"
    ["nuclei_all"]="vulnerabilities"
    
    # Report
    ["cuackreport"]="report"
)

# ============================================================
# FUNCIONES DE CHECKPOINT
# ============================================================

# Función para guardar estado
save_checkpoint() {
    local step="$1"
    mkdir -p "$CHECKPOINT_DIR"
    echo "$step" > "$CHECKPOINT_DIR/last_step.txt"
    printf '%s\n' "${COMPLETED_STEPS[@]}" > "$CHECKPOINT_DIR/completed_steps.txt"
    
    # Guardar configuración
cat > "$CHECKPOINT_DIR/config.env" << EOF
TARGET_URL="$TARGET_URL"
TARGET_DOMAIN="$TARGET_DOMAIN"
RATE_LIMIT=$RATE_LIMIT
STEPS="$STEPS"
AUTO_MODE=$AUTO_MODE
USER_AGENT="$USER_AGENT"
COOKIES="$COOKIES"
BEARER_TOKEN="$BEARER_TOKEN"
EXTRA_HEADERS="$EXTRA_HEADERS"
WORDLIST_SELF="$WORDLIST_SELF"
WORDLIST_FFUF="$WORDLIST_FFUF"
PARAMATER_NAMES="$PARAMATER_NAMES"
FFUF_THREADS="$FFUF_THREADS"  # <--- AÑADE ESTA LÍNEA
EOF
}

# Función para cargar estado
load_checkpoint() {
    if [ -f "$CHECKPOINT_DIR/last_step.txt" ]; then
        CURRENT_STEP=$(cat "$CHECKPOINT_DIR/last_step.txt")
        if [ -f "$CHECKPOINT_DIR/completed_steps.txt" ]; then
            mapfile -t COMPLETED_STEPS < "$CHECKPOINT_DIR/completed_steps.txt"
        fi
        log_info "Checkpoint cargado. Último paso: $CURRENT_STEP"
        log_info "Pasos completados: ${#COMPLETED_STEPS[@]}"
        return 0
    fi
    return 1
}

# Función para verificar si un paso ya fue completado
is_step_completed() {
    local step="$1"
    for s in "${COMPLETED_STEPS[@]}"; do
        if [ "$s" = "$step" ]; then
            return 0
        fi
    done
    return 1
}

# Función para marcar un paso como completado
mark_step_completed() {
    local step="$1"
    if ! is_step_completed "$step"; then
        COMPLETED_STEPS+=("$step")
        save_checkpoint "$step"
    fi
}

# Función para manejar Ctrl+C
cleanup_on_exit() {
    log_info "Cancelación detectada. Guardando estado..."
    
    # Guardar el checkpoint actual
    if [ ! -z "$CURRENT_STEP" ]; then
        save_checkpoint "$CURRENT_STEP"
        log_info "Checkpoint guardado en: $CHECKPOINT_DIR"
        log_info "Para reanudar, ejecuta: $0 --resume"
    fi
    
    # No borrar logs
    log_info "Logs preservados en: logs/"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ⚠️  ESCANEO PAUSADO ⚠️                       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Los resultados parciales se han guardado en:"
    echo "  - logs/: Archivos de log generados"
    echo "  - $CHECKPOINT_DIR/: Punto de control para reanudar"
    echo ""
    echo "  Para reanudar el escaneo:"
    echo "  $0 --resume"
    echo ""
    exit 1
}

# Capturar señales
trap cleanup_on_exit SIGINT SIGTERM

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

# Función para logging con timestamps
log() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a logs/execution.log
}

log_info() {
    log "INFO" "$1"
}

log_warn() {
    log "WARN" "$1"
}

log_error() {
    log "ERROR" "$1"
}

log_success() {
    log "SUCCESS" "$1"
}

# Función para extraer dominio de la URL
extract_domain() {
    local url=$1
    # Eliminar protocolo, path y puerto
    echo "$url" | sed -e 's|^[^/]*//||' -e 's|/.*$||' -e 's|:.*$||'
}

# Función para extraer el dominio base (sin subdominios)
extract_base_domain() {
    local domain=$1
    echo "$domain" | awk -F. '{print $(NF-1)"."$NF}'
}

# Función para filtrar URLs peligrosas
filter_dangerous_urls() {
    local input_file="$1"
    local output_file="$2"
    
    log_info "Filtrando URLs peligrosas..."
    
    # Crear patrón grep para excluir
    local exclude_pattern=""
    for pattern in "${DANGEROUS_PATTERNS[@]}"; do
        if [ -z "$exclude_pattern" ]; then
            exclude_pattern="$pattern"
        else
            exclude_pattern="$exclude_pattern|$pattern"
        fi
    done
    
    # Filtrar URLs peligrosas
    grep -v -E "$exclude_pattern" "$input_file" > "$output_file" 2>/dev/null || true
    
    local removed=$(wc -l < "$input_file" 2>/dev/null || echo "0")
    local kept=$(wc -l < "$output_file" 2>/dev/null || echo "0")
    log_info "URLs peligrosas filtradas: $((removed - kept))"
}

# Función para verificar si estamos en el scope
is_in_scope() {
    local url="$1"
    local domain=$(extract_domain "$url")
    
    # Verificar si está excluido
    for exclude in "${EXCLUDE_DOMAINS[@]}"; do
        # Eliminar comillas y caracteres especiales
        exclude=$(echo "$exclude" | tr -d '"' | tr -d "'")
        if [[ "$domain" == *"$exclude"* ]] || [[ "$domain" == "$exclude" ]]; then
            return 1
        fi
    done
    
    # Si no hay scope definido, todo es permitido
    if [ ${#SCOPE_DOMAINS[@]} -eq 0 ]; then
        log_warn "No se ha definido scope. Escaneando dominio completo: $domain"
        return 0
    fi
    
    # Verificar si está en el scope
    for scope in "${SCOPE_DOMAINS[@]}"; do
        # Limpiar el scope
        scope=$(echo "$scope" | tr -d '"' | tr -d "'")
        # Quitar *. si existe para comparación
        clean_scope="${scope#\*.}"
        if [[ "$domain" == *"$clean_scope"* ]] || [[ "$domain" == "$clean_scope" ]]; then
            return 0
        fi
    done
    
    return 1
}

# ============================================================
# FUNCIONES DE RATE LIMITING Y DETECCIÓN DE BLOQUEOS
# ============================================================

# Función para detectar si estamos bloqueados
check_if_blocked() {
    local url="$1"
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" \
        -H "User-Agent: $USER_AGENT" \
        --max-time 5 2>/dev/null)
    
    # Códigos que indican bloqueo
    if [[ $response == "403" ]] || [[ $response == "429" ]] || [[ $response == "503" ]] || [[ $response == "000" ]]; then
        BLOCK_COUNT=$((BLOCK_COUNT + 1))
        log_warn "POSIBLE BLOQUEO DETECTADO (HTTP $response) - Intento $BLOCK_COUNT/$MAX_BLOCK_COUNT"
        
        if [ $BLOCK_COUNT -ge $MAX_BLOCK_COUNT ]; then
            BLOCKED=true
            log_error "BLOQUEO CONFIRMADO. Sugerencias:"
            echo "    - Reducir el rate limit (actual: $RATE_LIMIT req/sec)"
            echo "    - Cambiar User-Agent"
            echo "    - Usar proxies rotativos"
            echo "    - Esperar $RETRY_DELAY segundos antes de continuar"
            sleep $RETRY_DELAY
            return 1
        fi
        return 1
    fi
    
    # Resetear contador si funciona
    BLOCK_COUNT=0
    return 0
}

# Función para ejecutar con rate limiting y reintentos
execute_with_retry() {
    local cmd="$1"
    local step_name="$2"
    local step_key="$3"
    local retries=0
    
    # Verificar si ya fue completado
    if is_step_completed "$step_key"; then
        log_info "✓ Paso ya ejecutado: $step_name"
        return 0
    fi
    
    log_info "Ejecutando: $step_name"
    
    # Guardar checkpoint antes de ejecutar
    CURRENT_STEP="$step_key"
    save_checkpoint "$step_key"
    
    while [ $retries -lt $MAX_RETRIES ]; do
        # Verificar si estamos bloqueados antes de ejecutar
        if [ "$BLOCKED" = true ]; then
            log_error "Script bloqueado. Esperando $RETRY_DELAY segundos..."
            sleep $RETRY_DELAY
            BLOCKED=false
            BLOCK_COUNT=0
            continue
        fi
        
        # Ejecutar el comando
        if eval $cmd; then
            log_success "Completado: $step_name"
            mark_step_completed "$step_key"
            return 0
        else
            retries=$((retries+1))
            log_warn "Intento $retries/$MAX_RETRIES falló para: $step_name"
            
            # Verificar si fue bloqueo
            if check_if_blocked "$TARGET_URL"; then
                log_info "No parece bloqueo, reintentando..."
            else
                log_warn "Posible bloqueo detectado, reduciendo velocidad..."
                sleep $((RETRY_DELAY * retries))
            fi
            
            sleep $LAY
        fi
    done
    
    log_error "FALLÓ después de $MAX_RETRIES intentos: $step_name"
    return 1
}

# ============================================================
# FUNCIONES PARA CARGAR CONFIGURACIÓN
# ============================================================

load_config() {
    local config_file="$1"
    
    if [ ! -f "$config_file" ]; then
        log_error "Archivo de configuración no encontrado: $config_file"
        exit 1
    fi
    
    log_info "Cargando configuración desde: $config_file"
    
    # Detectar formato del archivo
    if [[ "$config_file" == *.yaml ]] || [[ "$config_file" == *.yml ]]; then
        # Cargar YAML
        TARGET_URL=$(grep -E '^[[:space:]]*target_url:' "$config_file" | sed -E 's/^[[:space:]]*target_url:[[:space:]]*//' | tr -d '"')
        WORDLIST_SELF=$(grep -E '^[[:space:]]*wordlist_self:' "$config_file" | sed -E 's/^[[:space:]]*wordlist_self:[[:space:]]*//' | tr -d '"')
        WORDLIST_FFUF=$(grep -E '^[[:space:]]*wordlist_ffuf:' "$config_file" | sed -E 's/^[[:space:]]*wordlist_ffuf:[[:space:]]*//' | tr -d '"')
        PARAMATER_NAMES=$(grep -E '^[[:space:]]*paramater_names:' "$config_file" | sed -E 's/^[[:space:]]*paramater_names:[[:space:]]*//' | tr -d '"')
        COOKIES=$(grep -E '^[[:space:]]*cookies:' "$config_file" | sed -E 's/^[[:space:]]*cookies:[[:space:]]*//' | tr -d '"')
        BEARER_TOKEN=$(grep -E '^[[:space:]]*bearer_token:' "$config_file" | sed -E 's/^[[:space:]]*bearer_token:[[:space:]]*//' | tr -d '"')
        EXTRA_HEADERS=$(grep -E '^[[:space:]]*extra_headers:' "$config_file" | sed -E 's/^[[:space:]]*extra_headers:[[:space:]]*//' | tr -d '"')
        USER_AGENT=$(grep -E '^[[:space:]]*user_agent:' "$config_file" | sed -E 's/^[[:space:]]*user_agent:[[:space:]]*//' | tr -d '"')
        
        # Rate limiting
        RATE_LIMIT=$(grep -E '^[[:space:]]*rate_limit:' "$config_file" | sed -E 's/^[[:space:]]*rate_limit:[[:space:]]*//' | tr -d '"')
        RATE_LIMIT=${RATE_LIMIT:-50}
        
        # lay
        REQUEST_DELAY=$(awk "BEGIN {printf \"%.6f\", 1/$RATE_LIMIT}")
        
        # Después de cargar RATE_LIMIT
        KATANA_DEPTH=$(grep -E '^[[:space:]]*katana_depth:' "$config_file" | sed -E 's/^[[:space:]]*katana_depth:[[:space:]]*//' | tr -d '"')
        KATANA_DEPTH=${KATANA_DEPTH:-2}

        FFUF_THREADS=$(grep -E '^[[:space:]]*ffuf_threads:' "$config_file" | sed -E 's/^[[:space:]]*ffuf_threads:[[:space:]]*//' | tr -d '"')
        FFUF_THREADS=${FFUF_THREADS:-30}  # Valor por defecto si no está definido
        
        # Scope
        SCOPE_DOMAINS=()
        in_scope_block=false
        while IFS= read -r line; do
            # Detectar inicio del bloque scope
            if [[ "$line" =~ ^[[:space:]]*scope:[[:space:]]*$ ]]; then
                in_scope_block=true
                continue
            fi
            # Detectar fin del bloque scope (cuando empieza otra clave)
            if [[ "$in_scope_block" == true ]] && [[ "$line" =~ ^[[:space:]]*[a-zA-Z_]+:[[:space:]]*$ ]]; then
                in_scope_block=false
            fi
            # Capturar líneas con guión dentro del bloque
            if [[ "$in_scope_block" == true ]] && [[ "$line" =~ ^[[:space:]]*-[[:space:]]*(.+)$ ]]; then
                SCOPE_DOMAINS+=("${BASH_REMATCH[1]}")
            fi
        done < "$config_file"
        
        # Exclude
        EXCLUDE_DOMAINS=()
        in_exclude_block=false
        while IFS= read -r line; do
            # Detectar inicio del bloque exclude
            if [[ "$line" =~ ^[[:space:]]*exclude:[[:space:]]*$ ]]; then
                in_exclude_block=true
                continue
            fi
            # Detectar fin del bloque exclude
            if [[ "$in_exclude_block" == true ]] && [[ "$line" =~ ^[[:space:]]*[a-zA-Z_]+:[[:space:]]*$ ]]; then
                in_exclude_block=false
            fi
            # Capturar líneas con guión dentro del bloque
            if [[ "$in_exclude_block" == true ]] && [[ "$line" =~ ^[[:space:]]*-[[:space:]]*(.+)$ ]]; then
                EXCLUDE_DOMAINS+=("${BASH_REMATCH[1]}")
            fi
        done < "$config_file"
        
        # DEBUG - Mostrar lo que se cargó (opcional, eliminar después)
        if [ "$VERBOSE" = true ]; then
            echo "DEBUG: SCOPE_DOMAINS = ${SCOPE_DOMAINS[@]}"
            echo "DEBUG: EXCLUDE_DOMAINS = ${EXCLUDE_DOMAINS[@]}"
        fi
        
        # Pasos a ejecutar
        STEPS=$(sed -n '/^[[:space:]]*steps:/,/^[[:space:]]*[a-zA-Z]/p' "$config_file" | grep -E '^[[:space:]]*-[[:space:]]*' | sed -E 's/^[[:space:]]*-[[:space:]]*//' | tr -d '"' | tr '\n' ' ')
        
    elif [[ "$config_file" == *.conf ]]; then
        source "$config_file"
        if [ -z "$STEPS" ]; then
            STEPS="all"
        fi
    else
        source "$config_file"
        if [ -z "$STEPS" ]; then
            STEPS="all"
        fi
    fi
    
    # Si no hay STEPS definido, usar todos
    if [ -z "$STEPS" ]; then
        STEPS="all"
    fi
    
    # Validar que se cargó la URL
    if [ -z "$TARGET_URL" ]; then
        log_error "No se encontró 'target_url' en el archivo de configuración"
        exit 1
    fi
    
    # Extraer dominio automáticamente
    TARGET_DOMAIN=$(extract_domain "$TARGET_URL")
    
    # Verificar scope
    if ! is_in_scope "$TARGET_URL"; then
        log_error "El objetivo $TARGET_DOMAIN está fuera del scope definido"
        exit 1
    fi
    
    # Activar modo automático
    AUTO_MODE=true
}

# ============================================================
# FUNCIONES DE AUTORIZACIÓN
# ============================================================

check_authorization() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ⚠️  AVISO DE BUG BOUNTY ⚠️                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "1. Asegúrate de tener autorización para escanear este dominio"
    echo "2. Respeta los límites de rate-limit del programa de bug bounty"
    echo "3. No excedas las 15 peticiones por segundo por defecto"
    echo "4. Para escaneos extensivos, contacta primero al equipo de seguridad"
    echo ""
    echo "Objetivo: $TARGET_URL"
    echo "Rate Limit: $RATE_LIMIT peticiones/segundo"
    echo ""
    
    if [ "$AUTO_MODE" = true ] && [ "$AUTO_APPROVE" = false ]; then
        read -p "¿Has obtenido autorización para escanear este objetivo? (s/n): " authorization
        if [[ $authorization != "s" ]]; then
            log_error "Sin autorización, no se puede continuar"
            exit 1
        fi
    elif [ "$AUTO_MODE" = false ]; then
        read -p "¿Has obtenido autorización para escanear este objetivo? (s/n): " authorization
        if [[ $authorization != "s" ]]; then
            log_error "Sin autorización, no se puede continuar"
            exit 1
        fi
    fi
    
    log_info "Autorización confirmada para $TARGET_DOMAIN"
}

# ============================================================
# FUNCIÓN PARA VERIFICAR SI UN PASO DEBE EJECUTARSE
# ============================================================

should_run_step() {
    local step_key="$1"
    
    if [ "$AUTO_MODE" != true ]; then
        return 2
    fi
    
    if [ "$STEPS" = "all" ]; then
        return 0
    fi
    
    # Verificar si el paso está en la lista
    if echo "$STEPS" | grep -q "\b$step_key\b"; then
        return 0
    fi
    
    # Si no está, verificar si es sub-paso de un paso que está en la lista
    local parent_step="${PARENT_MAP[$step_key]}"
    if [ ! -z "$parent_step" ] && echo "$STEPS" | grep -q "\b$parent_step\b"; then
        return 0
    fi
    
    return 1
}

# ============================================================
# FUNCIÓN PARA PREGUNTAR AL USUARIO
# ============================================================

ask_step() {
    local step_name="$1"
    local step_desc="$2"
    local step_key="$3"
    local is_substep="${4:-false}"
    
    # Verificar si ya fue completado
    if is_step_completed "$step_key"; then
        log_info "✓ Paso ya completado: $step_name"
        return 2  # Retorno especial para "ya completado"
    fi
    
    if [ "$AUTO_MODE" = true ]; then
        local should_run
        should_run_step "$step_key"
        local result=$?
        
        if [ $result -eq 0 ]; then
            log_info "AUTO ✓ Ejecutando: $step_name"
            return 0
        elif [ $result -eq 1 ]; then
            # Si es un sub-paso, verificar si el padre está en la lista
            if [ "$is_substep" = "true" ]; then
                # Buscar el paso padre usando el array de mapeo
                local parent_step="${PARENT_MAP[$step_key]}"
                
                # Si no tiene mapeo explícito, intentar inferir
                if [ -z "$parent_step" ]; then
                    # Si tiene guión bajo, tomar la primera parte
                    if [[ "$step_key" == *_* ]]; then
                        parent_step=$(echo "$step_key" | cut -d'_' -f1)
                    fi
                fi
                
                if [ ! -z "$parent_step" ] && echo "$STEPS" | grep -q "\b$parent_step\b"; then
                    log_info "AUTO ✓ Ejecutando (sub-paso de $parent_step): $step_name"
                    return 0
                fi
            fi
            log_info "AUTO ✗ Omitiendo: $step_name"
            return 1
        else
            return 1
        fi
    fi
    
    # Modo interactivo
    while true; do
        echo ""
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║ PASO: $step_name"
        echo "║ $step_desc"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        read -p "  ¿Ejecutar este paso? (s/n): " response
        case $response in
            [sS]* ) return 0;;
            [nN]* ) return 1;;
            * ) echo "  Por favor, responde 's' (sí) o 'n' (no).";;
        esac
    done
}

# ============================================================
# FUNCIÓN PARA EJECUTAR COMANDO
# ============================================================

run_cmd() {
    local cmd="$1"
    local step_name="$2"
    local step_key="${3:-$step_name}"  # Usar el nombre como key si no se proporciona
    
    if [ "$VERBOSE" = true ]; then
        log_info "Comando: $cmd"
    fi
    
    execute_with_retry "$cmd" "$step_name" "$step_key"
}

run_cmd_background() {
    local cmd="$1"
    local step_name="$2"
    local step_key="${3:-$step_name}"
    
    # Verificar si ya fue completado
    if is_step_completed "$step_key"; then
        log_info "✓ Paso ya ejecutado: $step_name"
        return 0
    fi
    
    log_info "Ejecutando en background: $step_name"
    if [ "$VERBOSE" = true ]; then
        log_info "Comando: $cmd"
    fi
    
    # Guardar checkpoint antes de ejecutar
    CURRENT_STEP="$step_key"
    save_checkpoint "$step_key"
    
    eval $cmd &
    local pid=$!
    echo $pid >> logs/background_pids.txt
    log_info "PID: $pid (ejecutándose en background)"
    
    # Esperar a que termine el proceso
    wait $pid
    if [ $? -eq 0 ]; then
        log_success "Completado: $step_name"
        mark_step_completed "$step_key"
        return 0
    else
        log_error "FALLÓ: $step_name"
        return 1
    fi
}

# ============================================================
# FUNCIONES DE RECONOCIMIENTO ADICIONALES
# ============================================================

# Función para verificar archivos comunes
check_common_files() {
    local url="$1"
    local output_file="$2"
    
    log_info "Buscando archivos comunes..."
    
    local files=("robots.txt" "sitemap.xml" ".git/HEAD" ".env" "wp-config.php" "config.php" "backup.sql" "phpinfo.php" "info.php" "test.php" "debug.php" "logs.txt" "error.log")
    
    echo "" > "$output_file"
    for file in "${files[@]}"; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" "$url/$file" \
            -H "User-Agent: $USER_AGENT" \
            --max-time 3 2>/dev/null)
        
        if [[ $response == "200" ]] || [[ $response == "401" ]] || [[ $response == "403" ]]; then
            echo "[+] Encontrado: $file (HTTP $response)" | tee -a "$output_file"
            log_info "Archivo común encontrado: $file (HTTP $response)"
        fi
    done
}

# Función para probar métodos HTTP
test_http_methods() {
    local url="$1"
    local output_file="$2"
    
    log_info "Probando métodos HTTP..."
    
    local methods=("OPTIONS" "GET" "HEAD" "POST" "PUT" "DELETE" "TRACE" "CONNECT" "PATCH")
    
    echo "" > "$output_file"
    for method in "${methods[@]}"; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" \
            -H "User-Agent: $USER_AGENT" \
            --max-time 3 2>/dev/null)
        
        if [[ $response != "000" ]] && [[ $response != "405" ]]; then
            echo "[+] Método permitido: $method (HTTP $response)" | tee -a "$output_file"
            log_info "Método HTTP permitido: $method (HTTP $response)"
        elif [[ $response == "405" ]]; then
            echo "[-] Método no permitido: $method" >> "$output_file"
        fi
    done
}

# ============================================================
# PROCESAMIENTO DE PARÁMETROS
# ============================================================

print_usage() {
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  -c, --config FILE           Archivo de configuración (YAML, .conf o .env)"
    echo "  -u, --url URL              URL objetivo"
    echo "  --cookies COOKIES          Cookies en formato 'nombre1=valor1; nombre2=valor2'"
    echo "  --bearer TOKEN             Bearer token"
    echo "  --headers HEADERS          Headers adicionales"
    echo "  --wordlist FILE            Wordlist para ffuf (default: weblist.txt)"
    echo "  --params FILE              Wordlist para parámetros (default: weblist.txt)"
    echo "  --user-agent UA            User-Agent personalizado"
    echo "  --rate-limit NUM           Peticiones por segundo (default: 15)"
    echo "  --max-retries NUM          Número de reintentos (default: 3)"
    echo "  -v, --verbose              Modo verbose"
    echo "  -y, --yes                  Auto-aprobar autorización"
    echo "  --resume                   Reanudar desde el último checkpoint"
    echo "  -h, --help                 Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 -c config.yaml"
    echo "  $0 -u https://ejemplo.com --rate-limit 30"
    echo "  $0 --resume                # Reanudar escaneo pausado"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -u|--url)
            TARGET_URL="$2"
            shift 2
            ;;
        --cookies)
            COOKIES="$2"
            shift 2
            ;;
        --bearer)
            BEARER_TOKEN="$2"
            shift 2
            ;;
        --headers)
            EXTRA_HEADERS="$2"
            shift 2
            ;;
        --wordlist)
            WORDLIST_FFUF="$2"
            shift 2
            ;;
        --params)
            PARAMATER_NAMES="$2"
            shift 2
            ;;
        --user-agent)
            USER_AGENT="$2"
            shift 2
            ;;
        --rate-limit)
            RATE_LIMIT="$2"
            shift 2
            ;;
        --max-retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -y|--yes)
            AUTO_APPROVE=true
            shift
            ;;
        --resume)
            RESUME_MODE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Error: Opción desconocida $1"
            print_usage
            exit 1
            ;;
    esac
done

# ============================================================
# CHECKPOINT - RESUMEN
# ============================================================

# Si estamos en modo resume, cargar configuración del checkpoint
if [ "$RESUME_MODE" = true ]; then
    if load_checkpoint; then
        # Cargar configuración guardada
        if [ -f "$CHECKPOINT_DIR/config.env" ]; then
            source "$CHECKPOINT_DIR/config.env"
            log_info "Configuración cargada desde checkpoint"
            log_info "Target: $TARGET_URL"
            log_info "Pasos completados: ${#COMPLETED_STEPS[@]}"
        else
            log_error "No se encontró configuración en el checkpoint"
            exit 1
        fi
        AUTO_MODE=true
    else
        log_error "No hay checkpoint para reanudar"
        echo ""
        echo "Para crear un checkpoint, ejecuta un escaneo normalmente y usa Ctrl+C para pausarlo."
        exit 1
    fi
fi

# Cargar configuración si se especificó
if [ ! -z "$CONFIG_FILE" ] && [ "$RESUME_MODE" != true ]; then
    load_config "$CONFIG_FILE"
fi

# Verificar que se proporcionó URL
if [ -z "$TARGET_URL" ]; then
    echo "Error: La URL objetivo es requerida (-u o --url, o en archivo de configuración)"
    print_usage
    exit 1
fi

# Extraer dominio automáticamente
if [ -z "$TARGET_DOMAIN" ]; then
    TARGET_DOMAIN=$(extract_domain "$TARGET_URL")
fi

# Verificar autorización
if [ "$RESUME_MODE" != true ]; then
    check_authorization
else
    log_info "Reanudando escaneo - Autorización previamente confirmada"
fi

# Verificar herramientas necesarias
log_info "Verificando herramientas..."
MISSING_TOOLS=()
for tool in nmap whatweb gau waybackurls httpx ffuf nuclei subfinder assetfinder katana; do
    if ! command -v $tool &> /dev/null; then
        MISSING_TOOLS+=($tool)
    fi
done

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    log_warn "Herramientas faltantes: ${MISSING_TOOLS[*]}"
    echo "Instálalas con:"
    echo "  - go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    echo "  - go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"
    echo "  - go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
    echo "  - go install github.com/ffuf/ffuf/v2@latest"
    echo "  - go install github.com/lc/gau/v2/cmd/gau@latest"
    echo "  - go install github.com/tomnomnom/waybackurls@latest"
    echo "  - go install github.com/projectdiscovery/katana/cmd/katana@latest"
    echo "  - go install github.com/tomnomnom/assetfinder@latest"
fi

# ============================================================
# CONSTRUCCIÓN DE HEADERS
# ============================================================

AUTH_HEADER=""
if [ ! -z "$BEARER_TOKEN" ]; then
    AUTH_HEADER="-H \"Authorization: $BEARER_TOKEN\""
fi

COOKIE_HEADER=""
if [ ! -z "$COOKIES" ]; then
    COOKIE_HEADER="-H \"Cookie: $COOKIES\""
fi

EXTRA_HEADERS_FLAG=""
if [ ! -z "$EXTRA_HEADERS" ]; then
    IFS=';' read -ra HEADERS_ARRAY <<< "$EXTRA_HEADERS"
    for header in "${HEADERS_ARRAY[@]}"; do
        header=$(echo "$header" | xargs)
        if [ ! -z "$header" ]; then
            EXTRA_HEADERS_FLAG="$EXTRA_HEADERS_FLAG -H \"$header\""
        fi
    done
fi

HTTPX_HEADERS=""
if [ ! -z "$COOKIE_HEADER" ]; then
    HTTPX_HEADERS="$HTTPX_HEADERS $COOKIE_HEADER"
fi
if [ ! -z "$AUTH_HEADER" ]; then
    HTTPX_HEADERS="$HTTPX_HEADERS $AUTH_HEADER"
fi
if [ ! -z "$EXTRA_HEADERS_FLAG" ]; then
    HTTPX_HEADERS="$HTTPX_HEADERS $EXTRA_HEADERS_FLAG"
fi

FFUF_HEADERS=""
if [ ! -z "$COOKIES" ]; then
    FFUF_HEADERS="$FFUF_HEADERS -H \"Cookie: $COOKIES\""
fi
if [ ! -z "$BEARER_TOKEN" ]; then
    FFUF_HEADERS="$FFUF_HEADERS -H \"Authorization: $BEARER_TOKEN\""
fi
if [ ! -z "$EXTRA_HEADERS" ]; then
    IFS=';' read -ra HEADERS_ARRAY <<< "$EXTRA_HEADERS"
    for header in "${HEADERS_ARRAY[@]}"; do
        header=$(echo "$header" | xargs)
        if [ ! -z "$header" ]; then
            FFUF_HEADERS="$FFUF_HEADERS -H \"$header\""
        fi
    done
fi

# ============================================================
# INICIO DEL RECONOCIMIENTO
# ============================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║      RECONOCIMIENTO MEJORADO PARA BUG BOUNTY              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "[+] Target URL: $TARGET_URL"
echo "[+] Dominio: $TARGET_DOMAIN"
echo "[+] Dominio Base: $(extract_base_domain "$TARGET_DOMAIN")"
echo "[+] Fecha: $(date)"
echo "[+] Rate Limit: $RATE_LIMIT peticiones/segundo"
echo "[+] Modo: $([ "$AUTO_MODE" = true ] && echo "Automático" || echo "Interactivo")"
if [ "$AUTO_MODE" = true ]; then
    echo "[+] Pasos: $([ "$STEPS" = "all" ] && echo "Todos" || echo "$STEPS")"
fi
if [ "$RESUME_MODE" = true ]; then
    echo "[+] Modo: RESUMEN (reanudando desde checkpoint)"
    echo "[+] Pasos completados: ${#COMPLETED_STEPS[@]}"
fi
echo "[+] Autorización: Confirmada"
echo ""

# Crear directorio para logs (preservar si existe)
if [ "$RESUME_MODE" = true ]; then
    log_info "Modo resumen - Preservando logs existentes"
    mkdir -p logs
else
    # Solo mover logs anteriores si no estamos en modo resumen
    if [ -d "logs" ] && [ ! -z "$(ls -A logs)" ]; then
        BACKUP_DIR="logs_backup_$(date +%Y%m%d_%H%M%S)"
        mv logs "$BACKUP_DIR"
        log_info "Logs anteriores movidos a: $BACKUP_DIR"
    fi
    mkdir -p logs
fi

# ============================================================
# FASE 0 - VERIFICACIÓN INICIAL
# ============================================================

log_info "FASE 0 - Verificación inicial"

# Verificar si el sitio está accesible
if ! check_if_blocked "$TARGET_URL"; then
    log_warn "El sitio podría estar bloqueando peticiones"
fi

# Verificar archivos comunes
if ask_step "Archivos comunes" "Buscar archivos comunes (.env, .git, etc.)" "common_files"; then
    echo ""
    log_info "Buscando archivos comunes..."
    check_common_files "$TARGET_URL" "logs/common_files.txt"
    mark_step_completed "common_files"
fi

# Probar métodos HTTP
if ask_step "Métodos HTTP" "Probar métodos HTTP permitidos" "http_methods"; then
    echo ""
    log_info "Probando métodos HTTP..."
    test_http_methods "$TARGET_URL" "logs/http_methods.txt"
    mark_step_completed "http_methods"
fi

# ============================================================
# FASE 1 - RECONOCIMIENTO BÁSICO
# ============================================================

if ask_step "Reconocimiento básico" "Nmap + WhatWeb + SpiderFoot" "basic"; then
    echo ""
    log_info "FASE 1 - Reconocimiento básico"
    
    if ask_step "Escaneo de puertos" "Nmap - Escaneo de puertos y servicios" "nmap" "true"; then
        run_cmd_background "nmap -Pn -sV -sC --script=http-title,http-headers,http-methods -T3 --max-rate 50 --max-retries 1 $TARGET_DOMAIN -oN logs/nmap.txt &" "nmap"
    fi
    
    if ask_step "Fingerprinting" "WhatWeb - Identificación de tecnologías" "whatweb" "true"; then
        run_cmd "whatweb -a 3 $TARGET_URL > logs/whatweb.txt" "WhatWeb" "whatweb"
    fi
    
    mark_step_completed "basic"
fi

# ============================================================
# FASE 2 - SUBDOMINIOS
# ============================================================

if ask_step "Subdominios" "Enumeración de subdominios" "subdomains"; then
    echo ""
    log_info "FASE 2 - Enumeración de subdominios"
    
    if ask_step "Subfinder" "Enumeración pasiva de subdominios" "subfinder" "true"; then
        run_cmd "subfinder -d $TARGET_DOMAIN -silent -o logs/subdomains.txt" "Subfinder" "subfinder"
    fi
    
    if ask_step "Assetfinder" "Enumeración adicional de subdominios" "assetfinder" "true"; then
        run_cmd "assetfinder --subs-only $TARGET_DOMAIN >> logs/subdomains.txt 2>/dev/null" "Assetfinder" "assetfinder"
    fi
    
    if [ -f "logs/subdomains.txt" ] && ask_step "Verificar subdominios" "HTTPX sobre subdominios" "httpx_subdomains" "true"; then
        run_cmd "cat logs/subdomains.txt | sort -u | httpx -silent -status-code -title -follow-redirects -threads 50 -rl $RATE_LIMIT $HTTPX_HEADERS | tee logs/alive_subdomains.txt" "HTTPX subdominios" "httpx_subdomains"
    fi
    
    mark_step_completed "subdomains"
fi

# ============================================================
# FASE 3 - URLS HISTÓRICAS
# ============================================================

if ask_step "URLs históricas" "Gau + Waybackurls - URLs históricas" "historical"; then
    echo ""
    log_info "FASE 3 - URLs históricas"
    
    if ask_step "Gau" "Obtener URLs con gau" "gau" "true"; then
        run_cmd "gau $TARGET_DOMAIN | tee logs/gau.txt" "Gau" "gau"
    fi
    
    if ask_step "Waybackurls" "Obtener URLs con waybackurls" "wayback" "true"; then
        run_cmd "waybackurls $TARGET_DOMAIN | tee logs/wayback.txt" "Waybackurls" "wayback"
    fi
    
    if ask_step "Unificar resultados" "Combinar URLs de todas las fuentes" "unify" "true"; then
        run_cmd "cat logs/gau.txt logs/wayback.txt 2>/dev/null | sort -u > logs/historical_urls.txt" "Unificar" "unify"
    fi
    
    mark_step_completed "historical"
fi

# ============================================================
# FASE 4 - HOSTS ACTIVOS
# ============================================================

if ask_step "Hosts activos" "HTTPX - Verificar hosts activos" "active"; then
    echo ""
    log_info "FASE 4 - Hosts activos"
    
    if [ -f "logs/historical_urls.txt" ] && ask_step "Verificar URLs históricas" "HTTPX sobre URLs históricas" "httpx_historical" "true"; then
        run_cmd "cat logs/historical_urls.txt | httpx -silent -status-code -title -tech-detect -follow-redirects -threads 50 -rl $RATE_LIMIT $HTTPX_HEADERS | tee logs/alive_historical.txt" "HTTPX histórico" "httpx_historical"
    fi
    
    if ask_step "Verificar objetivo principal" "HTTPX sobre URL principal" "httpx_main" "true"; then
        run_cmd "echo $TARGET_URL | httpx -silent -status-code -title -tech-detect -follow-redirects -threads 50 -rl $RATE_LIMIT $HTTPX_HEADERS | tee -a logs/alive.txt" "HTTPX principal" "httpx_main"
    fi
    
    mark_step_completed "active"
fi

# ============================================================
# FASE 5 - CRAWLING
# ============================================================

if ask_step "Crawling" "Katana - Crawling completo" "crawling"; then
    echo ""
    log_info "FASE 5 - Crawling"
    
    if ask_step "Crawling completo" "Katana - Crawl completo del sitio" "katana_full" "true"; then
        KATANA_CMD="katana -u $TARGET_URL -d $KATANA_DEPTH -c 20 -timeout 10 -silent -o logs/katana.txt"
        if [ ! -z "$COOKIES" ]; then
            KATANA_CMD="$KATANA_CMD -H \"Cookie: $COOKIES\""
        fi
        if [ ! -z "$BEARER_TOKEN" ]; then
            KATANA_CMD="$KATANA_CMD -H \"Authorization: $BEARER_TOKEN\""
        fi
        if [ ! -z "$USER_AGENT" ]; then
            KATANA_CMD="$KATANA_CMD -H \"User-Agent: $USER_AGENT\""
        fi
        run_cmd "$KATANA_CMD" "Katana crawl" "katana_full"
    fi
    
    if ask_step "Extraer JavaScript" "Katana - Extraer archivos JS" "katana_js" "true"; then
        KATANA_JS_CMD="katana -u $TARGET_URL -d $KATANA_DEPTH -jc -o logs/js_files.txt"
        if [ ! -z "$COOKIES" ]; then
            KATANA_JS_CMD="$KATANA_JS_CMD -H \"Cookie: $COOKIES\""
        fi
        if [ ! -z "$BEARER_TOKEN" ]; then
            KATANA_JS_CMD="$KATANA_JS_CMD -H \"Authorization: $BEARER_TOKEN\""
        fi
        if [ ! -z "$USER_AGENT" ]; then
            KATANA_JS_CMD="$KATANA_JS_CMD -H \"User-Agent: $USER_AGENT\""
        fi
        run_cmd "$KATANA_JS_CMD" "Katana JS" "katana_js"
    fi
    
    mark_step_completed "crawling"
fi

# ============================================================
# FASE 6 - JAVASCRIPT RECON
# ============================================================

if ask_step "JavaScript Recon" "LinkFinder - Extraer endpoints de JS" "js_recon"; then
    echo ""
    log_info "FASE 6 - JavaScript Recon"
    
    if [ -f "logs/js_files.txt" ] && ask_step "Extraer endpoints" "LinkFinder sobre archivos JS" "linkfinder" "true"; then
        echo "" > logs/endpoints_from_js.txt
        
        # Activar entorno virtual
        source /opt/cuackrecon/venv/bin/activate 2>/dev/null || true
        
        for js in $(cat logs/js_files.txt | grep "\.js$" | head -10); do
            log_info "Procesando JS: $js"
            
            # Usar el módulo linkfinder instalado con pip
            python3 -m linkfinder -i "$js" -o cli >> logs/endpoints_from_js.txt 2>&1
            
            sleep $REQUEST_DELAY
        done
        
        # Desactivar entorno virtual
        deactivate 2>/dev/null || true
        
        log_success "JavaScript Recon completado"
        mark_step_completed "linkfinder"
    fi
      
    mark_step_completed "js_recon"
fi


# ============================================================
# FASE 7 - ENUMERACIÓN
# ============================================================

if ask_step "Enumeración" "Cuacktest + FFUF - Enumeración de directorios y parámetros" "enumeration"; then
    echo ""
    log_info "FASE 7 - Enumeración"
    
    if ask_step "Cuacktest" "Escaneo personalizado con autenticación" "cuacktest" "true"; then
        CUACKTEST_CMD="python cuacktest.py $TARGET_URL -w $WORDLIST_SELF -v -r $REQUEST_DELAY"
        if [ ! -z "$COOKIES" ]; then
            CUACKTEST_CMD="$CUACKTEST_CMD -c \"$COOKIES\""
        fi
        if [ ! -z "$BEARER_TOKEN" ]; then
            CUACKTEST_CMD="$CUACKTEST_CMD -a \"$BEARER_TOKEN\""
        fi
        if [ ! -z "$USER_AGENT" ]; then
            CUACKTEST_CMD="$CUACKTEST_CMD -u \"$USER_AGENT\""
        fi
        if [ ! -z "$EXTRA_HEADERS" ]; then
            IFS=';' read -ra HEADERS_ARRAY <<< "$EXTRA_HEADERS"
            for header in "${HEADERS_ARRAY[@]}"; do
                header=$(echo "$header" | xargs)
                if [ ! -z "$header" ]; then
                    CUACKTEST_CMD="$CUACKTEST_CMD -H \"$header\""
                fi
            done
        fi
        run_cmd "$CUACKTEST_CMD" "Cuacktest" "cuacktest"
        mv scan_results*.json logs/ 2>/dev/null
        mv scan_results*.txt logs/ 2>/dev/null
    fi
    
    if ask_step "FFUF Directorios" "Fuerza bruta de directorios con ffuf" "ffuf_dirs" "true"; then
        FFUF_DIR_CMD="ffuf -w $WORDLIST_FFUF -u $TARGET_URL/FUZZ -mc 200,301,302,401,403,500 -fc 404 -fs 0 -c -t $FFUF_THREADS -rate $RATE_LIMIT -D -e .php,.html,.txt,.bak,.old,.log,.xml,.json -of json -o logs/ffuf_directories.json -timeout 5"
        if [ ! -z "$FFUF_HEADERS" ]; then
            FFUF_DIR_CMD="$FFUF_DIR_CMD $FFUF_HEADERS"
        fi
        if [ ! -z "$USER_AGENT" ]; then
            FFUF_DIR_CMD="$FFUF_DIR_CMD -H \"User-Agent: $USER_AGENT\""
        fi
        run_cmd "$FFUF_DIR_CMD" "FFUF directorios" "ffuf_dirs"
    fi
    
    if ask_step "FFUF Parámetros" "Fuerza bruta de parámetros con ffuf" "ffuf_params" "true"; then
        FFUF_PARAM_CMD="ffuf -w $PARAMATER_NAMES -u \"$TARGET_URL/?FUZZ=test\" -mc 200,301,302,401,403,500 -fc 404 -c -t $FFUF_THREADS -rate $RATE_LIMIT -of json -o logs/ffuf_parameters.json -timeout 5"
        if [ ! -z "$FFUF_HEADERS" ]; then
            FFUF_PARAM_CMD="$FFUF_PARAM_CMD $FFUF_HEADERS"
        fi
        if [ ! -z "$USER_AGENT" ]; then
            FFUF_PARAM_CMD="$FFUF_PARAM_CMD -H \"User-Agent: $USER_AGENT\""
        fi
        run_cmd "$FFUF_PARAM_CMD" "FFUF parámetros" "ffuf_params"
    fi
    
    if ask_step "Parámetros Avanzados" "Arjun - Descubrimiento de parámetros" "arjun" "true"; then
        if command -v arjun &> /dev/null; then
            run_cmd "arjun -u $TARGET_URL -w $PARAMATER_NAMES -o logs/arjun_params.txt" "Arjun" "arjun"
        else
            log_warn "Arjun no instalado. Omitiendo..."
        fi
    fi
    
    mark_step_completed "enumeration"
fi

# ============================================================
# FASE 8 - VULNERABILIDADES
# ============================================================

if ask_step "Vulnerabilidades" "Nuclei - Escaneo de vulnerabilidades" "vulnerabilities"; then
    echo ""
    log_info "FASE 8 - Escaneo de vulnerabilidades"
    
    run_nuclei() {
        local tags="$1"
        local output="$2"
        local step_key="$3"
        local cmd=""
        
        # Si es "all", usar templates completos
        if [ "$tags" = "all" ]; then
            cmd="nuclei -u $TARGET_URL -templates ~/nuclei-templates/ -jsonl -o logs/$output -rate-limit $RATE_LIMIT -severity low,medium,high,critical -timeout 10 -silent"
        else
            cmd="nuclei -u $TARGET_URL -tags $tags -jsonl -o logs/$output -rate-limit $RATE_LIMIT -timeout 10 -silent"
        fi
        
        if ask_step "Nuclei - $tags" "Ejecutar escaneo de $tags" "$step_key" "true"; then
            if [ ! -z "$COOKIES" ]; then
                cmd="$cmd -H \"Cookie: $COOKIES\""
            fi
            if [ ! -z "$BEARER_TOKEN" ]; then
                cmd="$cmd -H \"Authorization: $BEARER_TOKEN\""
            fi
            if [ ! -z "$EXTRA_HEADERS" ]; then
                IFS=';' read -ra HEADERS_ARRAY <<< "$EXTRA_HEADERS"
                for header in "${HEADERS_ARRAY[@]}"; do
                    header=$(echo "$header" | xargs)
                    if [ ! -z "$header" ]; then
                        cmd="$cmd -H \"$header\""
                    fi
                done
            fi
            if [ ! -z "$USER_AGENT" ]; then
                cmd="$cmd -H \"User-Agent: $USER_AGENT\""
            fi
            
            run_cmd "$cmd" "Nuclei - $tags" "$step_key"
        fi
    }
    
    # Escaneos específicos
    run_nuclei "tech" "nuclei_tech.json" "nuclei_tech"
    run_nuclei "exposure" "nuclei_exposure.json" "nuclei_exposure"
    run_nuclei "misconfig" "nuclei_misconfig.json" "nuclei_misconfig"
    run_nuclei "cve" "nuclei_cve.json" "nuclei_cve"
    run_nuclei "vuln" "nuclei_vuln.json" "nuclei_vuln"
    
    # Escaneo de templates completos
    if ask_step "Nuclei - full" "Escaneo completo de templates" "nuclei_full" "true"; then
        run_cmd "nuclei -u $TARGET_URL -templates ~/nuclei-templates/ -severity low,medium,high,critical -jsonl -o logs/nuclei_full.json -rate-limit $RATE_LIMIT -timeout 10 -silent" "Nuclei full scan" "nuclei_full"
    fi
    
    mark_step_completed "vulnerabilities"
fi

# ============================================================
# FASE 9 - REPORTE
# ============================================================

if ask_step "Generar reporte" "Cuackreport - Reporte consolidado" "report"; then
    echo ""
    log_info "FASE 9 - Generación de reporte"
    
    # Crear directorio para reportes
    mkdir -p reports
    
    # Variable para controlar si se generaron reportes
    REPORTS_GENERATED=false
    
    # Generar reporte principal
    if [ -f "cuackreport.py" ]; then
        log_info "Generando reporte principal con cuackreport.py..."
        if run_cmd "python cuackreport.py" "Generando reporte principal" "cuackreport"; then
            # Mover reporte a la carpeta reports si existe
            if [ -f "cuackrecon_report.md" ]; then
                mv cuackrecon_report.md reports/
                log_success "Reporte principal movido a reports/cuackrecon_report.md"
                REPORTS_GENERATED=true
            fi
        fi
    else
        log_warn "cuackreport.py no encontrado. Generando reporte básico..."
        
        # Generar reporte básico
        cat > reports/cuackrecon_report.md << EOF
# Reporte de Reconocimiento - $TARGET_DOMAIN

**Fecha:** $(date)
**Objetivo:** $TARGET_URL
**Dominio:** $TARGET_DOMAIN

## Resumen
- **Subdominios encontrados:** $(wc -l < logs/subdomains.txt 2>/dev/null || echo "0")
- **URLs históricas:** $(wc -l < logs/historical_urls.txt 2>/dev/null || echo "0")
- **Hosts activos:** $(wc -l < logs/alive.txt 2>/dev/null || echo "0")
- **Archivos JS encontrados:** $(wc -l < logs/js_files.txt 2>/dev/null || echo "0")
- **Directorios encontrados:** $(grep -c "\"status\":20[0-9]" logs/ffuf_directories.json 2>/dev/null || echo "0")

## Archivos generados
$(ls -la logs/ 2>/dev/null | grep -E "\.(txt|json)$" | awk '{print "- " $9}')

## Notas
- Rate limit utilizado: $RATE_LIMIT peticiones/segundo
- Usuario: $(whoami)
- Comando: $0 $@
EOF
        log_success "Reporte básico generado: reports/cuackrecon_report.md"
        REPORTS_GENERATED=true
    fi
    
    # Generar reporte completo (full)
    if [ -f "full_cuackreport.py" ]; then
        log_info "Generando reporte completo con full_cuackreport.py..."
        if run_cmd "python full_cuackreport.py" "Generando reporte completo" "full_cuackreport"; then
            # Buscar el reporte full generado
            if [ -f "full_cuackrecon_report.md" ]; then
                mv full_cuackrecon_report.md reports/
                log_success "Reporte completo movido a reports/full_cuackrecon_report.md"
                REPORTS_GENERATED=true
            elif [ -f "cuackrecon_full_report.md" ]; then
                mv cuackrecon_full_report.md reports/
                log_success "Reporte completo movido a reports/cuackrecon_full_report.md"
                REPORTS_GENERATED=true
            elif [ -f "full_report.md" ]; then
                mv full_report.md reports/
                log_success "Reporte completo movido a reports/full_report.md"
                REPORTS_GENERATED=true
            else
                # Buscar cualquier archivo .md que parezca un reporte completo
                for file in *_full*.md full_*.md *_report_full*.md; do
                    if [ -f "$file" ]; then
                        mv "$file" reports/
                        log_success "Reporte completo movido a reports/$file"
                        REPORTS_GENERATED=true
                        break
                    fi
                done
            fi
        fi
    else
        log_warn "full_cuackreport.py no encontrado. Omitiendo reporte completo..."
    fi
    
    # Verificar si se generaron reportes
    if [ "$REPORTS_GENERATED" = true ]; then
        log_success "Reportes generados en la carpeta reports/"
        echo ""
        echo "  Reportes generados:"
        ls -la reports/ 2>/dev/null | grep -E "\.md$" | awk '{print "    - reports/" $9}'
    else
        log_warn "No se generaron reportes. Verifica que los archivos .py existan."
    fi
    
    mark_step_completed "report"
fi

# ============================================================
# LIMPIEZA FINAL - ELIMINAR CHECKPOINT
# ============================================================

# Eliminar checkpoint al completar exitosamente
if [ -d "$CHECKPOINT_DIR" ]; then
    rm -rf "$CHECKPOINT_DIR"
    log_info "Checkpoint eliminado (escaneo completado)"
fi

# ============================================================
# RESUMEN FINAL
# ============================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           RECONOCIMIENTO COMPLETADO                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Target: $TARGET_URL"
echo "  Dominio: $TARGET_DOMAIN"
echo "  Fecha: $(date)"
echo "  Rate Limit: $RATE_LIMIT peticiones/segundo"
echo "  Autenticación: $(if [ ! -z "$COOKIES" ] || [ ! -z "$BEARER_TOKEN" ]; then echo "Configurada"; else echo "No configurada"; fi)"
echo ""
echo "  Archivos generados en logs/:"
ls -la logs/ 2>/dev/null | grep -E "\.(txt|json|md)$" | awk '{print "    - " $9}' || echo "    - No hay archivos"
echo ""
echo "  Reportes generados en reports/:"
if [ -d "reports" ] && [ ! -z "$(ls -A reports)" ]; then
    ls -la reports/ 2>/dev/null | grep -E "\.md$" | awk '{print "    - reports/" $9}'
else
    echo "    - No se generaron reportes"
fi
echo ""

# Crear backup incluyendo reportes
BACKUP_DIR="logs_${TARGET_DOMAIN}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r logs/ "$BACKUP_DIR/" 2>/dev/null

# Copiar reportes si existen
if [ -d "reports" ]; then
    cp -r reports/ "$BACKUP_DIR/"
    echo "  Reportes incluidos en backup"
fi

# Copiar reportes individuales (por si están en el directorio raíz)
for report in cuackrecon_report.md full_cuackrecon_report.md cuackrecon_full_report.md full_report.md; do
    if [ -f "$report" ]; then
        cp "$report" "$BACKUP_DIR/"
    fi
done

echo "  Backup creado en: $BACKUP_DIR"

log_success "Reconocimiento completado para $TARGET_DOMAIN"
echo "╔════════════════════════════════════════════════════════════╗"
