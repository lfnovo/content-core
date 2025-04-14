# Contributing to Content-Core

Thank you for your interest in contributing to Content-Core! This guide will help you get started with the contribution process.

## Code of Conduct

In the interest of fostering an open and welcoming environment, we expect all contributors to be respectful and considerate of others. By participating in this project, you agree to:

- Be respectful of different viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

- Ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/lfnovo/content-core/issues).
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/lfnovo/content-core/issues/new).
- Include a clear title and description.
- Add as much relevant information as possible, including:
  - Steps to reproduce the issue
  - Expected behavior
  - Actual behavior
  - System details (OS, Python version, etc.)

### Suggesting Enhancements

- Open an issue with the tag "enhancement" to suggest new features or improvements.
- Clearly describe the enhancement and its benefits.

### Code Contributions

1. **Fork the Repo**: Fork the project repository to your own GitHub account.
2. **Clone the Repo**: Clone the forked repository to your local machine.
3. **Create a Branch**: Create a branch with a descriptive name related to the feature or bug you're working on.
4. **Make Changes**: Make your changes to the codebase. Ensure your code follows the project's coding style and conventions.
5. **Test Your Changes**: Make sure your changes pass all tests. Add tests if you're introducing new functionality.
6. **Commit Your Changes**: Commit your changes with a clear and descriptive commit message.
7. **Push to Your Fork**: Push your changes to your forked repository.
8. **Submit a Pull Request**: Create a pull request from your fork to the main project repository. Provide a clear description of your changes and why they are needed.

### Pull Request Guidelines

- Ensure your PR addresses a single issue or feature.
- Update documentation if your changes affect it.
- Reference related issues in your PR description.
- Be prepared to make changes based on feedback from maintainers.

## Development Setup

To set up the development environment:

1. Install Python 3.10 or later.
2. Install `uv` for package management:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Clone the repository and navigate to the project directory.
4. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   uv sync
   ```
5. Run tests to ensure everything is set up correctly:
   ```bash
   uv run pytest
   ```

## Coding Style

We follow PEP 8 for Python code. Please ensure your code adheres to these guidelines. Use tools like `flake8` or `pylint` to check your code style.

## License

By contributing to Content-Core, you agree that your contributions will be licensed under the [MIT License](LICENSE).

Thank you for contributing to Content-Core and helping make it better!
