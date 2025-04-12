# Module de journalisation pour la préparation de l'environnement de staging
# Version: 1.0
# Date: 7 avril 2025
#
# Ce module fournit des fonctions de journalisation pour le script de préparation
# de l'environnement de staging du système OCR Technicia.

<#
.SYNOPSIS
    Écrit un message dans le fichier de log et dans la console.

.DESCRIPTION
    Cette fonction permet d'écrire des messages formatés dans le fichier de log
    et dans la console avec différents niveaux de sévérité (INFO, WARN, ERROR, SUCCESS).

.PARAMETER Message
    Le message à journaliser.

.PARAMETER Level
    Le niveau de sévérité du message (INFO, WARN, ERROR, SUCCESS).
    Par défaut: INFO.

.EXAMPLE
    Write-LogMessage "Démarrage de l'installation" "INFO"
    Write-LogMessage "Opération réussie" "SUCCESS"
    Write-LogMessage "Configuration incomplète" "WARN"
    Write-LogMessage "Échec de l'opération" "ERROR"
#>
function Write-LogMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Définir les couleurs pour chaque niveau
    $colorMap = @{
        "INFO" = "White";
        "WARN" = "Yellow";
        "ERROR" = "Red";
        "SUCCESS" = "Green"
    }
    
    # Écrire dans la console avec la couleur appropriée
    Write-Host $logMessage -ForegroundColor $colorMap[$Level]
    
    # Écrire dans le fichier log
    if ($global:logFile) {
        Add-Content -Path $global:logFile -Value $logMessage
    }
}

<#
.SYNOPSIS
    Commence une section de log avec un titre.

.DESCRIPTION
    Cette fonction permet de créer une section visuelle dans les logs
    pour améliorer la lisibilité.

.PARAMETER Title
    Le titre de la section.

.EXAMPLE
    Start-LogSection "Installation des dépendances"
#>
function Start-LogSection {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Title
    )
    
    $separator = "=" * 80
    Write-LogMessage $separator "INFO"
    Write-LogMessage "= $Title" "INFO"
    Write-LogMessage $separator "INFO"
}

<#
.SYNOPSIS
    Termine une section de log.

.DESCRIPTION
    Cette fonction permet de terminer visuellement une section dans les logs.

.EXAMPLE
    Stop-LogSection
#>
function Stop-LogSection {
    $separator = "-" * 80
    Write-LogMessage $separator "INFO"
}

<#
.SYNOPSIS
    Journalise le début d'une tâche.

.DESCRIPTION
    Cette fonction permet de journaliser le début d'une tâche spécifique,
    avec un suivi de progression.

.PARAMETER TaskName
    Le nom de la tâche.

.EXAMPLE
    Start-LogTask "Installation de PostgreSQL"
#>
function Start-LogTask {
    param (
        [Parameter(Mandatory=$true)]
        [string]$TaskName
    )
    
    Write-LogMessage "Début de la tâche: $TaskName..." "INFO"
}

<#
.SYNOPSIS
    Journalise la fin d'une tâche.

.DESCRIPTION
    Cette fonction permet de journaliser la fin d'une tâche spécifique,
    avec un indicateur de succès ou d'échec.

.PARAMETER TaskName
    Le nom de la tâche.

.PARAMETER Success
    Indique si la tâche s'est terminée avec succès.
    Par défaut: $true.

.PARAMETER ErrorMessage
    Message d'erreur en cas d'échec de la tâche.
    Par défaut: $null.

.EXAMPLE
    Complete-LogTask "Installation de PostgreSQL" $true
    Complete-LogTask "Installation de Redis" $false "Échec de la connexion au service"
#>
function Complete-LogTask {
    param (
        [Parameter(Mandatory=$true)]
        [string]$TaskName,
        
        [Parameter(Mandatory=$false)]
        [bool]$Success = $true,
        
        [Parameter(Mandatory=$false)]
        [string]$ErrorMessage = $null
    )
    
    if ($Success) {
        Write-LogMessage "Tâche terminée: $TaskName" "SUCCESS"
    }
    else {
        Write-LogMessage "Échec de la tâche: $TaskName" "ERROR"
        if ($ErrorMessage) {
            Write-LogMessage "Détails de l'erreur: $ErrorMessage" "ERROR"
        }
    }
}

<#
.SYNOPSIS
    Journalise une exception avec des informations détaillées.

.DESCRIPTION
    Cette fonction permet de journaliser une exception avec des informations
    détaillées pour faciliter le débogage.

.PARAMETER Exception
    L'objet exception à journaliser.

.PARAMETER Context
    Contexte dans lequel l'exception s'est produite.

.EXAMPLE
    Write-ExceptionLog $_ "Installation de PostgreSQL"
#>
function Write-ExceptionLog {
    param (
        [Parameter(Mandatory=$true)]
        [System.Exception]$Exception,
        
        [Parameter(Mandatory=$false)]
        [string]$Context = "Opération inconnue"
    )
    
    Write-LogMessage "Exception dans '$Context': $($Exception.Message)" "ERROR"
    Write-LogMessage "Type d'exception: $($Exception.GetType().FullName)" "ERROR"
    
    if ($Exception.InnerException) {
        Write-LogMessage "Exception interne: $($Exception.InnerException.Message)" "ERROR"
    }
    
    Write-LogMessage "Stack trace: $($Exception.ScriptStackTrace)" "ERROR"
}

# Rendre les fonctions disponibles pour les autres scripts
# Cette approche est plus compatible avec le dot-sourcing
$global:Write_LogMessage = ${function:Write-LogMessage}
$global:Start_LogSection = ${function:Start-LogSection}
$global:Stop_LogSection = ${function:Stop-LogSection}
$global:Start_LogTask = ${function:Start-LogTask}
$global:Complete_LogTask = ${function:Complete-LogTask}
$global:Write_ExceptionLog = ${function:Write-ExceptionLog}
