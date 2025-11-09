# AI News Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Vue 3](https://img.shields.io/badge/Vue.js-3.0+-4FC08D.svg)](https://vuejs.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: A+](https://img.shields.io/badge/security-A%2B-brightgreen.svg)](#security-features)

> **Single-User Local Tool** - Transform articles into platform-optimized social media posts using AI

**AI News Hub** is an open-source social media content generator designed for **personal local use**. No account creation, no login required - just download, install, and use. Leverages OpenAI GPT-4 and Anthropic Claude to create engaging, platform-specific posts for Twitter, LinkedIn, Instagram, and Threads.

**✨ Perfect for:**
- Content creators managing their personal social media
- Marketers automating their own accounts
- Developers who want full control of their data
- Anyone seeking privacy-first social media automation

**🔒 Privacy First:**
- All data stays on **your machine**
- **No cloud service** - 100% local deployment
- Your API keys never leave your computer
- Complete control over your content and connections

---

## 🎉 **NEW: Easy Installation for Everyone!**

We've completely redesigned the installation process - **no technical expertise required!**

- **🚀 One-Click Setup** - Automated script installs everything (5 minutes)
- **🐳 Docker Support** - Single command to run (2 minutes)
- **📚 Beginner Guide** - Step-by-step [INSTALL.md](INSTALL.md) with screenshots
- **✅ Auto-Configuration** - Generates all keys automatically
- **🔧 Multi-Platform** - Windows, Mac, and Linux support

