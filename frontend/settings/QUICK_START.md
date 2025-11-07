# OAuth Credentials Management - Quick Start Guide

## Access the Interface

1. **Start the Backend Server**
   ```bash
   cd /Users/ranhui/ai_post/web/backend
   uvicorn main:app --reload --port 8000
   ```

2. **Open in Browser**
   ```
   http://localhost:8000/settings/oauth-credentials.html
   ```

3. **Login as Admin**
   - Use an account with `is_admin = true`
   - Or add admin email to environment: `ADMIN_EMAILS="admin@example.com"`

---

## Configure Twitter OAuth 1.0a

### Step 1: Get Twitter API Credentials
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create or select your app
3. Navigate to "Keys and tokens"
4. Copy your **API Key** and **API Secret**

### Step 2: Configure in UI
1. Click **"Configure Twitter"** button
2. Paste your **API Key** into the "API Key" field
3. Paste your **API Secret** into the "API Secret" field
4. Copy the **Callback URL** shown
5. Add the callback URL to your Twitter app settings
6. Click **"Test Connection"** to verify
7. Click **"Save Credentials"**

**Result:** Twitter OAuth card shows "Configured" badge with green checkmark.

---

## Configure LinkedIn OAuth 2.0

### Step 1: Get LinkedIn Credentials
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Create or select your app
3. Copy your **Client ID** and **Client Secret**

### Step 2: Configure in UI
1. Click **"Configure LinkedIn"** button
2. Paste your **Client ID**
3. Paste your **Client Secret**
4. Copy the **Redirect URI** shown
5. Add the redirect URI to your LinkedIn app settings
6. Click **"Test Connection"** to verify
7. Click **"Save Credentials"**

**Result:** LinkedIn OAuth card shows "Configured" badge with green checkmark.

---

## Configure Threads OAuth 2.0

### Step 1: Get Threads Credentials
1. Go to [Meta for Developers](https://developers.facebook.com/apps)
2. Create or select your Threads app
3. Copy your **App ID** and **App Secret**

### Step 2: Configure in UI
1. Click **"Configure Threads"** button
2. Paste your **App ID**
3. Paste your **App Secret**
4. Copy the **Redirect URI** shown
5. Add the redirect URI to your Threads app settings
6. Click **"Test Connection"** to verify
7. Click **"Save Credentials"**

**Result:** Threads OAuth card shows "Configured" badge with green checkmark.

---

## Common Tasks

### Edit Existing Credentials
1. Click **"Edit"** button on configured platform
2. Modify fields as needed
3. Test connection
4. Save credentials

### Test Connection
1. Click **"Test Connection"** button
2. Wait for spinner to finish
3. See success or error message
4. If error, check troubleshooting tips

### Remove Credentials
1. Click **"Remove"** button (red)
2. Confirm in dialog
3. Credentials deleted from database
4. Card shows "Not Configured" state

### Copy Callback/Redirect URL
1. Expand platform configuration form
2. Click **"Copy"** button next to URL field
3. Toast notification confirms copy
4. Paste into platform settings

---

## Keyboard Shortcuts

- **Tab**: Navigate between fields
- **Shift + Tab**: Navigate backward
- **Enter**: Submit form (when in input field)
- **Escape**: Close expanded form
- **Space**: Activate buttons

---

## Troubleshooting

### "Access Denied" Error
**Cause:** User is not an admin
**Fix:** Grant admin access:
```sql
UPDATE users SET is_admin = 1 WHERE email = 'your-email@example.com';
```

### "Connection Failed" Error
**Possible Causes:**
1. API credentials are incorrect
2. Callback/Redirect URL not added to platform
3. App permissions are insufficient
4. Platform service is down

**Fix:**
1. Double-check credentials (no extra spaces)
2. Verify callback URL matches exactly
3. Check app has Read and Write permissions
4. Test on platform developer portal first

### Form Won't Save
**Possible Causes:**
1. Required fields empty
2. Invalid characters in API key
3. Network error
4. Backend not running

**Fix:**
1. Fill all required fields (marked with *)
2. Remove special characters from API key
3. Check browser console for errors
4. Verify backend is running on port 8000

### Credentials Not Loading
**Possible Causes:**
1. Database encryption key missing
2. Credentials stored with different encryption key
3. Database connection issue

**Fix:**
1. Check `ENCRYPTION_KEY` environment variable is set
2. Re-save credentials if key changed
3. Check backend logs for database errors

---

## Best Practices

### Security
- ✅ Never share API secrets publicly
- ✅ Use strong, unique secrets
- ✅ Rotate credentials periodically
- ✅ Test connections before deploying
- ✅ Monitor for unauthorized access

### Maintenance
- 📅 Review credentials quarterly
- 🔄 Update when platforms make changes
- 📊 Monitor connection test results
- 📝 Document any custom configurations
- 🔍 Audit admin access regularly

### User Experience
- 🧪 Test new credentials before removing old ones
- 📋 Keep backup of working credentials
- 🔔 Set up alerts for credential expiration
- 📚 Document platform-specific requirements
- 🎯 Verify all features work after updates

---

## Support

### Documentation
- **UI Design:** `/backend/OAUTH_ADMIN_SETTINGS_UI_DESIGN.md`
- **Backend API:** `/backend/docs/OAUTH_CREDENTIALS_MANAGEMENT.md`
- **Implementation:** `OAUTH_CREDENTIALS_IMPLEMENTATION_SUMMARY.md`

### API Endpoints
```
GET    /api/admin/oauth-credentials           # List all platforms
GET    /api/admin/oauth-credentials/{platform}  # Get platform details
POST   /api/admin/oauth-credentials/{platform}  # Save credentials
POST   /api/admin/oauth-credentials/{platform}/test  # Test connection
DELETE /api/admin/oauth-credentials/{platform}  # Remove credentials
```

### Backend Logs
```bash
# View backend logs for errors
tail -f /var/log/ai_post/backend.log

# Or if running with uvicorn:
# Check terminal output where server is running
```

---

## Quick Reference

### File Locations
```
Frontend:
  /Users/ranhui/ai_post/web/frontend/settings/oauth-credentials.html
  /Users/ranhui/ai_post/web/frontend/settings/oauth-credentials.js

Backend:
  /Users/ranhui/ai_post/web/backend/api/admin_oauth_credentials.py
  /Users/ranhui/ai_post/web/backend/utils/oauth_credential_manager.py
  /Users/ranhui/ai_post/web/backend/database_oauth_credentials.py
```

### Environment Variables
```bash
# Required
ENCRYPTION_KEY="your-generated-encryption-key"

# Optional (for admin access)
ADMIN_EMAILS="admin1@example.com,admin2@example.com"
```

### Database Tables
```
oauth_platform_credentials  # Stores encrypted credentials
users                       # Contains is_admin field
```

---

## Success Checklist

Before deploying to production:

- [ ] Backend API is running and accessible
- [ ] ENCRYPTION_KEY is set in environment
- [ ] At least one admin user exists
- [ ] All 3 platforms tested with real credentials
- [ ] Callback/Redirect URLs configured on platforms
- [ ] Connection tests pass for all platforms
- [ ] Error handling tested (invalid credentials)
- [ ] Mobile responsive layout verified
- [ ] Accessibility tested with screen reader
- [ ] HTTPS enabled in production
- [ ] Database backups configured
- [ ] Admin access audited

---

**Estimated Setup Time:** 15-30 minutes (for all 3 platforms)

**Need Help?** Check the troubleshooting section or review backend logs for detailed error messages.
