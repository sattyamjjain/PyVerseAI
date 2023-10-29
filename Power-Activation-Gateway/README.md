
# Power Activation Gateway

This backend service allows users to activate the powers of the 'Infinity Stones' by making requests to the API. The service handles activation requests asynchronously, provides real-time updates through WebSockets, and tracks the activation statuses using a persistent database.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Real-time Communication](#real-time-communication)
- [Environment Variables](#environment-variables)
- [Database](#database)
- [Running the Application](#running-the-application)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package installer)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/sattyamjjain/PyVerseAI.git
   ```
2. Navigate to the project directory:
   ```bash
   cd Power-Activation-Gateway
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To use the service, start the Flask application and Celery worker. Then, make HTTP requests to the API endpoint to activate stone powers, and connect to the WebSocket to receive real-time updates.

## API Reference

### Activate Stone Power

```http
POST /activate
```

```json
{
    "stone_id": "5235",
    "user_id": "21431",
    "power_duration":10
}
```

## Real-time Communication

The service provides real-time updates on the status of stone power activations via WebSockets. Connect to the WebSocket at `ws://[server address]:5000` to receive updates.

## Environment Variables

- `BROKER_URL`: URL for the Celery broker
- `DATABASE_URL`: URL for the database connection

## Database

The service uses a SQL database to track the activation statuses of the infinity stones. The database schema includes fields such as `stone_id`, `user_id`, `activation_start`, and `activation_end`.

## Running the Application

1. Start the Flask application:
   ```bash
   python main.py
   ```
2. Start the Celery worker:
   ```bash
   celery -A main.celery worker --loglevel=info
   ```

## Tech Stack

- Flask: Web framework
- Celery: Asynchronous task queue
- SQLAlchemy: SQL toolkit and ORM
- Flask-SocketIO: Flask extension for handling WebSockets

## Contributing

Contributions are welcome! If you have suggestions or want to improve the code, feel free to create an issue or submit a pull request.
