import os
import time


def main():
    print("[worker] stub ready")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("[worker] stopping")


if __name__ == "__main__":
    main()

