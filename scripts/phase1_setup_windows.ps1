# Windows Setup Script for AI Chat Assistant

# Configuration
$VENV_NAME = "llm_agent_env"
$ENV_FILE = ".env"
$MIN_PYTHON_VERSION = "3.9.0"

# Verify Python installation
Write-Host "Verifying Python installation..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python 3 is required but not found"
    Write-Host "Please install Python 3.9 or higher from:"
    Write-Host "https://www.python.org/downloads/"
    exit 1
}

# Verify Python version
Write-Host "Verifying Python version..."
$pythonVersion = (python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
if ([version]$pythonVersion -lt [version]$MIN_PYTHON_VERSION) {
    Write-Host "Error: Python $MIN_PYTHON_VERSION or higher required (found $pythonVersion)"
    Write-Host "Please upgrade your Python installation from:"
    Write-Host "https://www.python.org/downloads/"
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..."
python -m venv $VENV_NAME
if (-not $?) {
    Write-Host "Failed to create virtual environment"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
. "$VENV_NAME\Scripts\Activate.ps1"
if (-not $?) {
    Write-Host "Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
Write-Host "Upgrading pip..."
python -m pip install --upgrade pip
if (-not $?) {
    Write-Host "Failed to upgrade pip"
    exit 1
}

# Install requirements
Write-Host "Installing required packages..."
pip install -r requirements.txt
if (-not $?) {
    Write-Host "Failed to install packages"
    exit 1
}

# Configure environment variables
Write-Host "Configuring environment variables..."
if (-not (Test-Path $ENV_FILE)) {
    @"
# API Keys
# Model Configurations
# Fallback Order
"@ | Out-File $ENV_FILE
}

# API Key Validation Function
function Validate-APIKey {
    param (
        [string]$key
    )
    Write-Host "Validating API key: $($key.Substring(0, [math]::Min(8, $key.Length)))..."
    
    # OpenAI key validation
    if ($key.StartsWith("sk-proj")) {
        try {
            $response = python -c @"
from openai import OpenAI
try:
    client = OpenAI(api_key='$key')
    models = client.models.list()
    print('valid')
except Exception as e:
    print('invalid')
"@
            return $response -eq 'valid'
        } catch {
            return $false
        }
    }
    
    # General key validation
    return $key.Length -gt 30 -and $key -match '^[a-zA-Z0-9_-]+$'
}

# Configure API keys
$apiKeys = @(
    @{Name="OPENAI_API_KEY"; Description="OpenAI (Required)"},
    @{Name="ANTHROPIC_API_KEY"; Description="Anthropic (Optional)"},
    @{Name="COHERE_API_KEY"; Description="Cohere (Optional)"}
)

foreach ($apiKey in $apiKeys) {
    $currentValue = Get-Content $ENV_FILE | Select-String "^$($apiKey.Name)="
    
    if ($currentValue -and -not $currentValue.ToString().Contains("your-")) {
        Write-Host "$($apiKey.Description) API key already configured [masked]"
        continue
    }
    
    while ($true) {
        $key = Read-Host "Enter your $($apiKey.Description) API key (or press Enter to skip)"
        
        if ([string]::IsNullOrEmpty($key)) {
            Write-Host "Skipping $($apiKey.Description) configuration"
            break
        }
        
        if (Validate-APIKey $key) {
            Add-Content -Path $ENV_FILE -Value "$($apiKey.Name)=$key"
            Write-Host "$($apiKey.Description) API key saved."
            break
        } else {
            Write-Host "Invalid API key format. Please enter a valid key or press Enter to skip."
        }
    }
}

# Add default configurations
$configDefaults = @(
    "DEFAULT_PROVIDER=openai",
    "OPENAI_MODEL=gpt-4o",
    "ANTHROPIC_MODEL=claude-3-opus",
    "COHERE_MODEL=command-r-plus",
    "MAX_TOKENS=1000",
    "LOG_LEVEL=INFO",
    "FALLBACK_ORDER=openai,anthropic,cohere"
)

foreach ($config in $configDefaults) {
    if (-not (Get-Content $ENV_FILE | Select-String "^$($config.Split('=')[0])=")) {
        Add-Content -Path $ENV_FILE -Value $config
    }
}

# Verify at least one API key is configured
$configuredKeys = Get-Content $ENV_FILE | Select-String '^(OPENAI|ANTHROPIC|COHERE)_API_KEY=' | Measure-Object | Select-Object -ExpandProperty Count
if ($configuredKeys -eq 0) {
    Write-Host "Error: No API keys configured. At least one API key is required."
    Write-Host "Please configure at least one provider in the .env file"
    exit 1
}

Write-Host ""
Write-Host "Setup completed successfully!"
Write-Host ""
Write-Host "To run the application:"
Write-Host "1. Activate the virtual environment:"
Write-Host "   .\$VENV_NAME\Scripts\Activate.ps1"
Write-Host "2. Verify the installation:"
Write-Host "   pip list"
Write-Host "3. Run the chat application:"
Write-Host "   python src\chat.py"
Write-Host ""
Write-Host "To deactivate the virtual environment when done:"
Write-Host "   deactivate"