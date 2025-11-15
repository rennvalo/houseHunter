# 🔍 Auto-Fill Quick Reference

## How to Use Auto-Fill

1. **Enter address** in the form (e.g., "123 Main St, Springfield, IL")
2. **Click "🔍 Auto-Fill"** button
3. **Wait** for data to load (2-5 seconds)
4. **Review** auto-populated fields
5. **Fill in** remaining subjective fields manually

## What Gets Auto-Filled ✅

| Field | Description |
|-------|-------------|
| **Bedrooms** | Number of bedrooms |
| **Bathrooms** | Total bathrooms (full + half) |
| **Square Feet** | Building size |
| **Lot Size** | Lot size in acres |
| **Garage** | Number of garage spaces |
| **Address** | Validated/formatted address |

## What You Still Enter ❌

These are **subjective** and not available from APIs:

- Nice backyard ⭐
- Curb appeal ⭐
- Bathroom quality ⭐
- Privacy level ⭐
- Noise level ⭐
- Deck, patio potential ⭐
- Pool, recreation, shopping ⭐
- Appliances & their condition ⭐
- Notes & thoughts ⭐

## Tips for Best Results

### Address Format
✅ **Good:**
- `1600 Amphitheatre Parkway, Mountain View, CA`
- `123 Main Street, Springfield, IL 62701`
- `456 Oak Ave, Chicago, Illinois`

❌ **May not work:**
- `123 Main` (too short)
- `Main Street` (no number)
- Unlisted/FSBO properties

### API Limits (Free Tier)
- **500 lookups/month** = ~16 per day
- Resets monthly
- No charges if you exceed (just stops working)

### When It Fails
If auto-fill doesn't work:
1. ✅ **Check address format** - try full address with city/state
2. ✅ **Try manual entry** - property might not be listed
3. ✅ **Check API key** - ensure `.env` has your RapidAPI key
4. ✅ **Verify subscription** - confirm you're subscribed to Realtor API on RapidAPI

## Common Errors & Solutions

| Error | Meaning | Solution |
|-------|---------|----------|
| "API key not configured" | Missing or invalid API key | Add key to `.env` file and restart Docker |
| "Address not found" | Property not in database | Enter details manually or try different format |
| "Request timed out" | API is slow/down | Wait and try again |
| "429 Too Many Requests" | Used all 500 monthly requests | Wait until next month or upgrade plan |

## Cost Breakdown

### Free Tier (Recommended)
- **$0/month**
- **500 requests/month**
- Perfect for personal house hunting
- Example: 20 houses/month × 25 months = FREE

### Pro Tier (If Needed)
- **~$10-30/month**
- **10,000-50,000 requests**
- Only needed if you're a real estate agent looking up hundreds of properties

## Quick Setup Reminder

1. **Sign up:** [RapidAPI.com](https://rapidapi.com) → Create account
2. **Subscribe:** [Realtor API](https://rapidapi.com/apidojo/api/realtor) → Basic (FREE) plan
3. **Get key:** Copy from Code Snippets section
4. **Configure:** Add to `.env` file:
   ```
   RAPIDAPI_KEY=your_key_here
   ```
5. **Restart:** `docker compose down && docker compose up -d`

## Full Setup Guide

For detailed step-by-step instructions with screenshots, see:
📖 **[RAPIDAPI_SETUP.md](RAPIDAPI_SETUP.md)**

---

**Remember:** Auto-fill is **optional**! You can always enter data manually.
