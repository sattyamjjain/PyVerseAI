## Real-Time-Telemetry

## Description
A real-time telemetry system that captures and processes meter values from various charge points using MQTT. The system consists of an MQTT broker, server, and mock clients that simulate meter value transmissions. Data received is stored in a PostgreSQL database and can be retrieved via API endpoints.

## Table of Contents
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
- [Usage](#usage)
  - [Starting the MQTT Broker](#starting-the-mqtt-broker)
  - [Running the Server](#running-the-server)
  - [Running the Client](#running-the-client)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)

## Installation

### Prerequisites
- Python 3.x
- PostgreSQL
- MQTT Broker (e.g., Mosquitto)

### Setup
1. Clone the repository.
2. Navigate to the `Real-Time-Telemetry` directory.
3. Install the required Python packages: `pip install -r requirements.txt`.
4. Ensure PostgreSQL is set up and running.
5. Configure the database connection in `config.yaml`.

## Usage

### Starting the MQTT Broker
Ensure the MQTT broker (e.g., Mosquitto) is running on localhost.

### Running the Server
Navigate to the `mqtt` directory within `Real-Time-Telemetry` and run:
```
python server.py
```

### Running the Client
In the same `mqtt` directory, run:
```
python client.py
```
This will simulate meter value transmissions from mock clients.

## API Endpoints
- **List Endpoint**: Returns data in a paginated format. Can be filtered by charge point IDs.
- **Detail Endpoint**: Returns complete data for a single record.

## Project Structure
- `mqtt`: Contains the MQTT server and client scripts.
- `db.py`: Contains database operations and configurations.
- `config.py`: Configuration loader.
- `utils.py`: Contains utility functions, including logging setup.
- API scripts and modules.

### Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Ensure you update tests as appropriate.
