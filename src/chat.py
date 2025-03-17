import os
import sys
import subprocess
import logging
import time
import argparse
from typing import Optional, Dict, List
from enum import Enum

def _check_environment(check_packages=False):
    """Verify virtual environment and optionally required packages
    
    Args:
        check_packages (bool): If True, also verify required packages
    """
    try:
        # First check virtual environment activation
        venv_path = os.environ.get('VIRTUAL_ENV')
        if not venv_path:
            # Fallback check for Python executable path
            python_path = sys.executable
            if 'llm_agent_env' not in python_path:
                print("Virtual environment not active")
                print("Please run the setup script first:")
                print("  ./scripts/phase1_setup.sh")
                print("Then activate the virtual environment using the command provided by the setup script")
                sys.exit(1)
        
        # Only check packages if explicitly requested
        if check_packages:
            required_packages = [
                'langchain', 'langchain_openai', 'langchain_community',
                'loguru', 'python-dotenv'
            ]
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)
                    
            if missing_packages:
                print(f"Missing required packages: {', '.join(missing_packages)}")
                print("Please re-run setup script: ./scripts/phase1_setup.sh")
                sys.exit(1)
    except Exception as e:
        print(f"Environment validation failed: {str(e)}")
        sys.exit(1)
                
        if missing_packages:
            print(f"Missing required packages: {', '.join(missing_packages)}")
            print("Please re-run setup script: ./scripts/phase1_setup.sh")
            sys.exit(1)
            
    except Exception as e:
        print(f"Environment validation failed: {str(e)}")
        sys.exit(1)

# Run environment check before any imports
_check_environment()

# Now import required packages
from dotenv import load_dotenv
from loguru import logger
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.memory import BaseMemory
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import (
    ChatAnthropic,
    ChatCohere
)
from langchain.callbacks.base import BaseCallbackHandler
import ssl

class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"

class DebugCallbackHandler(BaseCallbackHandler):
    """Callback handler for comprehensive debug logging
    
    This handler provides detailed logging of all LLM interactions when --debug flag is enabled.
    Logs include provider-specific raw input/output and system details.
    """
    def __init__(self, args: argparse.Namespace):
        """Initialize the debug callback handler
        
        Args:
            args: Command line arguments containing debug flag
        """
        self.args = args
        self.provider = None
        
    def set_provider(self, provider: Provider):
        """Set the current provider for provider-specific logging"""
        self.provider = provider
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        if self.args.debug:
            start_time = time.time()
            logger.debug("LLM Request:")
            logger.debug(f"Provider: {self.provider.value if self.provider else 'unknown'}")
            logger.debug(f"Model: {kwargs.get('invocation_params', {}).get('model_name', 'unknown')}")
            logger.debug(f"Temperature: {kwargs.get('invocation_params', {}).get('temperature', 0.7)}")
            logger.debug(f"Max Tokens: {kwargs.get('invocation_params', {}).get('max_tokens', 1000)}")
            
            # Provider-specific request details
            if self.provider == Provider.OPENAI:
                logger.debug("OpenAI Request Details:")
                logger.debug(f"System Messages: {kwargs.get('messages', [])}")
                logger.debug(f"Function Calls: {kwargs.get('functions', [])}")
            elif self.provider == Provider.ANTHROPIC:
                logger.debug("Anthropic Request Details:")
                logger.debug(f"System Prompt: {kwargs.get('system', '')}")
                logger.debug(f"Stop Sequences: {kwargs.get('stop_sequences', [])}")
            elif self.provider == Provider.COHERE:
                logger.debug("Cohere Request Details:")
                logger.debug(f"Conversation ID: {kwargs.get('conversation_id', '')}")
                logger.debug(f"Generation Parameters: {kwargs.get('generation_params', {})}")
            
            logger.debug("Prompts:")
            for i, prompt in enumerate(prompts):
                logger.debug(f"Prompt {i + 1}:\n{prompt}")
            self.start_time = start_time

    def on_llm_end(self, response, **kwargs):
        if self.args.debug:
            logger.debug("LLM Response:")
            logger.debug(f"Provider: {self.provider.value if self.provider else 'unknown'}")
            
            # Provider-specific response details
            if self.provider == Provider.OPENAI:
                logger.debug("OpenAI Response Details:")
                logger.debug(f"Completion Tokens: {response.llm_output.get('token_usage', {}).get('completion_tokens', 'unknown')}")
                logger.debug(f"Function Calls: {response.additional_kwargs.get('function_call', {})}")
            elif self.provider == Provider.ANTHROPIC:
                logger.debug("Anthropic Response Details:")
                logger.debug(f"Completion Reason: {response.additional_kwargs.get('stop_reason', 'unknown')}")
                logger.debug(f"Stop Sequence: {response.additional_kwargs.get('stop_sequence', 'unknown')}")
            elif self.provider == Provider.COHERE:
                logger.debug("Cohere Response Details:")
                logger.debug(f"Conversation ID: {response.additional_kwargs.get('conversation_id', 'unknown')}")
                logger.debug(f"Response Tokens: {response.additional_kwargs.get('response_tokens', 'unknown')}")
            
            logger.debug(f"Raw Response: {str(response)}")
            logger.debug(f"Response Time: {time.time() - self.start_time:.2f}s")

    def on_llm_error(self, error, **kwargs):
        logger.error(f"LLM Error: {str(error)}")
        if self.args.debug:
            logger.error("Error Details:")
            logger.error(f"Provider: {self.provider.value if self.provider else 'unknown'}")
            logger.error(f"Type: {type(error).__name__}")
            logger.error(f"Message: {str(error)}")
            
            # Provider-specific error details
            if self.provider == Provider.OPENAI:
                logger.error("OpenAI Error Details:")
                logger.error(f"API Version: {kwargs.get('api_version', 'unknown')}")
                logger.error(f"Request ID: {kwargs.get('request_id', 'unknown')}")
            elif self.provider == Provider.ANTHROPIC:
                logger.error("Anthropic Error Details:")
                logger.error(f"Error Type: {kwargs.get('error_type', 'unknown')}")
                logger.error(f"Error Code: {kwargs.get('error_code', 'unknown')}")
            elif self.provider == Provider.COHERE:
                logger.error("Cohere Error Details:")
                logger.error(f"Error Code: {kwargs.get('error_code', 'unknown')}")
                logger.error(f"Error Type: {kwargs.get('error_type', 'unknown')}")
            
            if hasattr(error, 'response'):
                logger.error(f"Response Status: {error.response.status_code}")
                logger.error(f"Response Text: {error.response.text}")

    def on_chain_end(self, outputs, **kwargs):
        """Log memory updates after each chain execution"""
        if self.args.debug:
            logger.debug("Memory Update:")
            logger.debug(f"Provider: {self.provider.value if self.provider else 'unknown'}")
            logger.debug(f"New Memory Content: {outputs.get('response', '')}")
            logger.debug(f"Current Memory State: {kwargs.get('memory', {}).get('history', '')}")
            logger.debug("Memory Metadata:")
            logger.debug(f"Input Tokens: {outputs.get('input_tokens', 'unknown')}")
            logger.debug(f"Output Tokens: {outputs.get('output_tokens', 'unknown')}")
            logger.debug(f"Total Tokens: {outputs.get('total_tokens', 'unknown')}")

