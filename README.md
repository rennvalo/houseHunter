# 🏠 HouseHunter

**A FastAPI-based web application that helps you make smart house decisions using a point-based scoring system.**

HouseHunter lets you track potential houses, rate them based on key features (garage, bedrooms, bathrooms, backyard, etc.), and compare scores to make data-driven decisions.

---

## ✨ Features

- **Add Houses**: Input address, features, and notes
- **Automatic Scoring**: Each house gets a score based on a point system
- **Compare Houses**: View all houses sorted by score
- **Session-Based**: All data is stored in-memory (resets on restart)
- **Modern UI**: Clean Tailwind CSS interface with house-themed background
- **Docker Ready**: Run everything with a single command

---

## 📊 Scoring System

| Feature | Description | Points |
|---------|-------------|--------|
| **Garage** | Has garage | +1 |
| | Two-car garage | +2 |
| | No garage | -1 |
| **Bathrooms** | 2 bathrooms | +1 |
| | 3+ bathrooms | +2 |
| **Bedrooms** | 2 bedrooms | +1 |
| | 3 bedrooms | +2 |
| | 4+ bedrooms | +4 |
| **Backyard** | Nice backyard | +2 |
| **Curb Appeal** | Has curb appeal | +1 |
| **Appliances** | Modern appliances | +1 |

---

## 🚀 Quick Start

### Prerequisites

- Docker
- Docker Compose

### Run the Application

1. **Clone or navigate to the project directory**

```bash
cd HouseHunter
```

2. **Start the application**

```bash
docker compose up --build
```

3. **Open your browser**

Navigate to: **http://localhost:7777**

4. **Start rating houses!**

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

## 📝 Usage

### Adding a House

1. Fill in the address (required)
2. Add any notes (optional)
3. Select features:
   - Garage options
   - Number of bathrooms
   - Number of bedrooms
   - Other amenities (backyard, curb appeal, appliances)
4. Click "Add House"

The score is calculated automatically!

### Viewing Houses

- All houses are displayed sorted by score (highest first)
- Each card shows:
  - Address and notes
  - Total score
  - Breakdown of points by feature
  - Actions (View Details, Delete)

### Example Data

Click **"Load Example Houses"** to populate the app with 3 sample houses.

### Clearing Data

Click **"Clear All Houses"** to remove all houses and start fresh.

---

## 🐳 Docker Commands

### Start the app
```bash
docker compose up
```

### Start with rebuild
```bash
docker compose up --build
```

### Run in background
```bash
docker compose up -d
```

### Stop the app
```bash
docker compose down
```

### View logs
```bash
docker compose logs -f
```

---

## 🌐 API Endpoints

### Web Interface
- `GET /` - Main web page

### House Management
- `POST /add_house` - Add a new house
- `GET /houses` - Get all houses (sorted by score)
- `GET /house/{id}` - Get a specific house
- `DELETE /house/{id}` - Delete a house
- `GET /score/{id}` - Get detailed scoring breakdown

### Utility
- `POST /seed_data` - Load example houses
- `DELETE /clear_all` - Clear all houses

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

## 💡 Tips

1. **Session-based storage**: Data is stored in memory and resets when the app restarts. This is intentional for privacy and simplicity.

2. **Garage logic**: Selecting "Two-car garage" automatically checks "Has garage"

3. **Score interpretation**:
   - Positive score (green) = Good house
   - Negative score (red) = May need compromises

4. **Mobile-friendly**: The interface is responsive and works on phones/tablets

---

## 🤝 Contributing

Feel free to fork, modify, and enhance! Some ideas:
- Add persistent database (PostgreSQL, MongoDB)
- Add user authentication
- Export houses to PDF/CSV
- Add photos for each house
- Custom scoring weights

---

## 📄 License

This project is open source and available for personal or educational use.

---

## 🙋 Support

If you encounter any issues:
1. Check that Docker is running
2. Ensure port 7777 is not in use
3. Try `docker compose down` and `docker compose up --build`

---

**Happy House Hunting! 🏡**
