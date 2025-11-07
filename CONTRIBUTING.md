# Contributing to AI News Hub

Thank you for considering contributing to AI News Hub! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check the [existing issues](https://github.com/larry311012/ai-news-hub/issues) to avoid duplicates
- Use the latest version to verify the bug still exists

When filing a bug report, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/Node versions)
- Relevant logs or error messages

### Suggesting Features

Feature requests are welcome! Please:
- Check [GitHub Discussions](https://github.com/larry311012/ai-news-hub/discussions) first
- Provide a clear use case and expected behavior
- Consider implementation complexity and project scope

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with clear commit messages:
   ```
   feat: add Twitter thread support
   fix: resolve OAuth callback issue
   docs: update installation guide
   ```
4. **Add tests** for new functionality
5. **Run the test suite**:
   ```bash
   cd backend
   pytest
   ```
6. **Format your code**:
   ```bash
   black .
   flake8 .
   ```
7. **Push** to your fork and **submit a pull request**

### Development Setup

See [Installation](README.md#installation) in the README for detailed setup instructions.

Quick start:
```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest  # Run tests

# Frontend
cd frontend
npm install
npm run test
```

### Coding Standards

**Python (Backend)**:
- Follow PEP 8 style guide
- Use `black` for formatting (line length: 100)
- Add type hints for function signatures
- Write docstrings for public APIs
- Maintain test coverage above 70%

**JavaScript (Frontend)**:
- Follow Vue 3 Composition API patterns
- Use `prettier` for formatting
- Write unit tests for components
- Keep components under 300 lines

### Commit Message Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(oauth): add GitHub OAuth support
fix(api): resolve rate limiting issue
docs(readme): update installation steps
```

### Testing

- Write tests for all new features
- Ensure all tests pass before submitting PR
- Aim for 70%+ code coverage
- Include integration tests for API changes

### Security

**Do not** open public issues for security vulnerabilities. Instead:
- Email security concerns to: larry311012@users.noreply.github.com
- We will respond within 48 hours
- We follow responsible disclosure practices

### Code Review Process

1. Maintainers will review your PR within 3-5 business days
2. Address any requested changes
3. Once approved, your PR will be merged
4. Contributors will be added to the acknowledgments

### Community Guidelines

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions.

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes (for significant contributions)
- Project README acknowledgments section

## Questions?

- Join our [Discord community](https://discord.gg/ainewshub) (coming soon)
- Start a [GitHub Discussion](https://github.com/larry311012/ai-news-hub/discussions)
- Check existing [documentation](docs/)

Thank you for contributing! 🎉
