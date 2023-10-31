
# PyVerseAI

Welcome to PyVerseAI, a collection of versatile AI and cloud-based projects aimed at solving real-world challenges using cutting-edge technologies.

## Introduction

PyVerseAI is a hub of diverse projects, each with its unique purpose and tech stack. Whether you're interested in AI, cloud management, web scraping, or any other domain, PyVerseAI aims to provide a solution.

## Projects

### EC2-Crawler

The EC2-Crawler project is designed to scrape news from various sources and manage AWS EC2 instances. Key features include:
- Web scraping from multiple news sources.
- EC2 instance management using AWS SDK.
- Configuration-driven approach for scalability.

[Detailed setup and usage for EC2-Crawler](./EC2-Crawler/README.md)

### SensorHub-MQTT-Dockerized

SensorHub is an MQTT-based system simulating the behavior of sensors, monitoring their readings, and providing APIs to retrieve data based on specific criteria. Key features include:
- MQTT broker setup using Docker.
- Simulation of sensor readings with a Python MQTT client.
- Data storage in MongoDB and in-memory management using Redis.
- API endpoints to fetch sensor readings.

[Detailed setup and usage for SensorHub-MQTT-Dockerized](./SensorHub-MQTT-Dockerized/README.md)

### Tokenized-Session-APIs

`Tokenized-Session-APIs` is a backend system designed to manage and facilitate session bookings between students and deans in a university context. Key features include:
- User authentication and token-based security.
- API endpoints for session viewing and booking.
- Flexible database structure for user data and session management.

[Detailed setup and usage for Tokenized-Session-APIs](./Tokenized-Session-APIs/README.md)


### E-Commerce Scraper Suite

The E-Commerce Scraper Suite is a web scraping tool designed to extract product data from leading e-commerce platforms such as Amazon and Flipkart. This suite efficiently extracts details like item name, price, discount, image, and the product company name, storing them in a structured database. Key features include:
- Targeted scraping for Amazon and Flipkart.
- Structured data storage in a database.
- Configuration-driven approach for scraper settings.
- Integration with databases for efficient data storage.

[Detailed setup and usage for E-Commerce Scraper Suite](./E-Commerce-Scraper-Suite/README.md)

### Real-Time-Telemetry

A real-time telemetry system capturing and processing meter values from various charge points using MQTT.

[Detailed setup and usage for Real time telemetry](./Real-Time-Telemetry/README.md)


### Order-Flow-Chain

An order management system to simulate a pizza ordering process. The project allows users to create custom pizzas by choosing a base, a type of cheese, and multiple toppings. Once an order is placed, the system tracks the status of the order in real-time using asynchronous tasks.

[Detailed setup and usage for Order Flow Chain](./Order-Flow-Chain/README.md)


### Thermal Sensor Visualization

Embark on a journey through temperature landscapes with real-time thermal imaging. This project takes raw sensor data and transforms it into enlightening and interactive thermal visuals. Dive into:
- Converting raw data into 2D thermal imagery.
- Real-time visualization with dynamic color scales reflecting temperature gradients.
- Image enhancement techniques to sharpen clarity.
- Automated pinpointing of temperature extremities within the visuals.

[Learn more about Thermal Sensor Visualization](./Thermal-Sensor-Visualization/README.md)


### Raffle Rack Blueprint

The Raffle Rack Blueprint is a comprehensive solution designed to simulate a raffle draw system. Users can buy tickets, start new draws, and run raffles to determine winners. The project supports two modes:

- **Database mode**: Uses a PostgreSQL database to persistently store user data, tickets, and draw results.
- **In-memory mode**: A lightweight version that operates entirely in memory without any database dependencies.

Key features include:
- User ticket purchasing with ticket numbers displayed upon purchase.
- Dynamic pot size calculation based on the number of tickets bought.
- Raffle execution that determines winners based on ticket matches.
- Structured prize distribution based on the number of matches with the winning ticket.
- Comprehensive unittests ensuring the functionality and reliability of the system.

[Detailed setup and usage for Raffle Rack Blueprint](./Raffle-Rack-Blueprint/README.md)

### Power Activation Gateway

A backend service for managing and activating the 'Infinity Stones' powers, providing real-time feedback and persistent status tracking.

- Asynchronous task processing for efficient handling of activation requests.
- Real-time updates to users via WebSockets.
- Persistent storage of activation statuses and user interactions.

[Detailed setup and usage for Power Activation Gateway](./Power-Activation-Gateway/README.md)

### Verilog Hierarchy Analyzer

Verilog Hierarchy Analyzer is a Python tool designed to parse Verilog netlists, extract module hierarchies, and count instances of modules and primitives in the design. It provides insight into the composition of Verilog designs, aiding in understanding, debugging, and documenting digital circuits.

- Extracts the hierarchy of modules and their instances from a Verilog netlist.
- Counts the number of instances of each primitive and module in the specified hierarchy.
- Recognizes and counts various Verilog primitives such as `invN1`, `nand2N1`, and `nor2N1`.

[Detailed setup and usage for Verilog Hierarchy Analyzer](./Verilog-Hierarchy-Analyzer/README.md)

### Future Projects

Stay tuned for more exciting projects in the PyVerseAI universe!

## Setup and Configuration

Each project within PyVerseAI has its own setup and configuration instructions. Please refer to the respective project directories and their README files for detailed steps.

## Contribution

Contributions to PyVerseAI are always welcome. Whether it's enhancements to existing projects, bug fixes, documentation, or the addition of entirely new projects, your efforts are appreciated.
