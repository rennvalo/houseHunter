# RapidAPI Setup Guide for HouseHunter

## 🎯 What This Does

The Auto-Fill feature automatically populates property details (bedrooms, bathrooms, square feet, lot size, garage) when you enter an address. This saves you time from manually looking up and entering this information.

## 📋 Prerequisites

- A free RapidAPI account
- The Realtor API subscription (free tier available)

## 🚀 Setup Instructions

### Step 1: Create RapidAPI Account

1. Go to [RapidAPI.com](https://rapidapi.com)
2. Click **"Sign Up"** (top right)
3. Create account with email or GitHub/Google

### Step 2: Subscribe to Realtor API

1. Go to [Realtor API on RapidAPI](https://rapidapi.com/apidojo/api/realtor)
2. Click **"Subscribe to Test"** button
3. Choose the **"Basic"** plan (FREE)
   - ✅ 500 requests/month
   - ✅ $0/month
   - ✅ Perfect for personal use
4. Complete subscription

### Step 3: Get Your API Key

1. On the Realtor API page, click **"Endpoints"** tab
2. Select any endpoint (e.g., "properties/v3/detail")
3. Look for the **"Code Snippets"** section on the right
4. You'll see headers like:
   ```javascript
   "X-RapidAPI-Key": "abc123def456..."
   "X-RapidAPI-Host": "realtor.p.rapidapi.com"
   ```
5. Copy the value of `X-RapidAPI-Key` (the long alphanumeric string)

### Step 4: Configure HouseHunter

#### Option A: Using .env File (Recommended for Docker)

1. Open the `.env` file in your HouseHunter project folder
2. Replace the line:
   ```
   RAPIDAPI_KEY=
   ```
   with:
   ```
   RAPIDAPI_KEY=your_actual_api_key_here
   ```
3. Save the file
4. Restart Docker container:
   ```bash
   docker compose down
   docker compose up -d
   ```

#### Option B: Using Environment Variable (Non-Docker)

**Windows (PowerShell):**
```powershell
$env:RAPIDAPI_KEY="your_actual_api_key_here"
python app/main.py
```

**Linux/Mac:**
```bash
export RAPIDAPI_KEY="your_actual_api_key_here"
python app/main.py
```

## ✅ Testing the Integration

1. Open HouseHunter in your browser: `http://localhost:7777`
2. In the "Add a House" form, enter an address like:
   ```
   1600 Amphitheatre Parkway, Mountain View, CA
   ```
3. Click the **"🔍 Auto-Fill"** button
4. If successful, you'll see:
   - Bedrooms, bathrooms, square feet, lot size, and garage fields populated
   - Success message with the data
5. If it fails:
   - Check the error message
   - Verify your API key is correct
   - Ensure you're subscribed to the free plan

## 🔍 How It Works

### What Gets Auto-Filled:
✅ **Bedrooms** - Number of bedrooms
✅ **Bathrooms** - Full + half baths combined
✅ **Square Feet** - Building size
✅ **Lot Size** - Converted from sq ft to acres
✅ **Garage** - Number of parking spaces
✅ **Address** - Validated/formatted address

### What You Still Enter Manually:
❌ **Subjective fields** (not available from API):
- Nice backyard
- Curb appeal
- Bathroom quality
- Privacy level
- Noise level
- Deck, patio potential
- Pool, recreation, shopping proximity
- Appliances and their condition
- Notes

## 💰 API Usage & Limits

### Free Tier (Basic Plan):
- **500 requests/month** = ~500 property lookups
- **Reset:** Monthly on your subscription date
- **Overage:** API stops working until next month (no charges)

### When to Upgrade:
- If you're looking at **500+ houses per month**, consider the Pro plan (~$10-30/month)
- For casual house hunting, the free tier is plenty

## 🐛 Troubleshooting

### Error: "API key not configured"
- ❌ **Problem:** `.env` file doesn't have your API key
- ✅ **Solution:** Add your key to `.env` and restart Docker

### Error: "Address not found"
- ❌ **Problem:** Address not in Realtor.com database
- ✅ **Solutions:**
  - Try different address format: "123 Main St, City, State ZIP"
  - Property might be FSBO (For Sale By Owner) - not on Realtor.com
  - Enter details manually

### Error: "Request timed out"
- ❌ **Problem:** RapidAPI is slow/down
- ✅ **Solution:** Wait a moment and try again

### Error: "429 Too Many Requests"
- ❌ **Problem:** You've used all 500 requests this month
- ✅ **Solution:** Wait until next month or upgrade plan

### Auto-Fill button does nothing
- ❌ **Problem:** JavaScript error or missing address
- ✅ **Solutions:**
  - Make sure you entered an address first
  - Check browser console (F12) for errors
  - Try refreshing the page

## 📊 Monitoring Usage

1. Go to [RapidAPI Dashboard](https://rapidapi.com/developer/dashboard)
2. Click on **"Analytics"**
3. View your API usage for the current month
4. See how many requests remaining

## 🔒 Security Notes

- **Never commit your API key to Git!** 
  - The `.env` file is already in `.gitignore`
  - Only commit `.env.example` (template)
- **Don't share your API key** with others
- **Regenerate key** if accidentally exposed:
  1. Go to RapidAPI dashboard
  2. Account Settings → Security
  3. Regenerate API key

## 🎓 Additional Resources

- [RapidAPI Documentation](https://docs.rapidapi.com/)
- [Realtor API Endpoints](https://rapidapi.com/apidojo/api/realtor/endpoints)
- [RapidAPI Pricing Plans](https://rapidapi.com/apidojo/api/realtor/pricing)

## 📝 Notes

- The API works best with **complete addresses** including city and state
- Some off-market properties won't be found
- Data is pulled from Realtor.com's MLS listings
- Auto-fill is optional - you can always enter data manually
- The free tier is perfect for casual house hunting (500 lookups = a lot!)

---

**Happy House Hunting! 🏡**

*Auto-fill makes comparing houses faster and easier!*
