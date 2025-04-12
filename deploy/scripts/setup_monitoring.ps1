# Script de configuration du monitoring - Technicia OCR
# Version: 1.0
# Date: 2 avril 2025
#
# Ce script configure le monitoring et les alertes pour le système OCR Technicia.
# Il installe et configure Prometheus, Grafana et les exporters nécessaires.

param (
    [string]$ProductionDir = "C:\Program Files\Technicia\OCRSystem",
    [string]$MonitoringDir = "C:\Technicia\Monitoring",
    [string]$GrafanaAdminUser = "admin",
    [System.Security.SecureString]$GrafanaAdminPassword = (ConvertTo-SecureString "TechniciaAdmin123!" -AsPlainText -Force),
    [string]$AlertEmailTo = "admin@technicia.com",
    [string]$AlertEmailFrom = "monitoring@technicia.com",
    [string]$SmtpServer = "smtp.technicia.com",
    [string]$SmtpPort = "587",
    [string]$SmtpUser = "",
    [System.Security.SecureString]$SmtpPassword = (ConvertTo-SecureString "" -AsPlainText -Force),
    [switch]$UseSSL
)

function Write-LogMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colorMap = @{
        "INFO" = "White";
        "WARN" = "Yellow";
        "ERROR" = "Red";
        "SUCCESS" = "Green"
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $colorMap[$Level]
}

# Vérification des droits d'administrateur
Write-LogMessage "Vérification des privilèges administrateur..."
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-LogMessage "Ce script doit être exécuté avec des privilèges administrateur." "ERROR"
    exit 1
}

# Création des répertoires nécessaires
Write-LogMessage "Création des répertoires nécessaires..."
$directories = @(
    $MonitoringDir,
    "$MonitoringDir\prometheus",
    "$MonitoringDir\prometheus\rules",
    "$MonitoringDir\grafana",
    "$MonitoringDir\grafana\dashboards",
    "$MonitoringDir\grafana\provisioning",
    "$MonitoringDir\grafana\provisioning\datasources",
    "$MonitoringDir\grafana\provisioning\dashboards",
    "$MonitoringDir\exporters",
    "$MonitoringDir\logs"
)

foreach ($dir in $directories) {
    if (-not (Test-Path -Path $dir -PathType Container)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-LogMessage "Répertoire créé: $dir"
    }
}

# Téléchargement et installation de Prometheus
Write-LogMessage "Configuration de Prometheus..."
$prometheusUrl = "https://github.com/prometheus/prometheus/releases/download/v2.37.0/prometheus-2.37.0.windows-amd64.zip"
$prometheusZip = "$env:TEMP\prometheus.zip"
$prometheusDir = "$MonitoringDir\prometheus"

if (-not (Test-Path -Path "$prometheusDir\prometheus.exe" -PathType Leaf)) {
    Write-LogMessage "Téléchargement de Prometheus..."
    Invoke-WebRequest -Uri $prometheusUrl -OutFile $prometheusZip
    
    Write-LogMessage "Extraction de Prometheus..."
    Expand-Archive -Path $prometheusZip -DestinationPath $env:TEMP -Force
    $extractedDir = Get-ChildItem -Path $env:TEMP -Directory -Filter "prometheus-*" | Select-Object -First 1
    
    # Copie des fichiers
    Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $prometheusDir -Recurse -Force
    
    # Nettoyage
    Remove-Item -Path $prometheusZip -Force
    Remove-Item -Path $extractedDir.FullName -Recurse -Force
}

# Configuration de Prometheus
Write-LogMessage "Création du fichier de configuration Prometheus..."
$prometheusConfig = @"
# Configuration Prometheus pour le système OCR Technicia
# Généré automatiquement par setup_monitoring.ps1

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

# Règles d'alertes
rule_files:
  - "rules/alerts.yml"

# Configuration d'Alertmanager
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - "localhost:9093"

