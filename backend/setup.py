#!/usr/bin/env python3
"""
AI News Hub - Automated Setup Script
One-click setup for non-technical users
"""

import os
import subprocess
import sys
from pathlib import Path
from cryptography.fernet import Fernet

def print_header(message):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60 + "\n")

def run_command(command, description, shell=True):
    """Run a command and handle errors"""
    print(f"⏳ {description}...")
    try:
        if shell:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Done!")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {description} failed")
        print(f"   {e.stderr}")
        return None

def check_prerequisites():
    """Check if required software is installed"""
    print_header("Checking Prerequisites")

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 9):
        print("❌ Python 3.9+ is required. Please upgrade Python.")
        sys.exit(1)
    print(f"✅ Python {python_version.major}.{python_version.minor} found")

    # Check Node.js
    node_check = subprocess.run("node --version", shell=True, capture_output=True, text=True)
    if node_check.returncode != 0:
        print("❌ Node.js is not installed. Please install Node.js 16+ from https://nodejs.org/")
        sys.exit(1)
    print(f"✅ Node.js {node_check.stdout.strip()} found")

    # Check npm
    npm_check = subprocess.run("npm --version", shell=True, capture_output=True, text=True)
    if npm_check.returncode != 0:
        print("❌ npm is not installed. Please install Node.js which includes npm.")
        sys.exit(1)
    print(f"✅ npm {npm_check.stdout.strip()} found")

def setup_backend():
    """Setup backend environment"""
    print_header("Setting Up Backend")

    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    # Create virtual environment
    if not (backend_dir / "venv").exists():
        run_command(f"{sys.executable} -m venv venv", "Creating virtual environment")

    # Determine pip path
    if sys.platform == "win32":
        pip_path = backend_dir / "venv" / "Scripts" / "pip"
        python_path = backend_dir / "venv" / "Scripts" / "python"
    else:
        pip_path = backend_dir / "venv" / "bin" / "pip"
        python_path = backend_dir / "venv" / "bin" / "python"

    # Install dependencies
    run_command(f"{pip_path} install -r requirements.txt", "Installing Python packages")

    # Generate .env file
    if not (backend_dir / ".env").exists():
        print("⏳ Generating secure keys...")

        # Generate keys
        encryption_key = Fernet.generate_key().decode()
        jwt_secret = subprocess.run("openssl rand -hex 32", shell=True, capture_output=True, text=True).stdout.strip()
        csrf_secret = subprocess.run("openssl rand -hex 32", shell=True, capture_output=True, text=True).stdout.strip()

        # Create .env file
        env_content = f"""# Database (SQLite for easy start)
DATABASE_URL=sqlite:///./ai_news.db

# Security Keys (Auto-generated - DO NOT SHARE)
ENCRYPTION_KEY={encryption_key}
JWT_SECRET_KEY={jwt_secret}
CSRF_SECRET_KEY={csrf_secret}

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
"""
        with open(backend_dir / ".env", "w") as f:
            f.write(env_content)

        print("✅ .env file created with secure keys")
    else:
        print("ℹ️  .env file already exists, skipping key generation")

    # Run database migrations
    run_command(f"{python_path} -m alembic upgrade head", "Setting up database")

    print("\n✅ Backend setup complete!")

def setup_frontend():
    """Setup frontend environment"""
    print_header("Setting Up Frontend")

    frontend_dir = Path(__file__).parent.parent / "frontend"

    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return

    os.chdir(frontend_dir)

    # Install npm packages
    run_command("npm install", "Installing JavaScript packages")

    # Create frontend .env if needed
    if not (frontend_dir / ".env").exists():
        env_content = """VITE_API_BASE_URL=http://localhost:8000
"""
        with open(frontend_dir / ".env", "w") as f:
            f.write(env_content)
        print("✅ Frontend .env file created")

    print("\n✅ Frontend setup complete!")

def print_next_steps():
    """Print instructions for running the app"""
    print_header("Setup Complete! 🎉")

    print("To start AI News Hub, open TWO terminal windows:\n")

    print("📌 Terminal 1 - Backend:")
    print("   cd backend")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("   uvicorn main:app --reload --port 8000\n")

    print("📌 Terminal 2 - Frontend:")
    print("   cd frontend")
    print("   npm run dev\n")

    print("Then open your browser to: http://localhost:3000")
    print("\n💡 First time? Create an account and add your OpenAI or Anthropic API key!")
    print("   Profile → API Keys → Add your key\n")

def main():
    """Main setup function"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║            AI News Hub - Automated Setup                  ║
    ║                                                           ║
    ║  This script will set up everything you need to run       ║
    ║  AI News Hub on your local machine.                       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    try:
        check_prerequisites()
        setup_backend()
        setup_frontend()
        print_next_steps()

        print("\n✨ Setup completed successfully! ✨\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
