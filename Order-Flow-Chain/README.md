
# Order-flow-chain

## Introduction
The `Order-flow-chain` system is designed for a pizzeria, allowing customers to select various pizza components and place orders. It also provides an asynchronous task for tracking the status of orders as they progress through different stages.

## Features
1. **Pizza Customization**: Customers can choose:
    - 1 type of pizza base out of 3 choices.
    - 1 type of cheese out of 4 choices.
    - 5 toppings out of 7 choices.
2. **Order Placement**: Generate an order with the selected pizza details. Multiple pizzas can be included in a single order.
3. **Order Tracking**: Asynchronous task to change the order status based on time:
    - From `Placed` to `Accepted` in 1 minute.
    - From `Accepted` to `Preparing` in 1 minute.
    - From `Preparing` to `Dispatched` in 3 minutes.
    - From `Dispatched` to `Delivered` in 5 minutes.

## Installation & Setup
1. Ensure you have Docker and Docker-compose installed on your machine.
2. Clone the repository.
3. Navigate to the root directory.
4. Run the command:
    ```bash
    docker-compose up -d
    ```
5. The application should be up and running. Access the API endpoints as per the documentation.

## Project Structure
The main components of the project are:
- `orderflowchain`: The main Django project folder containing settings, URLs, and other configurations.
- `pizzas`: Django app containing models, views, serializers, and other related components for the pizza ordering system.
- `Dockerfile` and `docker-compose.yml`: Configuration files for containerizing the application.

## Further Information
- **Database**: The project uses a MySQL database hosted in a Docker container.
- **Asynchronous Tasks**: Implemented using Celery.

### **Contribution**:
Contributions to `Order-Flow-Chain` are welcome! Whether it's feature enhancements, bug fixes, or documentation improvements, your inputs are valued.
