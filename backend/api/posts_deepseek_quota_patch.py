"""
PATCH INSTRUCTIONS FOR posts.py

This file contains the modifications needed to add DeepSeek support and quota checking to posts.py

CHANGES REQUIRED:

1. Add imports at top (after existing imports):
   - from middleware.quota_checker import QuotaManager, check_quota_dependency, increment_user_quota
   - from database import AdminSettings

2. Update _configure_api_key function (around line 148):
   Replace the function with:
"""

def _configure_api_key(api_key: str, ai_provider: str):
    """Set API key in environment based on provider."""
    if ai_provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif ai_provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif ai_provider == "deepseek":
        os.environ["DEEPSEEK_API_KEY"] = api_key


"""
3. Update generate_post function API key priority (around line 412):
   Replace the priority order section with:
"""

# Priority order: OpenAI first, then Anthropic, then DeepSeek
for provider in ["openai", "anthropic", "deepseek"]:
    if provider in available_keys:
        try:
            api_key = decrypt_api_key(available_keys[provider])
            if api_key:
                ai_provider = provider
                break
        except Exception as e:
            print(f"Failed to decrypt {provider} key: {e}")
            continue


"""
4. Add admin API key fallback for guest users (after line 438, before the "if not api_key:" check):
"""

# Fallback to admin default API key for guest users
if not api_key and user.user_tier == "guest":
    admin_api_key_setting = db.query(AdminSettings).filter(
        AdminSettings.key == "admin_default_api_key"
    ).first()
    admin_provider_setting = db.query(AdminSettings).filter(
        AdminSettings.key == "default_ai_provider"
    ).first()

    if admin_api_key_setting and admin_api_key_setting.value:
        ai_provider = admin_provider_setting.value if admin_provider_setting else "openai"

        # Decrypt if encrypted
        if admin_api_key_setting.encrypted:
            from cryptography.fernet import Fernet
            ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
            cipher_suite = Fernet(ENCRYPTION_KEY.encode())
            try:
                api_key = cipher_suite.decrypt(admin_api_key_setting.value.encode()).decode()
            except Exception as decrypt_error:
                logger.error(f"Failed to decrypt admin API key: {decrypt_error}")
        else:
            api_key = admin_api_key_setting.value

        logger.info(f"Using admin default {ai_provider} API key for guest user {user.id}")


"""
5. Update error message to include DeepSeek (line 440-444):
   Replace with:
"""

if not api_key:
    error_message = "No API key configured. Please add your OpenAI, Anthropic, or DeepSeek API key in your Profile settings."
    if user.user_tier == "guest":
        error_message = "No admin default API key configured. Please contact support or create an account."

    raise HTTPException(
        status_code=400,
        detail=error_message,
    )


"""
6. Add quota checking AFTER API key validation and BEFORE creating post record (after line 450):
"""

# QUOTA CHECK: Ensure user has quota remaining
quota_manager = QuotaManager(db)
has_quota, quota_info = quota_manager.check_quota(user)

if not has_quota:
    logger.warning(f"Quota exceeded for user {user.id} ({user.user_tier})")
    raise HTTPException(
        status_code=429,
        detail={
            "error": "quota_exceeded",
            "message": f"Daily quota exceeded. You have used {quota_info['used']}/{quota_info['limit']} posts today.",
            "quota": quota_info,
            "upgrade_message": "Upgrade to a paid plan for unlimited posts." if user.user_tier == "free" else None,
        },
    )

logger.info(f"Quota check passed for user {user.id}: {quota_info['used']}/{quota_info['limit']} used")


"""
7. Add quota increment AFTER post creation successful (after line 467, after db.refresh(post)):
"""

# Increment quota after successful post creation
try:
    increment_user_quota(user, db)
    logger.info(f"Incremented quota for user {user.id} after post {post.id} creation")
except Exception as e:
    logger.error(f"Failed to increment quota for user {user.id}: {e}")
    # Don't fail the request if quota increment fails


