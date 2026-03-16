# Contributing to AutoRAG Architect

First off, thank you for considering contributing to AutoRAG Architect! It's people like you that make AutoRAG Architect such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, make one! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

## Fork & create a branch

If this is something you think you can fix, then fork AutoRAG Architect and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-milvus-support
```

## Get the test suite running

Make sure you're using Python 3.10+. We recommend using a virtual environment:

```sh
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
make setup
```

## Implement your fix or feature

At this point, you're ready to make your changes. Feel free to ask for help; everyone is a beginner at first.

## Running Tests and Linting

Before pushing your changes, please run the test suite and ensure all linters pass:

```sh
make lint
make test
```

We use `black`, `isort`, `ruff`, and `mypy` natively configured in `pre-commit` to maintain codebase quality.

## Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with AutoRAG Architect's master branch. Then rebase your feature branch on top of it.

Finally, push your branch to GitHub and create a Pull Request.
