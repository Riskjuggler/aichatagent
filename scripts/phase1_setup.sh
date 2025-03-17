#!/bin/bash

# Configuration
VENV_NAME="llm_agent_env"
ENV_FILE=".env"

# Required Python version
MIN_PYTHON_VERSION="3.9.0"

# Function to compare Python versions
version_compare() {
    local version1=$1
    local version2=$2
    if [[ "$(printf '%s\n' "$version1" "$version2" | sort -V | head -n1)" == "$version1" ]]; then
        return 0
    else
        return 1
    fi
}

# Verify Python installation
echo "Verifying Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    echo "Please install Python 3.9 or higher:"
    echo "  macOS: brew install python@3.9"
    echo "  Linux: sudo apt install python3.9"
    echo "  Windows: https://www.python.org/downloads/"
    exit 1
fi

# Verify Python version
echo "Verifying Python version..."
PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
if ! version_compare "$MIN_PYTHON_VERSION" "$PYTHON_VERSION"; then
    echo "Error: Python $MIN_PYTHON_VERSION or higher required (found $PYTHON_VERSION)"
    echo "Please upgrade your Python installation:"
    echo "  macOS: brew upgrade python@3.9"
    echo "  Linux: sudo apt install python3.9"
    echo "  Windows: https://www.python.org/downloads/"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv $VENV_NAME || { echo "Failed to create virtual environment"; exit 1; }

# Activate virtual environment
echo "Activating virtual environment..."
source $VENV_NAME/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip || { echo "Failed to upgrade pip"; exit 1; }

# Install all required packages from requirements.txt
echo "Installing required packages from requirements.txt..."
pip install -r requirements.txt || { echo "Failed to install packages"; exit 1; }

# Create/update .env file
echo "Configuring environment variables..."

# Create temp file
TEMP_ENV=$(mktemp)

# Add existing variables first
if [ -f $ENV_FILE ]; then
    echo "Updating existing .env file..."
    cat $ENV_FILE > $TEMP_ENV
else
    echo "Creating new .env file..."
    echo "# API Keys" > $TEMP_ENV
    echo "# Model Configurations" >> $TEMP_ENV
    echo "# Fallback Order" >> $TEMP_ENV
fi

# Function to validate API key format
validate_api_key() {
    local key=$1
    echo "Validating API key: ${key:0:8}..."  # Show first 8 chars for security
    # OpenAI API keys start with 'sk-proj'
    if [[ $key == sk-proj* ]]; then
        # Test the key by making a simple API call
        response=$(python3 -c "
from openai import OpenAI
import traceback

try:
    print('Attempting API call...')
    client = OpenAI(api_key='$key')
    models = client.models.list()
    print('API call successful')
    print('valid')
except Exception as e:
    print('API call failed:')
    traceback.print_exc()
    print('invalid')
")
        echo "API response: $response"
        if [[ $response == *'valid'* ]]; then
            return 0
        else
            echo "API key validation failed. Please check your key."
            return 1
        fi
    fi
    # Other API keys should be at least 30 characters and alphanumeric
    echo "Validating API key: ${key:0:8}..."  # Show first 8 chars for security
    if [[ ${#key} -gt 30 && $key =~ ^[a-zA-Z0-9_-]+$ ]]; then
        echo "API key format valid"
        return 0
    else
        echo "API key format invalid"
        return 1
    fi
}

# Supported API keys and models
api_keys=(
    "OPENAI_API_KEY:OpenAI (Required)"
    "ANTHROPIC_API_KEY:Anthropic (Optional)"
    "COHERE_API_KEY:Cohere (Optional)"
)

echo ""
echo "We'll now configure API keys for supported LLM providers."

# Prompt for API keys
for item in "${api_keys[@]}"; do
    IFS=':' read -r var provider <<< "$item"
    current_value=$(grep -E "^$var=" $TEMP_ENV | cut -d'=' -f2)
    
    if [[ -n $current_value && $current_value != "your-*" ]]; then
        echo "$provider API key already configured [masked]"
        continue
    fi
    
    while true; do
        read -p "Enter your $provider API key (or press Enter to skip): " api_key
        
        if [[ -z $api_key ]]; then
            echo "Skipping $provider configuration"
            break
        fi
        
        if validate_api_key "$api_key"; then
            # Update or add the key
            if grep -q "^$var=" $TEMP_ENV; then
                sed -i.bak "/^$var=/d" $TEMP_ENV
            fi
            echo "$var=$api_key" >> $TEMP_ENV
            echo "$provider API key saved."
            break
        else
            echo "Invalid API key format. Please enter a valid key or press Enter to skip."
        fi
    done
done

# Add configuration variables
config_defaults=(
    "DEFAULT_PROVIDER:openai"
    "OPENAI_MODEL:gpt-4o"
    "ANTHROPIC_MODEL:claude-3-opus"
    "COHERE_MODEL:command-r-plus"
    "MAX_TOKENS:1000"
    "LOG_LEVEL:INFO"
    "FALLBACK_ORDER:openai,anthropic,cohere"
    "RATE_LIMIT_REQUESTS:60"
    "RATE_LIMIT_PERIOD:60"
    "REQUEST_TIMEOUT:30"
    "CONNECTION_TIMEOUT:10"
    "TEMPERATURE:0.7"
    "TOP_P:1.0"
    "FREQUENCY_PENALTY:0.0"
    "PRESENCE_PENALTY:0.0"
    "ENABLE_CACHING:true"
    "CACHE_TTL:300"
    "MAX_RETRIES:3"
    "RETRY_DELAY:1"
)

# Process configuration variables
for config_item in "${config_defaults[@]}"; do
    IFS=':' read -r var value <<< "$config_item"
    if ! grep -q "^$var=" $TEMP_ENV; then
        echo "$var=$value" >> $TEMP_ENV
    fi
done

for config_item in "${config_vars[@]}"; do
    IFS=':' read -r var value <<< "$config_item"
    if ! grep -q "^$var=" $TEMP_ENV; then
        echo "$var=$value" >> $TEMP_ENV
    fi
done

# Move temp file to final .env
mv $TEMP_ENV $ENV_FILE

# Verify at least one API key is configured
configured_keys=$(grep -E '^(OPENAI|ANTHROPIC|COHERE)_API_KEY=' $ENV_FILE | wc -l)
if [ $configured_keys -eq 0 ]; then
    echo "Error: No API keys configured. At least one API key is required."
    echo "Please configure at least one provider in the .env file"
    exit 1
fi

echo ""
echo "Setup completed successfully!"
echo ""
echo "To run the application:"
echo "1. Activate the virtual environment:"
echo "   source llm_agent_env/bin/activate"
echo "2. Verify the installation:"
echo "   pip list"
echo "3. Run the chat application:"
echo "   python3 src/chat.py"
echo ""
echo "To deactivate the virtual environment when done:"
echo "   deactivate"