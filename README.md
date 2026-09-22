# 🦆 CuackRecon

**CuackRecon** is a set of web reconnaissance tools for Bug Bounty, designed to automate and optimize the asset enumeration and discovery process.

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Included Tools](#-included-tools)
- [Directory Structure](#-directory-structure)
- [Checkpoints and Resume](#-checkpoints-and-resume)
- [Configuration Examples](#-configuration-examples)
- [Contributions](#-contributions)
- [License](#-license)
- [Warnings](#-warnings)

## ✨ Features

- **Complete reconnaissance** automated with multiple tools
- **Checkpoint system** to resume interrupted scans
- **Configurable rate limiting** to avoid blocks
- **Automatic and interactive mode** for full control
- **Authentication support** (cookies, Bearer tokens, custom headers)
- **Detailed reports** in HTML and Markdown
- **Hierarchical visualization** of directories and endpoints
- **Statistical analysis** of results
- **Block detection** and automatic retries
- **Scope management** to limit scanning to specific domains

## 📁 Project Structure

```
cuackrecon/
├── cuack-recon.sh          # Main reconnaissance script
├── cuack-install.sh        # Tool and dependency installer
├── cuacktest.py            # Parallelized directory/file scanner
├── cuackreport.py          # Markdown report generator
├── full_cuackreport.py     # HTML report generator with advanced analysis
├── config.yaml             # Example configuration file
├── weblist.txt             # Default wordlist for fuzzing
├── checkpoints/            # Checkpoints directory
├── logs/                   # Logs and tool results
├── reports/                # Generated reports
└── tools/                  # Installed tools
```

## 🔧 Prerequisites

- **Operating system:** Linux (Kali Linux recommended)
- **Operating system:** Linux (Debian distribution recommended)
- **Bash** 4.0+
- **Python 3.8+**
- **Go** 1.18+
- **Base tools:** git, curl, wget, jq, nmap, whatweb

## 📦 Installation

### Automatic Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/akthanon/cuackrecon.git
cd cuackrecon

# Give execution permissions
chmod +x cuack-install.sh cuack-recon.sh

# Run the installer
./cuack-install.sh
```

The installer:
1. Installs all system dependencies
2. Creates a Python virtual environment
3. Installs the necessary Go tools
4. Downloads wordlists and templates
5. Configures the directory structure

### Manual Installation

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl wget nmap whatweb jq unzip

# Install Go tools
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/ffuf/ffuf/v2@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
go install -v github.com/tomnomnom/waybackurls@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/tomnomnom/assetfinder@latest

# Create directories
mkdir -p logs reports checkpoints
```

## ⚙️ Configuration

### Configuration File (config.yaml)

```yaml
# Target URL
target_url: "https://ejemplo.com"

# Wordlists
wordlist_self: "weblist.txt"
wordlist_ffuf: "weblist.txt"
paramater_names: "weblist.txt"

# Authentication
cookies: "session=xyz123; token=abc456"
bearer_token: "Bearer eyJhbGciOiJIUzI1NiIs..."
extra_headers: "X-Forwarded-For: 127.0.0.1"
user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Rate Limiting
rate_limit: 15  # requests per second
ffuf_threads: 30

# Scope
scope:
  - "ejemplo.com"
  - "*.ejemplo.com"
exclude:
  - "admin.ejemplo.com"
  - "test.ejemplo.com"

# Steps to run
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

### Environment Variables

```bash
export TARGET_URL="https://ejemplo.com"
export COOKIES="session=xyz123"
export BEARER_TOKEN="Bearer token123"
```

## 🚀 Usage

### Run a Full Scan

```bash
# Using configuration file
./cuack-recon.sh -c config.yaml

# Using direct URL
./cuack-recon.sh -u https://ejemplo.com -y

# With authentication
./cuack-recon.sh -u https://ejemplo.com --cookies "session=xyz123" --bearer "Bearer token123"
```

### Available Options

| Option | Description |
|--------|-------------|
| `-c, --config FILE` | Configuration file (YAML) |
| `-u, --url URL` | Target URL |
| `--cookies COOKIES` | Cookies in format `name1=value1; name2=value2` |
| `--bearer TOKEN` | Bearer authentication token |
| `--headers HEADERS` | Additional headers |
| `--wordlist FILE` | Wordlist for ffuf (default: weblist.txt) |
| `--params FILE` | Wordlist for parameters (default: weblist.txt) |
| `--user-agent UA` | Custom User-Agent |
| `--rate-limit NUM` | Requests per second (default: 15) |
| `--max-retries NUM` | Number of retries (default: 3) |
| `-v, --verbose` | Verbose mode |
| `-y, --yes` | Auto-approve authorization |
| `--resume` | Resume from the last checkpoint |
| `-h, --help` | Show help |

### Resume a Scan

```bash
# Resume from the last checkpoint
./cuack-recon.sh --resume
```

### Run Individual Tools

```bash
# Scan with cuacktest.py
python3 cuacktest.py https://ejemplo.com -w weblist.txt -r 0.5

# Generate report
python3 cuackreport.py

# Generate advanced report
python3 full_cuackreport.py
```

## 🛠️ Included Tools

### Passive Scanning
- **Subfinder**: Subdomain enumeration
- **Assetfinder**: Additional subdomain enumeration
- **Gau**: Historical URL collection
- **Waybackurls**: URLs from the Wayback Machine archive
- **WhatWeb**: Technology fingerprinting

### Active Scanning
- **Nmap**: Port and service scanning
- **HTTPX**: Live host verification
- **Katana**: Advanced web crawling
- **FFUF**: Directory and parameter fuzzing
- **Nuclei**: Vulnerability scanning

### JavaScript Analysis
- **LinkFinder**: Endpoint extraction from JS files
- **Katana JS**: JavaScript file extraction

### Custom
- **cuacktest.py**: Parallelized directory/file scanner
- **cuackreport.py**: Markdown report generator
- **full_cuackreport.py**: Advanced HTML report generator

## 📂 Directory Structure

```
cuackrecon/
├── logs/                          # Logs from all tools
│   ├── nmap.txt                   # Nmap results
│   ├── whatweb.txt                # WhatWeb results
│   ├── subdomains.txt             # Found subdomains
│   ├── historical_urls.txt        # Historical URLs
│   ├── alive.txt                  # Live hosts
│   ├── katana.txt                 # Crawling URLs
│   ├── js_files.txt               # JavaScript files
│   ├── endpoints_from_js.txt      # Extracted endpoints
│   ├── ffuf_directories.json      # FFUF directory results
│   ├── ffuf_parameters.json       # FFUF parameter results
│   ├── nuclei_*.json              # Nuclei results
│   └── scan_results*.json         # cuacktest results
├── reports/                       # Generated reports
│   ├── cuackrecon_report.md       # Markdown report
│   ├── cuackrecon_megareport.html # Advanced HTML report
│   └── cuackrecon_full_report.md  # Full report
└── checkpoints/                   # Checkpoints
    ├── last_step.txt              # Last completed step
    ├── completed_steps.txt        # Completed steps
    └── config.env                 # Saved configuration
```

## 💾 Checkpoints and Resume

The checkpoint system allows you to:
- Save progress after each step
- Resume interrupted scans (Ctrl+C)
- Avoid re-running already completed steps
- Preserve partial results

### Using Checkpoints

```bash
# Start a scan (checkpoints will be saved automatically)
./cuack-recon.sh -c config.yaml

# If interrupted (Ctrl+C), the state is saved
# To resume:
./cuack-recon.sh --resume
```

## 📝 Configuration Examples

### Basic Configuration

```yaml
target_url: "https://ejemplo.com"
rate_limit: 30
steps:
  - basic
  - report
```

### Full Configuration with Authentication

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

### Configuration for Quick Scan

```yaml
target_url: "https://ejemplo.com"
rate_limit: 100
ffuf_threads: 50
steps:
  - basic
  - active
  - report
```

## 🤝 Contributions

Contributions are welcome. Please:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## 📄 License

This project is under the MIT License. See the `LICENSE` file for more details.

## ⚠️ Warnings

- **Authorization:** Make sure you have explicit permission to scan the target.
- **Rate Limiting:** Respect the limits of the Bug Bounty program.
- **Ethical Use:** Use these tools only on systems you have authorization to test.
- **Responsibility:** The author is not responsible for misuse of these tools.

---

**🦆 CuackRecon - Automated web reconnaissance for Bug Bounty**
