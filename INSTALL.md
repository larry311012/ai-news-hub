# Installation Guide

> **Important:** AI News Hub is a **single-user local tool**. No account creation or login required - all data stays on your machine!

Choose the installation method that works best for you:

## 🚀 Option 1: One-Click Setup (Recommended for Beginners)

**Perfect for:** Non-technical users who want the easiest setup

### Prerequisites
- [Python 3.9+](https://www.python.org/downloads/) - Download and install
- [Node.js 16+](https://nodejs.org/) - Download and install

### Steps

1. **Download the code:**
   ```bash
   git clone https://github.com/larry311012/ai-news-hub.git
   cd ai-news-hub/ai-news-hub-web
   ```

2. **Run the setup script:**
   ```bash
   cd backend
   python3 setup.py
   ```

3. **That's it!** The script will:
   - ✅ Check your system
   - ✅ Install all dependencies
   - ✅ Generate secure keys automatically
   - ✅ Set up the database
   - ✅ Configure everything for you

4. **Start the app** (follow the instructions shown by the script):
   - Open Terminal 1: Start backend
   - Open Terminal 2: Start frontend
   - Visit http://localhost:3000

---

## 🐳 Option 2: Docker (Easiest - One Command!)

**Perfect for:** Users who have Docker installed

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) - Download and install

### Steps

1. **Download the code:**
   ```bash
   git clone https://github.com/larry311012/ai-news-hub.git
   cd ai-news-hub/ai-news-hub-web
   ```

2. **Start everything:**
   ```bash
   docker-compose up
   ```

3. **That's it!** Visit http://localhost:3000

**To stop:** Press `Ctrl+C` or run `docker-compose down`

---

## ⚙️ Option 3: Manual Installation (For Advanced Users)

**Perfect for:** Developers who want full control

See the [detailed manual installation guide](README.md#installation) in the main README.

---

## 📝 After Installation

### First-Time Setup

**No account creation needed!** Just open http://localhost:3000 and start using.

1. **Add your API key:**
   - Go to Profile → API Keys
   - Add your OpenAI or Anthropic API key
   - Get keys from:
     - OpenAI: https://platform.openai.com/api-keys
     - Anthropic: https://console.anthropic.com/

2. **Connect social media (optional):**
   - Go to Settings → Social Connections
   - Connect Twitter, LinkedIn, Instagram, or Threads
   - You'll need developer accounts for each platform

3. **Start generating posts!**
   - Add RSS feeds or paste article URLs
   - Generate AI posts
   - Publish to your connected platforms

---

## 🆘 Troubleshooting

### "Python not found"
- **Windows:** Install from https://python.org, check "Add to PATH" during installation
- **Mac:** Run `brew install python3` (requires Homebrew)
- **Linux:** Run `sudo apt install python3 python3-pip`

### "Node.js not found"
- Install from https://nodejs.org/
- Download the LTS (Long Term Support) version

### "Port 8000 already in use"
- Another app is using port 8000
- **Fix:** `lsof -ti:8000 | xargs kill -9` (Mac/Linux)
- **Fix:** `netstat -ano | findstr :8000` then kill that process (Windows)

### "Database error"
- Delete `backend/ai_news.db`
- Run `alembic upgrade head` again

### "Frontend won't start"
- Delete `frontend/node_modules`
- Run `npm install` again

### Still stuck?
- Check [GitHub Issues](https://github.com/larry311012/ai-news-hub/issues)
- Create a new issue with your error message

---

## 🎥 Video Tutorials (Coming Soon)

- [ ] Complete installation walkthrough
- [ ] First-time setup guide
- [ ] Connecting social media accounts
- [ ] Generating your first post

---

## 💡 Tips for Non-Technical Users

### What's a Terminal?
- **Mac:** Applications → Utilities → Terminal
- **Windows:** Search for "Command Prompt" or "PowerShell"
- **Linux:** Press `Ctrl+Alt+T`

### What's a Virtual Environment?
- It's like a separate folder for Python packages
- Keeps this project's dependencies isolated
- You don't need to understand it - the scripts handle it!

### What are API Keys?
- Like passwords that let the app use AI services
- You get them from OpenAI or Anthropic
- They're stored encrypted - only you can access them

### Do I need to code?
- **No!** Everything is already built
- You just need to install and run it
- The web interface is point-and-click

---

## 🔒 Security Notes

- Your API keys are encrypted and stored locally
- No data is sent to our servers
- You control everything on your own machine
- Keep your `.env` file secret (never share it)

---

## 📚 Next Steps

After installation, check out:
- [User Guide](docs/USER_GUIDE.md) - How to use all features
- [FAQ](docs/FAQ.md) - Common questions
- [README](README.md) - Full documentation