class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"

class ProviderConfig:
    def __init__(self, api_key: str, model: str, max_tokens: int = 1000):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

# Parse command line arguments
parser = argparse.ArgumentParser(description='AI Chat Assistant')
parser.add_argument('--debug', action='store_true', help='Enable comprehensive debug logging')
args = parser.parse_args()

# Configure logging
log_level = logging.DEBUG if args.debug else logging.WARNING
logging.basicConfig(level=log_level)
logger.add("logs/chat.log", rotation="1 MB", retention="7 days")

if args.debug:
    logger.debug("Debug mode enabled")
    logger.debug("Debug output includes:")
    logger.debug("- System configuration")
    logger.debug("- Environment variables")
    logger.debug("- Provider initialization")
    logger.debug("- API key validation details")
    logger.debug("- Error stack traces")
    logger.debug("- Performance metrics")
    logger.debug("- Network request details")
    logger.debug("- Conversation details")
    logger.debug("- Memory updates")
    logger.debug("- Provider-specific request/response details")

# Load environment variables from project root
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if args.debug:
    logger.debug(f"Loading environment variables from: {env_path}")

if not os.path.exists(env_path):
    logger.error(f"Could not find .env file at {env_path}")
    logger.info("Please create a .env file in the project root directory")
    logger.info("Refer to design/phase1_environment_setup.md for the required format")
    sys.exit(1)

# Verify .env file is readable
try:
    with open(env_path, 'r') as f:
        if args.debug:
            logger.debug(f".env file contents:\n{f.read()}")
except Exception as e:
    logger.error(f"Failed to read .env file: {str(e)}")
    sys.exit(1)

# Load environment variables with manual parsing as fallback
loaded = load_dotenv(env_path, verbose=True)
if not loaded:
    logger.warning("dotenv failed to load variables, attempting manual parsing")
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
                        if args.debug:
                            logger.debug(f"Manually set {key.strip()}")
                    except ValueError:
                        continue
    except Exception as e:
        logger.error(f"Failed to manually parse .env file: {str(e)}")
        sys.exit(1)

if args.debug:
    logger.debug("Current environment variables:")
    for k, v in os.environ.items():
        logger.debug(f"{k}={v}")

