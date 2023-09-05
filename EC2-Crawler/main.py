import ec2_manager
import crawler
import config
import utils

_logger = utils.get_logger(__name__)


def main():
    _logger.info("Welcome to the EC2-Crawler Application!")
    while True:
        _logger.info("\nChoose an action:")
        _logger.info("1. Manage EC2 Instances")
        _logger.info("2. Scrape Y Combinator News")
        _logger.info("3. Exit")

        choice = input("Enter your choice (1/2/3): ")

        if choice == "1":
            while True:
                _logger.info("\nEC2 Manager options:")
                _logger.info("1. Launch a new EC2 instance")
                _logger.info("2. Stop an EC2 instance")
                _logger.info("3. Start an EC2 instance")
                _logger.info("4. Return to main menu")

                ec2_choice = input("Enter your choice (1/2/3/4): ")

                if ec2_choice == "1":
                    ec2_manager.launch_new_instance()
                    _logger.info("Instance launched successfully!")

                elif ec2_choice == "2":
                    instance_id = input("Enter the instance ID to stop: ")
                    ec2_manager.stop_instance(instance_id)
                    _logger.info(f"Instance {instance_id} stopped successfully!")

                elif ec2_choice == "3":
                    instance_id = input("Enter the instance ID to start: ")
                    ec2_manager.start_instance(instance_id)
                    _logger.info(f"Instance {instance_id} started successfully!")

                elif ec2_choice == "4":
                    break
                else:
                    _logger.warning(
                        "Invalid EC2 manager choice. Please choose a valid option."
                    )

        elif choice == "2":
            _logger.info("Starting web scraping...")
            crawler.fetch_news_data(config.WEB_URL)
            _logger.info("Web scraping completed. Check the JSON file for results.")

        elif choice == "3":
            _logger.info("Exiting the application. Goodbye!")
            break
        else:
            _logger.warning("Invalid choice. Please choose a valid option.")


if __name__ == "__main__":
    main()
