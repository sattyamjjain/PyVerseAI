
# SensorHub: MQTT and Docker Integration

A system to simulate the behavior of sensors, monitor their readings, and provide APIs to retrieve data.

## Setup and Usage

1. **Prerequisites**: Ensure you have Docker and Docker Compose installed on your machine.
2. Clone this repository: `git clone https://github.com/sattyamjjain/PyVerseAI.git`
3. Navigate to the project directory: `cd SensorHub-MQTT-Dockerized`
4. Build and start the services: `docker-compose up -d`
5. The FastAPI application will be available at `http://localhost:8000/`. You can access the API documentation at `http://localhost:8000/docs`.

## Service Overview

- **Mosquitto**: An MQTT broker for handling sensor data publication and subscription.
- **MongoDB**: Database used to store sensor readings.
- **Redis**: In-memory database to store the latest ten sensor readings.
- **Publisher**: Python application to simulate and publish random sensor readings.
- **Subscriber**: Python application to subscribe to sensor readings and store them in MongoDB and Redis.
- **API**: FastAPI application to provide endpoints for fetching sensor data.

## API Endpoints

- Fetch sensor readings by date range: `GET /readings/?start_date=<start_date>&end_date=<end_date>`
- Retrieve the last ten readings for a sensor: `GET /latest_readings/<sensor_type>`

## Design Rationale

- **FastAPI**: Chosen for its asynchronous nature, which can handle numerous concurrent requests efficiently.
- **MQTT**: Suitable for IoT applications, ensuring lightweight and efficient real-time communication.
- **MongoDB**: Flexible schema to store varied sensor data.
- **Redis**: Fast in-memory storage for quick retrieval of the latest readings.

## Challenges and Solutions

- **Challenge**: Ensuring real-time data flow from publisher to subscriber.
  - **Solution**: Leveraged MQTT's QoS levels to ensure message delivery.
  
- **Challenge**: Storing the latest readings efficiently.
  - **Solution**: Utilized Redis lists to keep the most recent sensor data at the fingertips.
