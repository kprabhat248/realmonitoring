from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel
import requests
import time
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import redis
from threading import Thread

# --- Configurations ---
API_KEY = "6aff3164b260b2d608235ea259cb903a"
REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql://postgres:12345@localhost/weatherdb"
CITIES = ["Delhi", "Mumbai", "Chennai", "Bangalore", "Kolkata", "Hyderabad"]

# Redis and PostgreSQL setup
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

# PostgreSQL setup
Base = declarative_base()
engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI()

# --- Database Models ---
class WeatherSummary(Base):
    __tablename__ = "weather_summary"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    avg_temp = Column(Float)
    max_temp = Column(Float)
    min_temp = Column(Float)
    dominant_condition = Column(String)
    date = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "weather_alerts"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    message = Column(String)
    date = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(bind=engine)

# --- Helper functions ---
def kelvin_to_celsius(kelvin_temp):
    return kelvin_temp - 273.15

def fetch_weather_data(city: str):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def process_weather_data(city: str, data: dict):
    temp_celsius = kelvin_to_celsius(data['main']['temp'])
    weather_condition = data['weather'][0]['main']

    # Ensure values from Redis are converted to float
    max_temp_redis = redis_client.get(f"{city}_max_temp")
    min_temp_redis = redis_client.get(f"{city}_min_temp")

    max_temp = max(float(max_temp_redis) if max_temp_redis else float('-inf'), temp_celsius)
    min_temp = min(float(min_temp_redis) if min_temp_redis else float('inf'), temp_celsius)

    summary = {
        "temp_celsius": temp_celsius,
        "weather_condition": weather_condition,
        "max_temp": max_temp,
        "min_temp": min_temp
    }

    redis_client.set(f"{city}_current_temp", temp_celsius, ex=300)  # Cache for 5 minutes
    redis_client.set(f"{city}_max_temp", summary["max_temp"], ex=86400)  # Cache for 1 day
    redis_client.set(f"{city}_min_temp", summary["min_temp"], ex=86400)  # Cache for 1 day
    redis_client.set(f"{city}_weather_condition", weather_condition, ex=300)

    # Update daily weather summary in PostgreSQL
    update_weather_summary(city, summary)

    # Check for alerts
    check_threshold(city, summary)

def check_threshold(city: str, summary: dict):
    threshold = 35  # Default alert threshold (can be made dynamic)
    if summary["temp_celsius"] > threshold:
        alert_message = f"ALERT: Temperature in {city} exceeded {threshold}°C! Current temperature: {summary['temp_celsius']:.2f}°C"
        store_alert(city, alert_message)

def store_alert(city: str, message: str):
    redis_client.lpush(f"{city}_alerts", message)  # Store alert in Redis
    redis_client.expire(f"{city}_alerts", 86400)  # Expire after 1 day

    # Store alert in PostgreSQL for persistence
    with SessionLocal() as db:
        new_alert = Alert(city=city, message=message)
        db.add(new_alert)
        db.commit()

def update_weather_summary(city: str, summary: dict):
    # Store daily weather summary in PostgreSQL
    with SessionLocal() as db:
        result = db.execute(select(WeatherSummary).filter_by(city=city)).first()
        db_summary = result[0] if result else None  # Unpack the row

        if not db_summary:
            db_summary = WeatherSummary(
                city=city,
                avg_temp=summary['temp_celsius'],
                max_temp=summary['max_temp'],
                min_temp=summary['min_temp'],
                dominant_condition=summary['weather_condition']
            )
            db.add(db_summary)
        else:
            db_summary.avg_temp = (db_summary.avg_temp + summary['temp_celsius']) / 2
            db_summary.max_temp = max(db_summary.max_temp, summary['max_temp'])
            db_summary.min_temp = min(db_summary.min_temp, summary['min_temp'])
            db_summary.dominant_condition = summary['weather_condition']
        db.commit()


# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    # Start monitoring in a background thread
    start_weather_monitoring()

def start_weather_monitoring():
    # Run weather monitoring task in the background
    def monitor():
        while True:
            for city in CITIES:
                data = fetch_weather_data(city)
                if data:
                    process_weather_data(city.strip(), data)
            time.sleep(300)  # Poll every 5 minutes

    thread = Thread(target=monitor)
    thread.daemon = True
    thread.start()

@app.get("/weather/{city}")
def get_weather_summary(city: str):
    # First try to fetch from Redis
    current_temp = redis_client.get(f"{city}_current_temp")
    max_temp = redis_client.get(f"{city}_max_temp")
    min_temp = redis_client.get(f"{city}_min_temp")
    weather_condition = redis_client.get(f"{city}_weather_condition")

    if current_temp:
        return {
            "city": city,
            "current_temp": float(current_temp),
            "max_temp": float(max_temp),
            "min_temp": float(min_temp),
            "dominant_condition": weather_condition
        }
    else:
        # Fetch from PostgreSQL if not in Redis
        with SessionLocal() as db:
            result = db.execute(select(WeatherSummary).filter_by(city=city)).first()
            db_summary = result[0] if result else None
            if db_summary:
                return {
                    "city": city,
                    "avg_temp": db_summary.avg_temp,
                    "max_temp": db_summary.max_temp,
                    "min_temp": db_summary.min_temp,
                    "dominant_condition": db_summary.dominant_condition
                }
            return {"error": "No data found for the city"}

@app.get("/alerts/{city}")
def get_alerts(city: str):
    # Fetch alerts from Redis
    alerts = redis_client.lrange(f"{city}_alerts", 0, -1)
    if alerts:
        return {"city": city, "alerts": alerts}

    # If no alerts in Redis, fetch from PostgreSQL
    with SessionLocal() as db:
        db_alerts = db.execute(select(Alert).filter_by(city=city)).all()
        if db_alerts:
            return {"city": city, "alerts": [alert.message for alert in db_alerts]}
        return {"city": city, "alerts": []}
