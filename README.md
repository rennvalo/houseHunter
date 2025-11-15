# 🏠 HouseHunter

**A FastAPI-based web application that helps you make smart house decisions using a comprehensive point-based scoring system.**

HouseHunter lets you track potential houses, rate them based on dozens of key features (garage, bedrooms, bathrooms, lot size, appliances, location, and more), and compare scores to make data-driven decisions. Your data persists in browser local storage, so your houses are saved even when you close the browser!

---

## ✨ Features

- **Add & Edit Houses**: Input address, features, and notes - edit them anytime
- **🔍 Auto-Fill Property Details**: Automatically populate bedrooms, bathrooms, square feet, lot size, and garage from address using RapidAPI (optional, requires free API key)
- **Automatic Scoring**: Each house gets a score based on a comprehensive point system
- **Compare Houses**: View all houses sorted by score (highest first)
- **Persistent Storage**: Data saved in browser localStorage AND in-memory
- **Edit Mode**: Modify existing houses without losing data
- **Modern UI**: Clean Tailwind CSS interface with house-themed background
- **Docker Ready**: Run everything with a single command
- **Mobile Responsive**: Works great on phones and tablets

---

## 📊 Scoring System

| Feature | Description | Points |
|---------|-------------|--------|
| **Garage** | Per car capacity | +1 per car |
| **Bathrooms** | Per bathroom | +1 per bathroom |
| **Bedrooms** | Per bedroom | +1 per bedroom |
| **Square Feet** | Per 500 sq ft | +1 per 500 sq ft |
| **Lot Size** | Per 0.25 acres | +1 per 0.25 acres |
| **Backyard** | Nice backyard | +2 |
| **Curb Appeal** | Has curb appeal | +1 |
| **Basement** | Unfinished basement | +1 |
| | Finished basement | +2 |
| **Privacy** | Very Private | +3 |
| | Private | +2 |
| | Normal | +1 |
| | Not Private | -1 |
| **Deck** | Has deck | +1 |
| **Patio Potential** | Space for patio | +2 |
| **Pool** | Has pool | +3 |
| **Near Recreation** | Close to parks/trails | +2 |
| **Walking to Shopping** | Walking distance | +2 |
| **Appliances** | Old appliance | +1 each |
| | Modern appliance | +2 each |
| | (Dishwasher, Range, Oven, Fridge, Washer, Dryer, Microwave) | |
| **HOA** | Has HOA | -1 |
| | Per $100/month fee | -1 per $100 |

**Example Scores:**
- 3-car garage, 4 bedrooms, 3 bathrooms, 2000 sq ft, 0.5 acre = +15 points (before other features)
- 6 modern appliances = +12 points
- HOA with $300/month fee = -4 points

---

## 🚀 Quick Start (From Scratch)

### Prerequisites