"""
8. Update generate_post return response to include quota info (line 501-506):
   Replace return statement with:
"""

# Get updated quota info
_, updated_quota = quota_manager.check_quota(user)

# Return immediately
return {
    "success": True,
    "post_id": post.id,
    "status": "processing",
    "message": "Post generation started. Poll /api/posts/{post_id}/status for progress or use SSE stream.",
    "quota": updated_quota,
}


"""
COMPLETE UPDATED generate_post FUNCTION:
Here's the complete function with all changes applied for reference:
"""

# @router.post("/generate")
# async def generate_post(
#     request: GenerateRequest,
#     user: User = Depends(get_current_user_dependency),
#     db: Session = Depends(get_db),
# ):
#     """
#     Generate social media posts from selected articles (optimized with async processing)
#
#     This endpoint now returns immediately with a post_id and status.
#     Use GET /api/posts/{post_id}/status to poll for completion, or
#     use GET /api/posts/generate/stream for real-time progress updates via SSE.
#
#     Enforces quota limits based on user tier:
#     - Guest users: 1 post (uses admin default API key)
#     - Free users: 2 posts per day
#     - Paid users: 100 posts per day
#     """
#     try:
#         # Get API key
#         user_api_keys = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).all()
#
#         available_keys = {key.provider: key.encrypted_key for key in user_api_keys}
#
#         api_key = None
#         ai_provider = None
#
#         # Priority order: OpenAI first, then Anthropic, then DeepSeek
#         for provider in ["openai", "anthropic", "deepseek"]:
#             if provider in available_keys:
#                 try:
#                     api_key = decrypt_api_key(available_keys[provider])
#                     if api_key:
#                         ai_provider = provider
#                         break
#                 except Exception as e:
#                     print(f"Failed to decrypt {provider} key: {e}")
#                     continue
#
#         # Fallback to Settings table
#         if not api_key:
#             ai_provider_setting = db.query(Settings).filter(Settings.key == "ai_provider").first()
#             api_key_setting = db.query(Settings).filter(Settings.key == "api_key").first()
#
#             if api_key_setting and api_key_setting.value:
#                 ai_provider = ai_provider_setting.value if ai_provider_setting else "openai"
#                 from cryptography.fernet import Fernet
#
#                 ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
#                 cipher_suite = Fernet(ENCRYPTION_KEY.encode())
#                 try:
#                     api_key = cipher_suite.decrypt(api_key_setting.value.encode()).decode()
#                 except Exception as decrypt_error:
#                     print(f"Failed to decrypt Settings API key: {decrypt_error}")
#
#         # Fallback to admin default API key for guest users
#         if not api_key and user.user_tier == "guest":
#             admin_api_key_setting = db.query(AdminSettings).filter(
#                 AdminSettings.key == "admin_default_api_key"
#             ).first()
#             admin_provider_setting = db.query(AdminSettings).filter(
#                 AdminSettings.key == "default_ai_provider"
#             ).first()
#
#             if admin_api_key_setting and admin_api_key_setting.value:
#                 ai_provider = admin_provider_setting.value if admin_provider_setting else "openai"
#
#                 # Decrypt if encrypted
#                 if admin_api_key_setting.encrypted:
#                     from cryptography.fernet import Fernet
#                     ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
#                     cipher_suite = Fernet(ENCRYPTION_KEY.encode())
#                     try:
#                         api_key = cipher_suite.decrypt(admin_api_key_setting.value.encode()).decode()
#                     except Exception as decrypt_error:
#                         logger.error(f"Failed to decrypt admin API key: {decrypt_error}")
#                 else:
#                     api_key = admin_api_key_setting.value
#
#                 logger.info(f"Using admin default {ai_provider} API key for guest user {user.id}")
#
#         if not api_key:
#             error_message = "No API key configured. Please add your OpenAI, Anthropic, or DeepSeek API key in your Profile settings."
#             if user.user_tier == "guest":
#                 error_message = "No admin default API key configured. Please contact support or create an account."
#
#             raise HTTPException(
#                 status_code=400,
#                 detail=error_message,
#             )
#
#         # Get articles
#         articles = db.query(Article).filter(Article.id.in_(request.article_ids)).all()
#
#         if not articles:
#             raise HTTPException(status_code=404, detail="No articles found")
#
#         # QUOTA CHECK: Ensure user has quota remaining
#         quota_manager = QuotaManager(db)
#         has_quota, quota_info = quota_manager.check_quota(user)
#
#         if not has_quota:
#             logger.warning(f"Quota exceeded for user {user.id} ({user.user_tier})")
#             raise HTTPException(
#                 status_code=429,
#                 detail={
#                     "error": "quota_exceeded",
#                     "message": f"Daily quota exceeded. You have used {quota_info['used']}/{quota_info['limit']} posts today.",
#                     "quota": quota_info,
#                     "upgrade_message": "Upgrade to a paid plan for unlimited posts." if user.user_tier == "free" else None,
#                 },
#             )
#
#         logger.info(f"Quota check passed for user {user.id}: {quota_info['used']}/{quota_info['limit']} used")
#
#         # Create post record immediately with "processing" status
#         post = Post(
#             user_id=user.id,
#             article_id=articles[0].id if len(articles) == 1 else None,
#             article_title=articles[0].title if len(articles) == 1 else f"{len(articles)} articles",
#             twitter_content="",
#             linkedin_content="",
#             threads_content="",
#             platforms=request.platforms,
#             status="processing",
#             ai_summary="",
#         )
#
#         db.add(post)
#         db.commit()
#         db.refresh(post)
#
#         # Increment quota after successful post creation
#         try:
#             increment_user_quota(user, db)
#             logger.info(f"Incremented quota for user {user.id} after post {post.id} creation")
#         except Exception as e:
#             logger.error(f"Failed to increment quota for user {user.id}: {e}")
#             # Don't fail the request if quota increment fails
#
#         # Invalidate user's post list cache (new post added)
#         await PostsCache.invalidate_user_posts(user.id)
#
#         # Initialize job status
#         generation_jobs[post.id] = {
#             "status": "queued",
#             "progress": 0,
#             "current_step": "Queued",
#             "content": {},
#             "error": None,
#             "error_details": None,
#         }
#
#         # Start background task (create a new session for thread safety)
#         from database import SessionLocal
#
#         background_db = SessionLocal()
#
#         # Fire and forget the async task
#         asyncio.create_task(
#             generate_post_async(
#                 post.id,
#                 request.article_ids,
#                 request.platforms,
#                 user.id,
#                 api_key,
#                 ai_provider,
#                 background_db,
#             )
#         )
#
#         # Get updated quota info
#         _, updated_quota = quota_manager.check_quota(user)
#
#         # Return immediately
#         return {
#             "success": True,
#             "post_id": post.id,
#             "status": "processing",
#             "message": "Post generation started. Poll /api/posts/{post_id}/status for progress or use SSE stream.",
#             "quota": updated_quota,
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         import traceback
#
#         error_detail = str(e) if str(e) else "Unknown error occurred"
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=error_detail)


"""
TESTING INSTRUCTIONS:

1. Run migration:
   python web/backend/migrations/add_user_tiers.py seed

2. Test guest user (should use admin API key):
   - Create guest session
   - Try to generate 1 post (should work)
   - Try to generate 2nd post (should fail with quota exceeded)

3. Test free user:
   - Create free account
   - Generate 2 posts (should work)
   - Try 3rd post same day (should fail)
   - Check /api/users/quota endpoint

4. Test DeepSeek integration:
   - Add DeepSeek API key via /api/settings/validate-api-key
   - Generate post (should use DeepSeek if it's the only key)

5. Test quota reset:
   - Set quota_reset_date to past date in database
   - Generate post (should reset quota and work)
"""