# Configurations des cibles de scraping
scrape_configs:
  # Prometheus lui-même
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
  
  # Node Exporter (métriques système)
  - job_name: "node"
    static_configs:
      - targets: ["localhost:9100"]
  
  # Windows Exporter (métriques Windows)
  - job_name: "windows"
    static_configs:
      - targets: ["localhost:9182"]
  
  # PostgreSQL Exporter
  - job_name: "postgresql"
    static_configs:
      - targets: ["localhost:9187"]
  
  # Application OCR Technicia
  - job_name: "technicia-ocr"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["localhost:5000"]

  # Redis Exporter
  - job_name: "redis"
    static_configs:
      - targets: ["localhost:9121"]
"@

$prometheusConfig | Set-Content -Path "$prometheusDir\prometheus.yml" -Force

# Création des règles d'alerte
Write-LogMessage "Création des règles d'alerte Prometheus..."
$alertRules = @"
# Règles d'alerte pour le système OCR Technicia
# Généré automatiquement par setup_monitoring.ps1

groups:
- name: ocr_system_alerts
  rules:
  # Alerte pour un taux d'erreur élevé dans le traitement OCR
  - alert: OCRHighErrorRate
    expr: rate(ocr_processing_errors_total[5m]) / rate(ocr_documents_processed_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Taux d'erreur OCR élevé"
      description: "Le taux d'erreur OCR est supérieur à 10% depuis 5 minutes."

  # Alerte pour un temps de traitement anormalement long
  - alert: OCRSlowProcessing
    expr: avg_over_time(ocr_document_processing_duration_seconds[15m]) > 60
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "Traitement OCR lent"
      description: "Le temps moyen de traitement des documents est supérieur à 60 secondes depuis 15 minutes."

  # Alerte pour une file d'attente qui s'accumule
  - alert: OCRQueueBacklog
    expr: ocr_queue_length > 50
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Backlog important dans la file OCR"
      description: "Plus de 50 documents sont en attente de traitement depuis 10 minutes."

  # Alerte pour une utilisation CPU élevée
  - alert: HighCPUUsage
    expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Utilisation CPU élevée"
      description: "L'utilisation CPU est supérieure à 85% depuis 10 minutes."

  # Alerte pour une utilisation mémoire élevée
  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 90
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Utilisation mémoire élevée"
      description: "L'utilisation de la mémoire est supérieure à 90% depuis 10 minutes."

  # Alerte pour un espace disque faible
  - alert: LowDiskSpace
    expr: node_filesystem_avail_bytes{mountpoint="C:"} / node_filesystem_size_bytes{mountpoint="C:"} * 100 < 10
    for: 15m
    labels:
      severity: critical
    annotations:
      summary: "Espace disque faible"
      description: "Il reste moins de 10% d'espace disque libre sur le volume C: depuis 15 minutes."

  # Alerte pour une instance PostgreSQL non disponible
  - alert: PostgreSQLDown
    expr: pg_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "PostgreSQL inaccessible"
      description: "L'instance PostgreSQL est inaccessible depuis 1 minute."

  # Alerte pour une instance Redis non disponible
  - alert: RedisDown
    expr: redis_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Redis inaccessible"
      description: "L'instance Redis est inaccessible depuis 1 minute."
"@

New-Item -Path "$prometheusDir\rules" -ItemType Directory -Force | Out-Null
$alertRules | Set-Content -Path "$prometheusDir\rules\alerts.yml" -Force

# Téléchargement et installation de Grafana
Write-LogMessage "Configuration de Grafana..."
$grafanaUrl = "https://dl.grafana.com/oss/release/grafana-9.3.0.windows-amd64.zip"
$grafanaZip = "$env:TEMP\grafana.zip"
$grafanaDir = "$MonitoringDir\grafana"

if (-not (Test-Path -Path "$grafanaDir\bin\grafana-server.exe" -PathType Leaf)) {
    Write-LogMessage "Téléchargement de Grafana..."
    Invoke-WebRequest -Uri $grafanaUrl -OutFile $grafanaZip
    
    Write-LogMessage "Extraction de Grafana..."
    Expand-Archive -Path $grafanaZip -DestinationPath $env:TEMP -Force
    $extractedDir = Get-ChildItem -Path $env:TEMP -Directory -Filter "grafana-*" | Select-Object -First 1
    
    # Copie des fichiers
    Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $grafanaDir -Recurse -Force
    
    # Nettoyage
    Remove-Item -Path $grafanaZip -Force
    Remove-Item -Path $extractedDir.FullName -Recurse -Force
}

# Configuration de Grafana
Write-LogMessage "Création de la configuration Grafana..."
$grafanaIni = @"
# Configuration Grafana pour le système OCR Technicia
# Généré automatiquement par setup_monitoring.ps1

[server]
http_port = 3000
domain = localhost
root_url = http://localhost:3000/

[database]
type = sqlite3
path = $grafanaDir/data/grafana.db

[security]
admin_user = $GrafanaAdminUser
admin_password = $($GrafanaAdminPassword | ConvertFrom-SecureString -AsPlainText)

[auth.anonymous]
enabled = false

[log]
mode = file console
level = info
filters = 
"@

$grafanaIni | Set-Content -Path "$grafanaDir\conf\custom.ini" -Force

# Configuration des sources de données Grafana
Write-LogMessage "Configuration des sources de données Grafana..."
$datasourceProvisioning = @"
# Configuration des sources de données Grafana pour le système OCR Technicia
# Généré automatiquement par setup_monitoring.ps1

apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: POST
"@

$datasourceProvisioning | Set-Content -Path "$grafanaDir\provisioning\datasources\prometheus.yml" -Force

# Configuration des tableaux de bord Grafana
Write-LogMessage "Configuration des tableaux de bord Grafana..."
$dashboardProvisioning = @"
# Configuration des tableaux de bord Grafana pour le système OCR Technicia
# Généré automatiquement par setup_monitoring.ps1

apiVersion: 1

providers:
  - name: 'TechniciaOCR'
    orgId: 1
    folder: 'Technicia'
    type: file
    disableDeletion: true
    editable: false
    updateIntervalSeconds: 30
    allowUiUpdates: false
    options:
      path: $grafanaDir/dashboards
"@

$dashboardProvisioning | Set-Content -Path "$grafanaDir\provisioning\dashboards\technicia.yml" -Force

# Création d'un tableau de bord pour le système OCR
Write-LogMessage "Création du tableau de bord OCR principal..."
$ocrDashboard = @'
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "title": "Taux de traitement OCR",
      "type": "timeseries",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "rate(ocr_documents_processed_total[5m])",
          "refId": "A",
          "legendFormat": "Documents traités/min"
        }
      ]
    },
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "title": "Temps de traitement moyen",
      "type": "gauge",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "avg_over_time(ocr_document_processing_duration_seconds[5m])",
          "refId": "A"
        }
      ],
      "options": {
        "maxValue": 120,
        "minValue": 0,
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "green", "value": null },
            { "color": "yellow", "value": 30 },
            { "color": "red", "value": 60 }
          ]
        }
      }
    },
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "title": "Taille de la file d'attente",
      "type": "stat",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "ocr_queue_length",
          "refId": "A"
        }
      ]
    },
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "id": 4,
      "title": "Qualité OCR moyenne",
      "type": "gauge",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "avg(ocr_quality_score) * 100",
          "refId": "A"
        }
      ],
      "options": {
        "maxValue": 100,
        "minValue": 0,
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "red", "value": null },
            { "color": "yellow", "value": 75 },
            { "color": "green", "value": 90 }
          ]
        }
      }
    },
    {
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 16
      },
      "id": 5,
      "title": "Erreurs de traitement",
      "type": "timeseries",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "rate(ocr_processing_errors_total[5m])",
          "refId": "A",
          "legendFormat": "Erreurs/min"
        }
      ]
    }
  ],
  "refresh": "10s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["technicia", "ocr"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "title": "Technicia OCR - Vue d'ensemble",
  "uid": "technicia-ocr-overview",
  "version": 1
}
'@

