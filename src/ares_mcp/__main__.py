from .server import mcp


def main() -> None:
    mcp.run()  # stdio by default


if __name__ == "__main__":
    main()
