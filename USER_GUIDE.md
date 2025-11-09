# User Guide

> **Quick guide to using AI News Hub** - From first launch to publishing your first post in 10 minutes!

This guide assumes you've already installed AI News Hub. If not, see [INSTALL.md](INSTALL.md) first.

---

## Table of Contents

1. [First Time Setup](#first-time-setup)
2. [Adding Your AI API Key](#adding-your-ai-api-key)
3. [Adding RSS Feeds](#adding-rss-feeds)
4. [Generating Your First Post](#generating-your-first-post)
5. [Editing and Refining Posts](#editing-and-refining-posts)
6. [Connecting Social Media Accounts](#connecting-social-media-accounts)
7. [Publishing Posts](#publishing-posts)
8. [Managing Saved Articles](#managing-saved-articles)
9. [Common Workflows](#common-workflows)
10. [Tips and Tricks](#tips-and-tricks)
11. [Troubleshooting](#troubleshooting)

---

## First Time Setup

### Step 1: Start the Application

After installation, you should have two terminal windows open:

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate  # Mac/Linux
uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

### Step 2: Open the App

Open your browser and go to: **http://localhost:3000**

You should see the AI News Hub home page with:
- RSS feed list (empty at first)
- "Add Feed" button
- Navigation menu at the top

**Important:** AI News Hub runs in **anonymous mode** - no login required! Everything is ready to use immediately.

---

## Adding Your AI API Key

Before you can generate posts, you need to add an API key from OpenAI or Anthropic.

### Getting an API Key

**Option 1: OpenAI (GPT-4)**
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

**Option 2: Anthropic (Claude)**
1. Go to https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to "API Keys"
4. Create a new key and copy it

### Adding the Key to AI News Hub

1. **Click on your profile icon** in the top right corner
2. Select **"Profile"** from the dropdown
3. Scroll to the **"API Keys"** section
4. Click **"Add API Key"**
5. Fill in the form:
   - **Provider:** Select "OpenAI" or "Anthropic"
   - **API Key:** Paste your key
   - **Name (optional):** Give it a name like "My OpenAI Key"
6. Click **"Save"**

**Your API key is encrypted and stored locally** - it never leaves your computer!

### Verify It Works

You should see:
- ✅ Green checkmark next to the key
- "Status: Active" label
- The key partially masked (e.g., `sk-****...****1234`)

---

## Adding RSS Feeds

RSS feeds are sources of articles that you can turn into social media posts.

### Popular RSS Feeds to Try

**Tech News:**
- TechCrunch: `https://techcrunch.com/feed/`
- Hacker News: `https://news.ycombinator.com/rss`
- The Verge: `https://www.theverge.com/rss/index.xml`

**AI News:**
- MIT Technology Review: `https://www.technologyreview.com/feed/`
- OpenAI Blog: `https://openai.com/blog/rss/`

**Business:**
- Harvard Business Review: `https://hbr.org/feed`
- TechCrunch Startups: `https://techcrunch.com/tag/startups/feed/`

### Adding a Feed

1. **Click "Add Feed"** button on the home page
2. Enter the **RSS feed URL**
3. Click **"Add Feed"** or press Enter
4. The feed will appear in your list with latest articles

### Auto-Discover Feeds

Don't know the exact RSS URL? Try the auto-discovery feature:

1. Click **"Discover Feeds"**
2. Enter a website URL (e.g., `https://techcrunch.com`)
3. AI News Hub will find available RSS feeds
4. Select the one you want and click "Add"

---

## Generating Your First Post

Now comes the fun part - turning articles into social media posts!

### Method 1: From Home Page

1. **Browse your RSS feeds** on the home page
2. Find an interesting article
3. Click the **"Generate Post"** button on the article card
4. Wait 10-20 seconds while AI generates platform-specific posts

### Method 2: From URL

1. Click **"Generate from URL"** in the top menu
2. Paste any article URL (Medium, blog, news site, etc.)
3. Click **"Generate Posts"**

### Method 3: From Saved Articles

1. Browse articles and click the **bookmark icon** to save them
2. Go to **"Saved Articles"** in the menu
3. Select articles you want to use
4. Click **"Generate Post"**

### What Happens Next

AI News Hub will generate **4 posts** optimized for each platform:

- **Twitter** - Concise thread (280 chars per tweet)
- **LinkedIn** - Professional tone, longer format
- **Instagram** - Visual-focused with emoji
- **Threads** - Casual, conversational style

Each post includes:
- Platform-appropriate tone
- Relevant hashtags
- Character count validation
- Link to original article

---

## Editing and Refining Posts

After generation, you'll be on the **Post Editor** page.

### Edit Post Content

1. **Select a platform tab** (Twitter, LinkedIn, Instagram, Threads)
2. **Edit the text** directly in the text area
3. **Watch the character counter** to stay within platform limits
4. **Add or remove hashtags** as needed

### Platform-Specific Tips

**Twitter:**
- Maximum 280 characters per tweet
- Threads automatically split if too long
- Include 2-3 hashtags max

**LinkedIn:**
- Longer posts work well (1300+ characters)
- Professional tone resonates
- Ask questions to drive engagement

**Instagram:**
- First line is crucial (appears in feed)
- Use 5-10 relevant hashtags
- Emoji make posts stand out

**Threads:**
- Casual, conversational tone
- 500 character limit
- Build on trending topics

### Save as Draft

If you're not ready to publish:

1. Click **"Save Draft"** button
2. Your post is saved locally
3. Access drafts from **"Drafts"** in the menu

---

## Connecting Social Media Accounts

To publish posts, you need to connect your social media accounts.

### Before You Start

You'll need **developer accounts** for each platform:

- **Twitter:** https://developer.twitter.com/
- **LinkedIn:** https://www.linkedin.com/developers/
- **Instagram:** https://developers.facebook.com/
- **Threads:** https://developers.facebook.com/

**Don't worry!** Developer accounts are free and just require a few clicks to set up.

### Connecting Twitter

1. Go to **Settings → Social Connections**
2. Click **"Connect Twitter"**
3. Enter your Twitter OAuth credentials:
   - **API Key** (25 characters)
   - **API Secret** (50 characters)
   - **Access Token**
   - **Access Token Secret**
4. Click **"Save & Connect"**
5. Authorize the app in the popup window

**Status:** You should see ✅ "Connected" with your Twitter username

### Connecting LinkedIn

1. Go to **Settings → Social Connections**
2. Click **"Connect LinkedIn"**
3. Enter your LinkedIn OAuth credentials:
   - **Client ID**
   - **Client Secret**
4. Click **"Save & Connect"**
5. Authorize in the LinkedIn popup

### Connecting Instagram

1. Go to **Settings → Social Connections**
2. Click **"Connect Instagram"**
3. Enter your Facebook/Instagram OAuth credentials
4. Authorize the app
5. Select the Instagram business account to use

### Connecting Threads

Similar to Instagram (uses Facebook OAuth):

1. Go to **Settings → Social Connections**
2. Click **"Connect Threads"**
3. Authorize with Facebook credentials
4. Select your Threads account

---

## Publishing Posts

Once you have social accounts connected, publishing is easy!

### Publish Single Platform

1. Open a post in the **Post Editor**
2. Click the **platform tab** you want to publish to
3. Click **"Publish to [Platform]"** button
4. Confirm in the dialog
5. Wait for confirmation toast: "Published successfully!"

### Publish to Multiple Platforms

1. Open a post in the **Post Editor**
2. Select the checkboxes for platforms you want
3. Click **"Publish to All Selected"**
4. Confirm
5. Posts will be published sequentially

### What Happens

- Post is sent to the platform's API
- Status changes to "Published"
- Timestamp is recorded
- Link to published post is saved (where available)

### Publishing History

View all your published posts:

1. Go to **"History"** in the menu
2. See all published posts with:
   - Platform icons
   - Publication dates
   - Links to view on platform
   - Analytics (if available)

---

## Managing Saved Articles

Save interesting articles to read or use later.

### Saving Articles

**From Home Page:**
- Click the **bookmark icon** on any article card
- Icon turns solid to indicate it's saved

**From Article Page:**
- Click the **"Save Article"** button
- Article added to your saved collection

### Viewing Saved Articles

1. Go to **"Saved"** in the menu
2. Browse your saved articles
3. Filter by:
   - **All** - Everything you've saved
   - **Today** - Saved today
   - **This Week** - Saved in last 7 days

### Using Saved Articles

From the Saved page, you can:

1. **Read Article** - Click title to open original
2. **Generate Post** - Click "Generate" button
3. **Remove** - Click the X icon to unsave

### Organization Tips

- Save articles throughout the week
- Review saved articles on specific days
- Generate posts in batches for efficiency

---

## Common Workflows

### Workflow 1: Daily Content Curator

**Best for:** Sharing daily industry news

1. **Morning:** Add RSS feeds for your industry
2. **Browse** latest articles over coffee
3. **Save** 5-10 interesting articles (bookmark them)
4. **Lunch break:** Generate posts from saved articles
5. **Review and edit** posts
6. **Schedule** or publish throughout the day

**Time:** 30 minutes total

### Workflow 2: Weekly Batch Publisher

**Best for:** Busy professionals who want to plan ahead

1. **Monday:** Review last week's RSS articles
2. **Save** 20-30 articles for the week
3. **Generate posts** for all saved articles (bulk generation)
4. **Tuesday-Thursday:** Edit and refine posts
5. **Friday:** Publish all posts or save as drafts

**Time:** 2 hours on Monday, 30 min daily editing

### Workflow 3: Event Coverage

**Best for:** Covering conferences, product launches, news

1. **Before event:** Set up RSS feeds for event coverage
2. **During event:**
   - Find breaking news articles
   - Generate posts from URLs
   - Edit quickly for timely publishing
3. **Publish immediately** to relevant platforms
4. **After event:** Review and analyze engagement

**Time:** Active monitoring + 5 min per post

### Workflow 4: Thought Leadership

**Best for:** Building personal brand, sharing insights

1. **Find research** or industry reports (RSS or URL)
2. **Generate LinkedIn post** (focus on this platform)
3. **Add personal insights** - edit to include your perspective
4. **Add a question** to drive discussion
5. **Publish and engage** with comments

**Time:** 15-20 minutes per post

---

## Tips and Tricks

### 🚀 Productivity Tips

**Keyboard Shortcuts:**
- `Ctrl/Cmd + S` - Save draft
- `Esc` - Close dialogs
- `Tab` - Navigate between fields

**Batch Operations:**
- Select multiple articles with checkboxes
- Generate posts for all at once
- Save time on repetitive tasks

**Template Reuse:**
- Save your best-performing posts
- Use them as templates for similar content
- Maintain consistent voice

### 🎯 Content Quality Tips

**Better AI Output:**
- Choose articles with clear structure
- Longer articles = better summaries
- Technical content works especially well

**Hashtag Strategy:**
- Twitter: 2-3 hashtags max
- Instagram: 5-10 hashtags
- LinkedIn: 3-5 professional hashtags
- Research trending hashtags in your niche

**Engagement Boosters:**
- Ask questions at the end
- Include statistics or data points
- Use emoji strategically (not too many!)
- Tag relevant people/companies (manually add)

### 💡 Platform-Specific Tips

**Twitter:**
- Front-load important info
- Break long posts into threads
- Use line breaks for readability
- Tag sources when sharing

**LinkedIn:**
- Start with a hook question
- Use bullet points for clarity
- Share personal experiences
- Call-to-action at the end

**Instagram:**
- First line visible in feed - make it count
- Use emoji to break up text
- Create carousel posts for more space
- Consistency in hashtags

**Threads:**
- Conversational, authentic tone
- Jump on trending topics
- Engage with replies quickly
- Keep it casual

### 🔧 Technical Tips

**Performance:**
- Generate posts during off-peak hours
- Close unused browser tabs
- Clear cache if UI feels slow

**Privacy:**
- Your data stays local
- Regularly backup your database
- Keep encryption keys safe

**Reliability:**
- Keep both backend and frontend running
- Check API key balance (OpenAI/Anthropic)
- Monitor for platform API changes

---

## Troubleshooting

### "No posts generated" or empty results

**Cause:** AI API key missing or invalid

**Fix:**
1. Go to Profile → API Keys
2. Check key status (should be green ✅)
3. If red ❌, delete and re-add the key
4. Make sure you have API credits (OpenAI/Anthropic)

---

### "Failed to fetch article"

**Cause:** Website blocks scraping or invalid URL

**Fix:**
1. Try a different URL from the same site
2. Use RSS feed instead of direct URL
3. Copy/paste article text manually (future feature)

---

### Post generation is slow (>30 seconds)

**Cause:** AI API rate limits or server load

**Fix:**
1. Wait a bit and try again
2. Check OpenAI/Anthropic status page
3. Try a shorter article
4. Use a different AI provider

---

### "Publishing failed" error

**Cause:** Social media OAuth token expired or invalid

**Fix:**
1. Go to Settings → Social Connections
2. Disconnect the platform
3. Reconnect and re-authorize
4. Try publishing again

---

### Character count shows red (over limit)

**Cause:** Post is too long for platform

**Fix:**
1. Edit the post to shorten it
2. Remove unnecessary words
3. For Twitter: Post will auto-split into thread
4. Regenerate for a different tone (may be shorter)

---

### Can't see my published posts

**Cause:** Publishing completed but link not available

**Fix:**
1. Check your social media account directly
2. Look in History page for records
3. Some platforms don't return post URLs
4. Check platform API permissions

---

### RSS feed not updating

**Cause:** Feed URL changed or site is down

**Fix:**
1. Check feed URL in browser
2. Remove and re-add the feed
3. Try the feed discovery feature
4. Contact site admin if feed is broken

---

### Backend/Frontend won't start

**Cause:** Port already in use or dependencies missing

**Fix:**

**Backend (Port 8000):**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Restart
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Frontend (Port 3000):**
```bash
# Kill existing process
lsof -ti:3000 | xargs kill -9

# Restart
cd frontend
npm run dev
```

---

### Getting authentication errors

**Cause:** Anonymous mode issue (rare)

**Fix:**
1. Clear browser cache and cookies
2. Restart backend server
3. Check `.env` file has `ANONYMOUS_MODE=true`
4. If persists, delete `backend/ai_news.db` and restart

---

## Getting More Help

### Documentation

- **Installation Issues:** [INSTALL.md](INSTALL.md)
- **Technical Details:** [TECHNICAL.md](TECHNICAL.md)
- **General Info:** [README.md](README.md)

### Community Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/larry311012/ai-news-hub/issues)
- **Discussions:** [Ask questions and share tips](https://github.com/larry311012/ai-news-hub/discussions)

### Quick Reference

| Task | Page | Time |
|------|------|------|
| Add API Key | Profile | 2 min |
| Add RSS Feed | Home | 1 min |
| Generate Post | Generate | 20 sec |
| Connect Social Media | Settings | 5 min |
| Publish Post | Editor | 10 sec |

---

## What's Next?

Now that you know how to use AI News Hub, here are some ideas:

1. **Set up 5 RSS feeds** in your industry
2. **Generate 10 posts** from different sources
3. **Connect 2 social accounts** to start
4. **Publish your first post** (exciting!)
5. **Create a weekly workflow** that fits your schedule

**Questions?** Check [GitHub Discussions](https://github.com/larry311012/ai-news-hub/discussions) or open an issue.

**Enjoying AI News Hub?** Star the repo on GitHub and share with friends!

---

Made with ❤️ for content creators everywhere.