$ocrDashboard | Set-Content -Path "$grafanaDir\dashboards\ocr-overview.json" -Force

# Création d'un tableau de bord pour le système et ressources
Write-LogMessage "Création du tableau de bord système..."
$systemDashboard = @'
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "title": "Utilisation CPU",
      "type": "timeseries",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
          "refId": "A",
          "legendFormat": "% CPU"
        }
      ]
    },
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "title": "Utilisation mémoire",
      "type": "timeseries",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100",
          "refId": "A",
          "legendFormat": "% Mémoire"
        }
      ]
    },
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "title": "Espace disque disponible",
      "type": "gauge",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "node_filesystem_avail_bytes{mountpoint=\"C:\"} / node_filesystem_size_bytes{mountpoint=\"C:\"} * 100",
          "refId": "A"
        }
      ],
      "options": {
        "maxValue": 100,
        "minValue": 0,
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "red", "value": null },
            { "color": "yellow", "value": 10 },
            { "color": "green", "value": 20 }
          ]
        }
      }
    },
    {
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "id": 4,
      "title": "I/O Disque",
      "type": "timeseries",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "rate(node_disk_read_bytes_total{device=\"C:\"}[5m])",
          "refId": "A",
          "legendFormat": "Lecture"
        },
        {
          "expr": "rate(node_disk_written_bytes_total{device=\"C:\"}[5m])",
          "refId": "B",
          "legendFormat": "Écriture"
        }
      ]
    }
  ],
  "refresh": "10s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["technicia", "system"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "title": "Technicia OCR - Ressources système",
  "uid": "technicia-system",
  "version": 1
}
'@