[**Get Started Now →**](#quick-start)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

**For Developers:** See [TECHNICAL.md](TECHNICAL.md) for architecture, API documentation, security details, development guides, and testing instructions.

---

## Features

### Core Capabilities
- **AI-Powered Content Generation** - Transform articles into engaging social posts using OpenAI GPT-4 or Anthropic Claude
- **Multi-Platform Publishing** - Native support for Twitter, LinkedIn, Instagram, and Threads with platform-specific optimizations
- **RSS Feed Aggregation** - Automatically discover and aggregate content from your favorite RSS feeds
- **Draft Management** - Save, edit, and refine posts before publishing
- **Publishing History** - Track all published content with timestamps and analytics
- **Real-time Validation** - Character count, hashtag validation, and platform-specific constraints

### Security & Privacy
- **Bank-Level Encryption** - All your API keys and tokens are encrypted (AES-256)
- **Your Keys, Your Control** - No shared credentials; you own everything
- **Secure Authentication** - OAuth 2.0/1.0a for social media connections
- **Local Data** - Everything stored on your machine, never sent to third parties
- **Privacy First** - No tracking, no analytics, no data collection

**Security Score:** A+ rated. [See security details →](TECHNICAL.md#security-features)

### Developer Experience
- **FastAPI Backend** - High-performance async Python framework with automatic OpenAPI docs
- **Vue 3 Frontend** - Modern, reactive UI with Tailwind CSS
- **Type Safety** - Pydantic models and TypeScript throughout
- **Comprehensive Testing** - 1,951 test cases covering critical paths
- **Claude Code Skills** - 7 pre-built skills for common tasks (migrations, OAuth setup, security audits)
- **Docker Support** - One-command deployment with docker-compose
- **Easy Setup** - Automated installation scripts for all platforms (Windows/Mac/Linux)

---

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104+ (Python 3.9+)
- **Database**: PostgreSQL 13+ / SQLite (development)
- **ORM**: SQLAlchemy 2.0 with Alembic migrations
- **Authentication**: JWT + OAuth 1.0a/2.0 (Authlib)
- **Security**: bcrypt, cryptography (AES-256), CSRF tokens
- **AI Providers**: OpenAI API, Anthropic API
- **Caching**: Redis (optional)
- **Testing**: pytest, pytest-asyncio, pytest-cov

### Frontend
- **Framework**: Vue 3 with Composition API
- **Build Tool**: Vite 4
- **Styling**: Tailwind CSS 3
- **HTTP Client**: Axios
- **State Management**: Vue Reactivity API

### Infrastructure
- **Web Server**: Uvicorn (ASGI)
- **Proxy**: Nginx (production)
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions (coming soon)

**For Developers:** See [TECHNICAL.md](TECHNICAL.md) for detailed architecture diagrams, API documentation, and development workflows.

---

## Quick Start

**New!** We've made installation super easy for everyone - no technical skills required! Choose your preferred method:

### 🚀 Option 1: One-Click Setup (Recommended for Beginners)

**Perfect for first-time users** - Automated script handles everything:

```bash
# 1. Download the code
git clone https://github.com/larry311012/ai-news-hub.git
cd ai-news-hub/backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# OR: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the automated setup script
python3 setup.py

# 5. Follow the on-screen instructions
# That's it! Setup takes ~5 minutes
```

**What setup.py does automatically:**
- ✅ Checks your system
- ✅ Generates secure keys (no copy/paste!)
- ✅ Sets up database with anonymous user
- ✅ Configures everything for you

### 🐳 Option 2: Docker (Easiest - One Command!)

**Have Docker installed?** Get running in 2 minutes:

```bash
git clone https://github.com/larry311012/ai-news-hub.git
cd ai-news-hub/ai-news-hub-web
docker-compose up
```

Open <http://localhost:3000> - **Done!**

### ⚙️ Option 3: Manual Installation

**For developers who want full control** - See detailed instructions in [INSTALL.md](INSTALL.md#option-3-manual-installation-for-advanced-users)

---

### 📖 Need Help?

- **Installation guide:** [INSTALL.md](INSTALL.md) - Step-by-step setup for all skill levels
- **User guide:** [USER_GUIDE.md](USER_GUIDE.md) - How to use the app (RSS feeds, posts, publishing)
- **Troubleshooting:** [Common issues and fixes](INSTALL.md#troubleshooting)
- **Prerequisites:** [Python](https://www.python.org/downloads/) & [Node.js](https://nodejs.org/) downloads

---

## Installation

**📚 Complete Guide:** See [INSTALL.md](INSTALL.md) for detailed, beginner-friendly instructions

### Prerequisites

Choose your installation method first - prerequisites vary:

| Method | What You Need | Time | Skill Level |
|--------|---------------|------|-------------|
| 🚀 **One-Click** | Python 3.9+ & Node.js 16+ | 5 min | Beginner ⭐ |
| 🐳 **Docker** | Docker Desktop only | 2 min | Easiest ⭐⭐⭐ |
| ⚙️ **Manual** | Python, Node.js, PostgreSQL | 15 min | Advanced |

**Download Links:**
- Python 3.9+: <https://www.python.org/downloads/>
- Node.js 16+: <https://nodejs.org/>
- Docker Desktop: <https://www.docker.com/products/docker-desktop/>

### Installation Scripts

We provide automated setup scripts for all platforms:

- **`backend/setup.py`** - Mac/Linux automated setup
- **`backend/setup.bat`** - Windows automated setup (double-click)
- **`docker-compose.yml`** - Docker one-command setup

All scripts automatically:
- Check prerequisites
- Install dependencies
- Generate secure keys (no manual steps!)
- Configure database
- Set up environment files

**Just run the script and follow prompts!**

### First-Time Setup (After Installation)

**No account creation needed!** AI News Hub runs in single-user mode - just open and use.

1. **Open the app:** <http://localhost:3000>

2. **Add your AI API key:**
   - Go to Profile → API Keys
   - Add OpenAI key from <https://platform.openai.com/api-keys>
   - Or Anthropic key from <https://console.anthropic.com/>

3. **Optional - Connect social media:**
   - Settings → Social Connections
   - Connect Twitter, LinkedIn, Instagram, or Threads

4. **Start generating posts!**
   - Add RSS feeds or paste article URLs
   - Click "Generate Post"
   - Edit and publish to connected platforms

**Need help?**
- **Installation:** See [INSTALL.md](INSTALL.md) for detailed setup guides
- **Using the app:** See [USER_GUIDE.md](USER_GUIDE.md) for step-by-step tutorials

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run tests and linters (`pytest && black . && flake8`)
5. Commit with conventional commits (`feat: add amazing feature`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Reporting Issues

- **Bugs**: Use the bug report template
- **Features**: Use the feature request template
- **Security**: Email security@ainewshub.com (do not open public issues)

### Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
Copyright (c) 2025 AI News Hub Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

**Vote on features**: [GitHub Discussions](https://github.com/larry311012/ai-news-hub/discussions)

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Vue.js](https://vuejs.org/) - Progressive JavaScript framework
- [Anthropic Claude](https://www.anthropic.com/) - AI assistant
- [OpenAI](https://openai.com/) - GPT models
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS

Special thanks to all contributors and the open-source community.

---

## Support

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md) - Complete walkthrough
- **Installation Help**: [INSTALL.md](INSTALL.md) - Setup guide
- **Technical Docs**: [TECHNICAL.md](TECHNICAL.md) - For developers
- **Discussions**: [GitHub Discussions](https://github.com/larry311012/ai-news-hub/discussions)
- **Issues**: [GitHub Issues](https://github.com/larry311012/ai-news-hub/issues)

---

**Star this repo** if you find it useful!

Made with care by developers, for developers.
