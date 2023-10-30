# Power Activation Gateway

## Description

The Power Activation Gateway is a backend service designed to manage and activate the powers of the 'Infinity Stones'. Users can interact with the service to activate the unique powers of each stone, with real-time updates provided through WebSockets. The service is built using Flask, Celery, and Flask-SocketIO.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [API Endpoints](#api-endpoints)
5. [WebSocket Events](#websocket-events)
6. [Running the Application](#running-the-application)
7. [Testing](#testing)

## Installation

To set up the project on your local machine, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/sattyamjjain/PyVerseAI.git
   cd Power-Activation-Gateway
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Update the database URL and Celery configurations in the `config.yaml`.

## Usage

### API Endpoints

- **Activate Stone Power**: `POST /activate`
  - **Parameters**:
    - `stone_id`: The unique identifier of the stone.
    - `user_id`: The ID of the user making the activation request.
    - `power_duration`: The duration (in seconds) the power should remain active.

### WebSocket Events

- **Connect**: Establish a WebSocket connection.
- **Disconnect**: Disconnect from the WebSocket server.
- **Authenticate**: Send authentication credentials.
- **Activation Update**: Receive real-time updates on stone power activations.

## Running the Application

1. Start the Flask application:
   ```
   python3 main.py
   ```

2. Start the Celery worker:
   ```
   celery -A main.celery worker --loglevel=info
   ```

3. Start the WebSocket client (optional):
   ```
   python socket_client.py
   ```

## Testing

Describe how to run the automated tests for this system.
