
## E-Commerce Scraper Suite

---

### Introduction

The E-Commerce Scraper Suite is a web scraping tool designed to extract product data from leading e-commerce platforms such as Amazon and Flipkart. This suite efficiently extracts details like item name, price, discount, image, and the product company name, storing them in a structured database.

### Features

- **Targeted Scraping**: Specifically designed to extract data from Amazon and Flipkart.
- **Structured Data Storage**: Extracted data is stored in a structured database format.
- **Configurable**: Use the provided `config.yaml` file to manage your scraping preferences.
- **Database Integration**: The suite integrates with databases to store extracted data efficiently.

### Installation & Setup

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/sattyamjjain/PyVerseAI.git
    cd E-Commerce-Scraper-Suite
    ```

2. **Install Required Packages**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Configuration**:
    - Edit the `config.yaml` file as per your requirements. This includes database configurations, target URLs, and other scraping preferences.
    - Make sure your database is up and running.

### Usage

To start the scraper:

```bash
python main.py
```

### Modules & Files

- `main.py`: The primary script to initiate the scraping process.
- `db.py`: Handles database operations.
- `config.yaml`: Configuration file to manage scraper settings.
- `config.py`: Script to parse the configuration file and make it accessible in the project.
- `utils.py`: Contains utility functions that assist in data extraction and other processes.

### Note

This project is primarily focused on showcasing code quality, approach, library usage, and data extraction techniques rather than the output. Always ensure you have the necessary permissions and adhere to the platform's `robots.txt` file and terms of service when scraping.

### Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Ensure you update tests as appropriate.

---