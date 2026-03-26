```python
import argparse
import sys

# Constants
SCRIPT_NAME = "Main Script"
VERSION = "1.0.0"

def main() -> None:
    """
    Main function to start the script.
    """
    try:
        # Define command line arguments
        parser = argparse.ArgumentParser(description=SCRIPT_NAME)
        parser.add_argument("--version", action="version", version=f"{SCRIPT_NAME} {VERSION}")
        args = parser.parse_args()

        # Main script logic
        print(f"{SCRIPT_NAME} {VERSION} started successfully.")

    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```