# Validate configured environment variables
if args.debug:
    logger.debug("Validating configured environment variables...")
configured_vars = [var for var in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY"]
                  if os.getenv(var)]

if not configured_vars:
    logger.error("No LLM API keys configured")
    logger.info("Please configure at least one API key in the .env file")
    logger.info("Refer to design/phase1_environment_setup.md for the required format")
    sys.exit(1)

if args.debug:
    logger.debug(f"Configured API keys: {', '.join(configured_vars)}")

class ChatApp:
    def __init__(self):
        self.providers = self._initialize_providers()
        self.provider = None
        self.fallback_order = self._get_fallback_order()
        self.llm = None
        from langchain_community.chat_message_histories import ChatMessageHistory
        self.memory = ChatMessageHistory()
        self.memory.add_user_message("Hello! I'm your AI assistant.")
        self.conversation = None
        self._check_openssl_version()

    def _initialize_providers(self) -> Dict[Provider, ProviderConfig]:
        """Initialize all provider configurations"""
        providers = {
            Provider.OPENAI: ProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY", "").strip(),
                model=os.getenv("OPENAI_MODEL", "gpt-4o")
            ),
            Provider.ANTHROPIC: ProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus")
            ),
            Provider.COHERE: ProviderConfig(
                api_key=os.getenv("COHERE_API_KEY", "").strip(),
                model=os.getenv("COHERE_MODEL", "command-r-plus")
            ),
        }
        return providers

    def _get_fallback_order(self) -> List[Provider]:
        """Get the fallback order from environment variables"""
        fallback = os.getenv("FALLBACK_ORDER", "openai,anthropic,cohere")
        return [Provider(p.strip()) for p in fallback.split(",")]

    def _initialize_llm(self):
        """Initialize the language model with fallback support"""
        for provider in [self.provider] + self.fallback_order:
            config = self.providers[provider]
            
            if not config.api_key or config.api_key.startswith("your-"):
                continue
                
            try:
                if provider == Provider.OPENAI:
                    llm = ChatOpenAI(
                        openai_api_key=config.api_key,
                        model_name=config.model,
                        temperature=0.7,
                        max_tokens=config.max_tokens,
                        streaming=True
                    )
                    # Test connection
                    llm.invoke("Test connection")
                    return llm
                    
                elif provider == Provider.ANTHROPIC:
                    llm = ChatAnthropic(
                        anthropic_api_key=config.api_key,
                        model=config.model,
                        temperature=0.7,
                        max_tokens_to_sample=config.max_tokens
                    )
                    # Test connection
                    llm.invoke("Test connection")
                    return llm
                    
                elif provider == Provider.COHERE:
                    llm = ChatCohere(
                        cohere_api_key=config.api_key,
                        model=config.model,
                        temperature=0.7,
                        max_tokens=config.max_tokens
                    )
                    # Test connection
                    llm.invoke("Test connection")
                    return llm
                    
            except Exception as e:
                error_msg = f"Failed to initialize {provider.value}: {str(e)}"
                if "401" in str(e):
                    error_msg += "\nInvalid API key - please verify your credentials"
                elif "404" in str(e):
                    error_msg += "\nModel not found - please verify model name"
                elif "429" in str(e):
                    error_msg += "\nRate limit exceeded - please try again later"
                if args.debug:
                    logger.warning(error_msg)
                continue
                
        logger.error("No working LLM provider found")
        sys.exit(1)

    def _check_openssl_version(self):
        """Check SSL library version for informational purposes"""
        openssl_version = ssl.OPENSSL_VERSION
        
        if args.debug:
            logger.debug(f"SSL library version: {openssl_version}")
            if "LibreSSL" in openssl_version:
                logger.debug("LibreSSL detected - showing full details in debug mode")
                logger.debug("Some advanced cryptographic features may require OpenSSL")
        else:
            # Add warning filters for LibreSSL-related warnings in normal mode
            import warnings
            warnings.filterwarnings(
                action='ignore',
                category=UserWarning,
                message='.*LibreSSL.*'
            )
            warnings.filterwarnings(
                action='ignore',
                category=UserWarning,
                message='.*NotOpenSSLWarning.*'
            )
            
            if "LibreSSL" in openssl_version:
                logger.info("LibreSSL detected - works for most use cases")
                logger.info("Advanced cryptographic features may require OpenSSL")

    def _initialize_conversation(self) -> RunnableWithMessageHistory:
        """Initialize the conversation chain with message history"""
        prompt_template = PromptTemplate(
            input_variables=["history", "input"],
            template="""
            You are a helpful AI assistant. Continue the conversation in a helpful and professional manner.

            Previous conversation:
            {history}

            Current input:
            {input}
            """
        )
        
        debug_handler = DebugCallbackHandler(args)
        debug_handler.set_provider(self.provider)
        
        chain = prompt_template | self.llm
        
        return RunnableWithMessageHistory(
            runnable=chain,
            get_session_history=lambda session_id: self.memory,
            input_messages_key="input",
            history_messages_key="history",
            callbacks=[debug_handler] if args.debug else None,
            metadata={"memory": self.memory}
        )

    def get_available_providers(self) -> List[Provider]:
        """Get list of providers with valid API keys"""
        providers = []
        for provider in Provider:
            config = self.providers[provider]
            if args.debug:
                logger.debug(f"Checking provider: {provider.value}")
                logger.debug(f"API key: {config.api_key}")
            
            # Check if API key exists and is valid
            if not config.api_key or len(config.api_key.strip()) < 30:
                if args.debug:
                    logger.debug(f"Invalid API key length for {provider.value}")
                continue
                
            clean_key = config.api_key.strip().replace('"', '').replace("'", "")
            
            # Validate key format based on provider
            if provider == Provider.OPENAI:
                if not clean_key.startswith("sk-"):
                    if args.debug:
                        logger.debug(f"Invalid OpenAI key format for {provider.value}")
                    continue
                if not (clean_key.startswith("sk-proj-") or len(clean_key) == 51):
                    logger.debug(f"Invalid OpenAI key structure for {provider.value}")
                    continue
                providers.append(provider)
            elif provider == Provider.ANTHROPIC:
                if not clean_key.startswith("sk-ant-api"):
                    if args.debug:
                        logger.debug(f"Invalid Anthropic key format for {provider.value}")
                    continue
                providers.append(provider)
            elif provider == Provider.COHERE:
                if not clean_key.startswith("cohere_"):
                    if args.debug:
                        logger.debug(f"Invalid Cohere key format for {provider.value}")
                    continue
                if len(clean_key) != 40:
                    logger.debug(f"Invalid Cohere key length for {provider.value}")
                    continue
                providers.append(provider)
            
            if args.debug:
                logger.debug(f"Valid {provider.value.capitalize()} key found")
                
        if args.debug:
            logger.debug(f"Available providers: {[p.value for p in providers]}")
        return providers

    def _select_provider(self):
        """Prompt user to select a provider from available options"""
        available_providers = self.get_available_providers()
        
        if not available_providers:
            logger.error("No valid API keys found for any provider")
            sys.exit(1)
            
        if len(available_providers) == 1:
            print(f"Using {available_providers[0].value.capitalize()} provider")
            return available_providers[0]
            
        print("Available providers:")
        for i, provider in enumerate(available_providers):
            print(f"{i + 1}. {provider.value.capitalize()}")
            
        while True:
            try:
                choice = int(input(f"Select provider (1-{len(available_providers)}): "))
                if 1 <= choice <= len(available_providers):
                    return available_providers[choice - 1]
                print("Invalid choice, try again")
            except ValueError:
                print("Please enter a number")

    def run(self):
        """Main chat loop"""
        try:
            print("Welcome to the AI Chat Assistant!")
            self.provider = self._select_provider()
            self.llm = self._initialize_llm()
            self.conversation = self._initialize_conversation()
            print("Type 'exit' to quit or 'switch' to change provider")
            
            while True:
                try:
                    user_input = input("\nYou: ")
                    
                    if user_input.lower() in ["exit", "quit"]:
                        print("Goodbye!")
                        break
                    elif user_input.lower() == "switch":
                        available_providers = self.get_available_providers()
                        if len(available_providers) == 1:
                            print(f"Only {available_providers[0].value.capitalize()} provider available")
                            continue
                            
                        self.provider = self._select_provider()
                        self.llm = self._initialize_llm()
                        self.conversation = self._initialize_conversation()
                        print(f"Switched to {self.provider.value.capitalize()} provider")
                        continue
                        
                    response = self.conversation.invoke(
                        {"input": user_input},
                        config={"configurable": {"session_id": "default"}}
                    )
                    print(f"\nAssistant: {response.content}")
                    
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except Exception as e:
                    if args.debug:
                        logger.error(f"Error during conversation: {str(e)}")
                    print("An error occurred. Please try again.")
                    
        finally:
            # Cleanup resources
            if hasattr(self, 'llm') and self.llm:
                if hasattr(self.llm, 'close'):
                    self.llm.close()
                del self.llm
                
            if hasattr(self, 'memory') and self.memory:
                self.memory.clear()
                del self.memory
                
            if hasattr(self, 'conversation') and self.conversation:
                del self.conversation
        


def main():
    try:
        _check_environment()
        app = ChatApp()
        app.run()
    except Exception as e:
        if args.debug:
            logger.error(f"Application error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()