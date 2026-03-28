import argparse

# Constants
PRIME_MESSAGE = "is a prime number"
NOT_PRIME_MESSAGE = "is not a prime number"

def is_prime(n: int) -> bool:
    """
    Checks if a number is prime.

    Args:
    n (int): The number to check.

    Returns:
    bool: True if the number is prime, False otherwise.
    """
    if n <= 1:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    max_divisor = int(n**0.5) + 1
    for d in range(3, max_divisor, 2):
        if n % d == 0:
            return False
    return True

def main() -> None:
    """
    Asks the user for a number and prints whether it is prime or not.
    """
    parser = argparse.ArgumentParser(description="Checks if a number is prime.")
    parser.add_argument("-n", type=int, help="The number to check.")
    args = parser.parse_args()
    if args.n is None:
        while True:
            try:
                num = int(input("Please enter a number: "))
                break
            except ValueError:
                print("Invalid input. Please enter a valid number.")
    else:
        num = args.n
    if is_prime(num):
        print(f"{num} {PRIME_MESSAGE}")
    else:
        print(f"{num} {NOT_PRIME_MESSAGE}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")