$systemDashboard | Set-Content -Path "$grafanaDir\dashboards\system-overview.json" -Force

# Téléchargement et installation des exporters
Write-LogMessage "Installation des exporters..."
$exportersDir = "$MonitoringDir\exporters"

# Windows Exporter
Write-LogMessage "Installation de Windows Exporter..."
$windowsExporterUrl = "https://github.com/prometheus-community/windows_exporter/releases/download/v0.20.0/windows_exporter-0.20.0-amd64.msi"
$windowsExporterMsi = "$env:TEMP\windows_exporter.msi"

if (-not (Get-Service -Name "windows_exporter" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "Téléchargement de Windows Exporter..."
    Invoke-WebRequest -Uri $windowsExporterUrl -OutFile $windowsExporterMsi
    
    Write-LogMessage "Installation de Windows Exporter..."
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $windowsExporterMsi, "/qn" -Wait
    
    # Nettoyage
    Remove-Item -Path $windowsExporterMsi -Force
}

# PostgreSQL Exporter
Write-LogMessage "Configuration de PostgreSQL Exporter..."
$postgresExporterUrl = "https://github.com/prometheus-community/postgres_exporter/releases/download/v0.11.1/postgres_exporter-0.11.1.windows-amd64.zip"
$postgresExporterZip = "$env:TEMP\postgres_exporter.zip"
$postgresExporterDir = "$exportersDir\postgres_exporter"

if (-not (Test-Path -Path "$postgresExporterDir\postgres_exporter.exe" -PathType Leaf)) {
    Write-LogMessage "Téléchargement de PostgreSQL Exporter..."
    New-Item -Path $postgresExporterDir -ItemType Directory -Force | Out-Null
    Invoke-WebRequest -Uri $postgresExporterUrl -OutFile $postgresExporterZip
    
    Write-LogMessage "Extraction de PostgreSQL Exporter..."
    Expand-Archive -Path $postgresExporterZip -DestinationPath $env:TEMP -Force
    $extractedDir = Get-ChildItem -Path $env:TEMP -Directory -Filter "postgres_exporter-*" | Select-Object -First 1
    
    # Copie des fichiers
    Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $postgresExporterDir -Recurse -Force
    
    # Nettoyage
    Remove-Item -Path $postgresExporterZip -Force
    Remove-Item -Path $extractedDir.FullName -Recurse -Force
    
    # Configuration
    $pgConfig = @"
DATA_SOURCE_NAME="postgresql://technicia:securepassword@localhost:5432/ocr_db?sslmode=disable"
"@
    $pgConfig | Set-Content -Path "$postgresExporterDir\.env" -Force
}

# Redis Exporter
Write-LogMessage "Configuration de Redis Exporter..."
$redisExporterUrl = "https://github.com/oliver006/redis_exporter/releases/download/v1.45.0/redis_exporter-v1.45.0.windows-amd64.zip"
$redisExporterZip = "$env:TEMP\redis_exporter.zip"
$redisExporterDir = "$exportersDir\redis_exporter"

if (-not (Test-Path -Path "$redisExporterDir\redis_exporter.exe" -PathType Leaf)) {
    Write-LogMessage "Téléchargement de Redis Exporter..."
    New-Item -Path $redisExporterDir -ItemType Directory -Force | Out-Null
    Invoke-WebRequest -Uri $redisExporterUrl -OutFile $redisExporterZip
    
    Write-LogMessage "Extraction de Redis Exporter..."
    Expand-Archive -Path $redisExporterZip -DestinationPath $env:TEMP -Force
    $extractedDir = Get-ChildItem -Path $env:TEMP -Directory -Filter "redis_exporter-*" | Select-Object -First 1
    
    # Copie des fichiers
    Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $redisExporterDir -Recurse -Force
    
    # Nettoyage
    Remove-Item -Path $redisExporterZip -Force
    Remove-Item -Path $extractedDir.FullName -Recurse -Force
}

# Configuration d'AlertManager
Write-LogMessage "Configuration d'AlertManager..."
$alertManagerUrl = "https://github.com/prometheus/alertmanager/releases/download/v0.24.0/alertmanager-0.24.0.windows-amd64.zip"
$alertManagerZip = "$env:TEMP\alertmanager.zip"
$alertManagerDir = "$MonitoringDir\alertmanager"

if (-not (Test-Path -Path "$alertManagerDir\alertmanager.exe" -PathType Leaf)) {
    Write-LogMessage "Téléchargement d'AlertManager..."
    New-Item -Path $alertManagerDir -ItemType Directory -Force | Out-Null
    Invoke-WebRequest -Uri $alertManagerUrl -OutFile $alertManagerZip
    
    Write-LogMessage "Extraction d'AlertManager..."
    Expand-Archive -Path $alertManagerZip -DestinationPath $env:TEMP -Force
    $extractedDir = Get-ChildItem -Path $env:TEMP -Directory -Filter "alertmanager-*" | Select-Object -First 1
    
    # Copie des fichiers
    Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $alertManagerDir -Recurse -Force
    
    # Nettoyage
    Remove-Item -Path $alertManagerZip -Force
    Remove-Item -Path $extractedDir.FullName -Recurse -Force
    
    # Construction du chemin complet avec le port spécifié
    $smtpHostPortString = "$SmtpServer`:$SmtpPort"
    
    # Configuration
    $alertManagerConfig = @"
# Configuration AlertManager pour le système OCR Technicia
# Généré automatiquement par setup_monitoring.ps1

global:
  resolve_timeout: 5m
  smtp_from: '$AlertEmailFrom'
  smtp_smarthost: '$smtpHostPortString'
  smtp_auth_username: '$SmtpUser'
  smtp_auth_password: $($SmtpPassword | ConvertFrom-SecureString -AsPlainText)
  smtp_require_tls: $($UseSSL.ToString().ToLower())

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'email-notifications'

receivers:
- name: 'email-notifications'
  email_configs:
  - to: '$AlertEmailTo'
    send_resolved: true
    headers:
      subject: '[ALERTE] Système OCR Technicia: {{ .GroupLabels.alertname }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
"@
    $alertManagerConfig | Set-Content -Path "$alertManagerDir\alertmanager.yml" -Force
}

# Création des services Windows
Write-LogMessage "Création des services Windows pour le monitoring..."

# Vérification de NSSM (Non-Sucking Service Manager)
if (-not (Get-Command -Name "nssm" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "NSSM n'est pas installé. Téléchargement et installation..."
    
    # Téléchargement de NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm-2.24.zip"
    $nssmExtractDir = "$env:TEMP\nssm-2.24"
    
    Write-LogMessage "Téléchargement de NSSM..."
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
    
    # Extraction de NSSM
    Write-LogMessage "Extraction de NSSM..."
    Expand-Archive -Path $nssmZip -DestinationPath $nssmExtractDir -Force
    
    # Copie de NSSM dans le répertoire système
    $nssmExe = Get-ChildItem -Path $nssmExtractDir -Recurse -Filter "nssm.exe" | Where-Object { $_.DirectoryName -like "*win64*" } | Select-Object -First 1
    Copy-Item -Path $nssmExe.FullName -Destination "C:\Windows\System32\" -Force
    
    # Nettoyage
    Remove-Item -Path $nssmZip -Force
    Remove-Item -Path $nssmExtractDir -Recurse -Force
}

# Service Prometheus
if (-not (Get-Service -Name "TechniciaPrometheus" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "Création du service Prometheus..."
    & nssm install "TechniciaPrometheus" "$prometheusDir\prometheus.exe" "--config.file=`"$prometheusDir\prometheus.yml`" --storage.tsdb.path=`"$prometheusDir\data`""
    & nssm set "TechniciaPrometheus" AppDirectory "$prometheusDir"
    & nssm set "TechniciaPrometheus" DisplayName "Technicia OCR - Prometheus"
    & nssm set "TechniciaPrometheus" Description "Service Prometheus pour le monitoring du système OCR Technicia"
    & nssm set "TechniciaPrometheus" Start SERVICE_AUTO_START
    & nssm set "TechniciaPrometheus" AppStdout "$MonitoringDir\logs\prometheus_stdout.log"
    & nssm set "TechniciaPrometheus" AppStderr "$MonitoringDir\logs\prometheus_stderr.log"
}

# Service Grafana
if (-not (Get-Service -Name "TechniciaGrafana" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "Création du service Grafana..."
    & nssm install "TechniciaGrafana" "$grafanaDir\bin\grafana-server.exe" "--config=`"$grafanaDir\conf\custom.ini`" --homepath=`"$grafanaDir`""
    & nssm set "TechniciaGrafana" AppDirectory "$grafanaDir\bin"
    & nssm set "TechniciaGrafana" DisplayName "Technicia OCR - Grafana"
    & nssm set "TechniciaGrafana" Description "Service Grafana pour le monitoring du système OCR Technicia"
    & nssm set "TechniciaGrafana" Start SERVICE_AUTO_START
    & nssm set "TechniciaGrafana" AppStdout "$MonitoringDir\logs\grafana_stdout.log"
    & nssm set "TechniciaGrafana" AppStderr "$MonitoringDir\logs\grafana_stderr.log"
}

# Service PostgreSQL Exporter
if (-not (Get-Service -Name "TechniciaPostgreSQLExporter" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "Création du service PostgreSQL Exporter..."
    & nssm install "TechniciaPostgreSQLExporter" "$postgresExporterDir\postgres_exporter.exe"
    & nssm set "TechniciaPostgreSQLExporter" AppDirectory "$postgresExporterDir"
    & nssm set "TechniciaPostgreSQLExporter" DisplayName "Technicia OCR - PostgreSQL Exporter"
    & nssm set "TechniciaPostgreSQLExporter" Description "Service PostgreSQL Exporter pour le monitoring du système OCR Technicia"
    & nssm set "TechniciaPostgreSQLExporter" Start SERVICE_AUTO_START
    & nssm set "TechniciaPostgreSQLExporter" AppStdout "$MonitoringDir\logs\postgres_exporter_stdout.log"
    & nssm set "TechniciaPostgreSQLExporter" AppStderr "$MonitoringDir\logs\postgres_exporter_stderr.log"
    & nssm set "TechniciaPostgreSQLExporter" AppEnvironmentExtra "DATA_SOURCE_NAME=postgresql://technicia:securepassword@localhost:5432/ocr_db?sslmode=disable"
}

# Service Redis Exporter
if (-not (Get-Service -Name "TechniciaRedisExporter" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "Création du service Redis Exporter..."
    & nssm install "TechniciaRedisExporter" "$redisExporterDir\redis_exporter.exe" "--redis.addr=localhost:6379"
    & nssm set "TechniciaRedisExporter" AppDirectory "$redisExporterDir"
    & nssm set "TechniciaRedisExporter" DisplayName "Technicia OCR - Redis Exporter"
    & nssm set "TechniciaRedisExporter" Description "Service Redis Exporter pour le monitoring du système OCR Technicia"
    & nssm set "TechniciaRedisExporter" Start SERVICE_AUTO_START
    & nssm set "TechniciaRedisExporter" AppStdout "$MonitoringDir\logs\redis_exporter_stdout.log"
    & nssm set "TechniciaRedisExporter" AppStderr "$MonitoringDir\logs\redis_exporter_stderr.log"
}

# Service AlertManager
if (-not (Get-Service -Name "TechniciaAlertManager" -ErrorAction SilentlyContinue)) {
    Write-LogMessage "Création du service AlertManager..."
    & nssm install "TechniciaAlertManager" "$alertManagerDir\alertmanager.exe" "--config.file=`"$alertManagerDir\alertmanager.yml`" --storage.path=`"$alertManagerDir\data`""
    & nssm set "TechniciaAlertManager" AppDirectory "$alertManagerDir"
    & nssm set "TechniciaAlertManager" DisplayName "Technicia OCR - AlertManager"
    & nssm set "TechniciaAlertManager" Description "Service AlertManager pour les alertes du système OCR Technicia"
    & nssm set "TechniciaAlertManager" Start SERVICE_AUTO_START
    & nssm set "TechniciaAlertManager" AppStdout "$MonitoringDir\logs\alertmanager_stdout.log"
    & nssm set "TechniciaAlertManager" AppStderr "$MonitoringDir\logs\alertmanager_stderr.log"
}

# Démarrage des services
Write-LogMessage "Démarrage des services de monitoring..."
$monitoringServices = @(
    "TechniciaPrometheus",
    "TechniciaGrafana",
    "TechniciaPostgreSQLExporter",
    "TechniciaRedisExporter",
    "TechniciaAlertManager"
)

foreach ($service in $monitoringServices) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        Start-Service -Name $service
        Write-LogMessage "Service $service démarré."
    }
}

Write-LogMessage "Configuration du monitoring terminée avec succès !" "SUCCESS"
Write-LogMessage ""
Write-LogMessage "Informations importantes:"
Write-LogMessage " - Prometheus: http://localhost:9090"
Write-LogMessage " - Grafana: http://localhost:3000 (login: $GrafanaAdminUser / $($GrafanaAdminPassword | ConvertFrom-SecureString -AsPlainText))"
Write-LogMessage " - AlertManager: http://localhost:9093"
Write-LogMessage ""
Write-LogMessage "Tableaux de bord disponibles dans Grafana:"
Write-LogMessage " - Technicia OCR - Vue d'ensemble"
Write-LogMessage " - Technicia OCR - Ressources système"
Write-LogMessage ""
Write-LogMessage "Alertes configurées pour envoyer des notifications à: $AlertEmailTo"