- **Docker Desktop** installed and running
  - Windows: [Download Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
  - Mac: [Download Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
  - Linux: Install Docker and Docker Compose via your package manager

### Initial Setup

1. **Clone or download the project**

```bash
# If you have git
git clone <repository-url>
cd HouseHunter

# Or simply navigate to your project folder
cd HouseHunter
```

2. **Verify Docker is running**

```bash
docker --version
docker compose version
```

You should see version numbers. If not, start Docker Desktop first.

3. **[Optional] Set up RapidAPI for Auto-Fill**

To enable the auto-fill feature that populates property details from an address:

1. Sign up at [RapidAPI.com](https://rapidapi.com) (free)
2. Subscribe to the [Realtor API](https://rapidapi.com/apidojo/api/realtor) free plan (500 requests/month)
3. Copy your API key
4. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` and add your API key:
   ```
   RAPIDAPI_KEY=your_api_key_here
   ```

**📖 Detailed instructions:** See [RAPIDAPI_SETUP.md](RAPIDAPI_SETUP.md)

**Note:** This step is optional. You can still use the app and enter all details manually without the API.

4. **Build and start the application**

```bash
docker compose up --build
```

This will:
- Build the Python/FastAPI container
- Install all dependencies
- Start the web server on port 7777

5. **Open your browser**

Navigate to: **http://localhost:7777**

6. **Start rating houses!**

Try the "Load Example Houses" button to see sample data.

---

## 🔧 Running the Application

### Standard Start (after first build)

```bash
docker compose up
```

### Start in Background (Detached Mode)

```bash
docker compose up -d
```

### Stop the Application

```bash
# Stop gracefully (Ctrl+C if running in foreground)
# Or use:
docker compose down
```

### View Logs

```bash
docker compose logs -f app
```

---

## 🐛 Troubleshooting Guide

### Problem: "Port 7777 is already in use"

**Solution 1: Stop other services using the port**
```bash
# Windows (PowerShell as Admin)
netstat -ano | findstr :7777
# Note the PID and kill it
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:7777 | xargs kill -9
```

**Solution 2: Change the port**
Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Change 7777 to 8080 (or any free port)
```

### Problem: "Docker daemon is not running"

**Solution:**
- **Windows/Mac**: Open Docker Desktop application
- **Linux**: Start Docker service
  ```bash
  sudo systemctl start docker
  ```

### Problem: "Container keeps restarting" or crashes on startup

**Solution:**
```bash
# Check logs for errors
docker compose logs app

# Common fixes:
# 1. Remove old containers and rebuild
docker compose down
docker compose up --build

# 2. Remove all related containers/volumes
docker compose down -v
docker compose up --build

# 3. Check if requirements.txt is causing issues
docker compose build --no-cache
```

### Problem: "Cannot connect to localhost:7777"

**Solutions:**
1. Verify container is running:
   ```bash
   docker compose ps
   ```
   Should show `app` with status `Up`

2. Check if app started successfully:
   ```bash
   docker compose logs app
   ```
   Look for: `Uvicorn running on http://0.0.0.0:8000`

3. Try accessing via 127.0.0.1 instead:
   ```
   http://127.0.0.1:7777
   ```

4. On Windows, check if Windows Firewall is blocking the port

### Problem: "Module not found" or Python import errors

**Solution:**
```bash
# Rebuild container from scratch
docker compose down
docker compose build --no-cache
docker compose up
```

### Problem: Changes to code not reflected

**Solution:**
```bash
# Rebuild the container
docker compose up --build

# Or force a complete rebuild
docker compose build --no-cache
docker compose up
```

### Problem: Browser localStorage not persisting

**Solution:**
- Check browser settings - localStorage might be disabled
- Try a different browser (Chrome, Firefox, Edge)
- Check if you're in Private/Incognito mode (localStorage is cleared on close)
- Clear browser cache and reload

### Problem: "Permission denied" errors (Linux)

**Solution:**
```bash
# Run with sudo
sudo docker compose up --build

# Or add your user to docker group
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

### Problem: Container builds but website shows blank page

**Solution:**
1. Check browser console (F12) for JavaScript errors
2. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
3. Clear browser cache
4. Check if `templates/index.html` exists in the container:
   ```bash
   docker compose exec app ls -la /app/templates/
   ```

### Complete Reset (Nuclear Option)

If nothing else works:
```bash
# Stop and remove everything
docker compose down -v

# Remove all HouseHunter images
docker rmi househunter-app

# Clear Docker cache
docker system prune -a

# Rebuild from scratch
docker compose up --build
```

---

## 🛠️ Project Structure

```
HouseHunter/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models & scoring logic
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Docker configuration
│   ├── templates/
│   │   └── index.html       # Main web interface
│   └── static/
│       └── styles.css       # Custom CSS (optional)
├── docker-compose.yml       # Docker Compose configuration
└── README.md               # This file
```

---

## 📝 Usage Guide

### Auto-Filling Property Details (Optional)

If you've set up RapidAPI (see setup instructions above):

1. **Enter an address** in the Address field
2. **Click the "🔍 Auto-Fill" button**
3. Wait a moment while the system looks up the property
4. **Property details auto-populate**:
   - ✅ Bedrooms
   - ✅ Bathrooms
   - ✅ Square feet
   - ✅ Lot size (acres)
   - ✅ Garage spaces
5. **Review and adjust** if needed
6. **Manually fill** subjective fields (backyard, privacy, appliances, etc.)

**Without RapidAPI:** Simply enter all fields manually as before.

### Adding a House

1. **Fill in basic information:**
   - Address (required)
   - Notes (optional - add thoughts, concerns, realtor info, etc.)

2. **Enter property details:**
   - Garage capacity (number of cars)
   - Bathrooms (number)
   - Bedrooms (number)
   - Square footage
   - Lot size in acres

3. **Select features:**
   - Nice backyard
   - Curb appeal
   - Deck
   - Patio potential
   - Pool
   - Near recreation areas
   - Walking distance to shopping

4. **Choose from dropdowns:**
   - Basement (None, Unfinished, Finished)
   - Privacy level (Very Private, Private, Normal, Not Private)

5. **Select appliances and their condition:**
   - Check each appliance present (Dishwasher, Range, Oven, Fridge, Washer, Dryer, Microwave)
   - Select Old (+1) or Modern (+2) for each

6. **HOA Information:**
   - Check if has HOA
   - Enter monthly HOA fee if applicable

7. **Click "Add House"**

The score is calculated automatically and the house appears in the list!

### Editing a House

1. Click the **"Edit"** button (green) on any house card
2. The form will populate with all existing data
3. Make your changes
4. Click **"Update House"** to save
5. Click **"Cancel Edit"** to abort changes

### Viewing Houses

- All houses are displayed **sorted by score (highest first)**
- Each card shows:
  - Address and notes
  - Total score (green for positive, red for negative)
  - Detailed breakdown of points by feature
  - Action buttons (View Details, Edit, Delete)

### Example Data

Click **"Load Example Houses"** to populate the app with 3 diverse sample houses showing different scoring scenarios.

### Clearing Data

Click **"Clear All Houses"** to remove all houses from both server memory and browser storage.

### Data Persistence

- **Browser Storage**: Houses are automatically saved to your browser's localStorage
- **Session Sync**: When you open the app, houses are loaded from localStorage to the server
- **Same Browser**: Your houses persist even after closing the browser
- **Different Browser/Device**: Houses are browser-specific (not synced across devices)

---

## 🐳 Docker Commands Reference

### Basic Commands

```bash
# Start the app (builds if needed)
docker compose up

# Start with forced rebuild
docker compose up --build

# Run in background (detached mode)
docker compose up -d

# Stop the app
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Logs and Debugging

```bash
# View logs (follow mode)
docker compose logs -f

# View logs for specific service
docker compose logs -f app

# View last 50 lines
docker compose logs --tail=50 app

# Check container status
docker compose ps

# Execute command in running container
docker compose exec app bash
```

### Maintenance

```bash
# Rebuild without cache
docker compose build --no-cache

# Restart services
docker compose restart

# Pull latest images (if using external images)
docker compose pull

# Remove unused Docker resources
docker system prune
docker system prune -a  # Remove all unused images
```

---

## 🌐 API Endpoints

### Web Interface
- `GET /` - Main web page

### House Management
- `POST /add_house` - Add a new house
- `GET /houses` - Get all houses (sorted by score, descending)
- `GET /house/{id}` - Get a specific house
- `PUT /house/{id}` - Update an existing house
- `DELETE /house/{id}` - Delete a house
- `GET /score/{id}` - Get detailed scoring breakdown

### Utility
- `POST /seed_data` - Load 3 example houses
- `DELETE /clear_all` - Clear all houses
- `POST /sync_houses` - Sync houses from browser localStorage (called automatically on page load)

### API Documentation
Visit `http://localhost:7777/docs` for interactive API documentation (Swagger UI)

### RapidAPI Integration
- `GET /lookup_address?address={address}` - Look up property details from Realtor.com via RapidAPI
  - Returns: bedrooms, bathrooms, square feet, lot size, garage spaces
  - Requires: RAPIDAPI_KEY environment variable
  - Free tier: 500 lookups/month

---

## 🔧 Development

### Run without Docker

1. **Install Python dependencies**

```bash
cd app
pip install -r requirements.txt
```

2. **Run the application**

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. **Access at http://localhost:8000**

---

## 🎨 Technologies Used

- **Backend**: FastAPI (Python)
- **Frontend**: HTML + Tailwind CSS (via CDN)
- **Database**: In-memory Python dictionary (session-based)
- **Containerization**: Docker + Docker Compose
- **UI Framework**: Tailwind CSS

---

## 📦 Dependencies

### Python (requirements.txt)
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation

### Frontend
- Tailwind CSS (loaded via CDN)
- Vanilla JavaScript (no framework needed)

---

## 💡 Tips & Best Practices

1. **Data Persistence**: 
   - Data is saved in your browser's localStorage automatically
   - Server memory is synced from localStorage on each page load
   - Use the same browser to maintain your house list
   - Export important data by taking screenshots or using browser dev tools

2. **Score Interpretation**:
   - **30+ points**: Excellent house with many desirable features
   - **20-29 points**: Very good house
   - **10-19 points**: Decent house with some good features
   - **0-9 points**: Basic house or has some negative factors
   - **Negative score**: Has significant drawbacks (usually high HOA fees or lack of key features)

3. **Using the Scoring System Effectively**:
   - Don't just look at total score - review the breakdown
   - Some features may be more important to you than the points suggest
   - Use notes to capture non-quantifiable factors (school district, commute time, neighborhood feel)

4. **Appliance Tracking**:
   - Check each appliance that comes with the house
   - Modern appliances score higher but old appliances still add value
   - This helps estimate move-in costs if appliances need replacement

5. **Privacy Levels Explained**:
   - **Very Private**: Large lot, no visible neighbors, wooded/fenced
   - **Private**: Some distance from neighbors, decent privacy
   - **Normal**: Standard suburban spacing
   - **Not Private**: Very close neighbors, no privacy

6. **Mobile Usage**: The interface is fully responsive - great for looking up houses on your phone while house hunting!

7. **Editing Houses**: Use the Edit feature to update information as you learn more about a property

---

## 🤝 Contributing

Feel free to fork, modify, and enhance! Some ideas:
- Add persistent database (PostgreSQL, MongoDB) for true multi-device sync
- Add user authentication and accounts
- Export houses to PDF/CSV/Excel
- Add photo uploads for each house
- Custom scoring weights (let users configure point values)
- Map integration to show house locations
- Comparison view (side-by-side house comparison)
- Price tracking and mortgage calculator integration

---

## 📄 License

This project is open source and available for personal or educational use.

---

## 🆘 Getting Help

If you encounter issues not covered in the troubleshooting guide:

1. **Check Docker is running**: Open Docker Desktop
2. **Verify port availability**: Make sure port 7777 is free
3. **Check logs**: Run `docker compose logs app` for error messages
4. **Try clean rebuild**: `docker compose down -v && docker compose up --build`
5. **Check browser console**: Press F12 and look for JavaScript errors
6. **Test API directly**: Visit `http://localhost:7777/docs` to test API endpoints

### Common Success Checklist
- ✅ Docker Desktop is running
- ✅ Port 7777 is available (or you changed it in docker-compose.yml)
- ✅ All files present in project directory
- ✅ `docker compose up --build` completed without errors
- ✅ Browser can access `http://localhost:7777`

---

## 🔍 Architecture Overview

**Frontend:**
- Single-page application (SPA) with vanilla JavaScript
- Tailwind CSS for styling
- Browser localStorage for data persistence

**Backend:**
- FastAPI framework (Python)
- Pydantic for data validation
- In-memory dictionary for session storage
- Automatic data sync from localStorage on page load

**Deployment:**
- Dockerized application
- Uvicorn ASGI server
- Port mapping: 7777 (host) → 8000 (container)

---

**Happy House Hunting! 🏡**

*Made with ❤️ for smart homebuyers*
