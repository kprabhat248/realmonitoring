# Weather Monitoring API

This application is a FastAPI-based weather monitoring system that fetches weather data for multiple cities, stores the data in PostgreSQL, and uses Redis for caching. It also sends alerts when the temperature exceeds a specified threshold. 

## Features

- Fetch current weather data from OpenWeatherMap API. 
- Store daily weather summaries in PostgreSQL. 
- Cache current temperature, max/min temperatures, and weather conditions in Redis. 
- Generate alerts when the temperature exceeds a predefined threshold. 
- Retrieve weather summaries and alerts via RESTful API endpoints. 

## Technologies Used

- **FastAPI**: Web framework for building the API. 
- **SQLAlchemy**: ORM for interacting with PostgreSQL. 
- **Redis**: In-memory data structure store for caching. 
- **OpenWeatherMap API**: Service for fetching weather data. 

## Configuration

Before running the application, set the following environment variables or update the constants in the code: 

- `API_KEY`: Your OpenWeatherMap API key. 
- `REDIS_URL`: URL for your Redis instance (default: `redis://localhost:6379`). 
- `POSTGRES_URL`: Connection string for your PostgreSQL database (default: `postgresql://postgres:12345@localhost/weatherdb`).
  
You can view the interactive API documentation at http://localhost:8000/docs. This page provides detailed information about all available endpoints and how to use them.

You can configure the list of cities to monitor by updating the `CITIES` variable in the code: 

```python
CITIES = ["Delhi", "Mumbai", "Chennai", "Bangalore", "Kolkata", "Hyderabad"]
Database Setup

Create a PostgreSQL database (e.g., weatherdb).
Run the application to automatically create the necessary tables.
Make sure Redis is installed and running on your local machine. You can start it using the command:

bash
Copy code
redis-server
Installation

Clone the repository:
bash
Copy code
git clone https://github.com/yourusername/weather-monitoring-api.git 
cd weather-monitoring-api
Create a virtual environment and activate it:
bash
Copy code
python -m venv venv 
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
Install the required packages:
bash
Copy code
pip install fastapi[all] sqlalchemy redis requests
Running the Application

To start the FastAPI server, run the following command:

bash
Copy code
uvicorn main:app --reload
The API will be available at http://localhost:8000.

API Endpoints

Get Weather Summary
Retrieve the current weather summary for a specified city:

bash
Copy code
GET /weather/{city}
Example:

bash
Copy code
GET /weather/Delhi
Get Weather Alerts
Retrieve weather alerts for a specified city:

bash
Copy code
GET /alerts/{city}
Example:

bash
Copy code
GET /alerts/Delhi
Background Tasks

The application continuously monitors the weather in the specified cities in a background thread, updating the database and Redis cache every 5 minutes.

License

This project is licensed under the MIT License.
Accessing API Documentation

You can view the interactive API documentation at http://localhost:8000/docs. This page provides detailed information about all available endpoints and how to use them.


