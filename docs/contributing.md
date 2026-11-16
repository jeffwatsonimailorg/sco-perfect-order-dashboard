# Contributing to your project

This is a default guide to contributing to open source projects. If you're reading this in a project, please customize it to match the project's standards.

In general, certain features of GitHub have been disabled. For example, "Issue" are disabled as Intermountain emphasizes the use of Jira or Service Now for issue tracking. The wiki is also disabled as Intermountain uses Confluence or SharePoint for documentation. Likewise, the "Projects" feature is disabled as Intermountain uses Jira and / or Service Now for project management.

Standards for the following should be documented:
- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Project Development GitFlow

We use a specific Git workflow that helps us manage development and release smoothly. Here's an overview of our branch hierarchy and workflow:

- **Main Branch**: Our production branch. All deployment-ready code lives here.
- **Develop Branch**: Our development branch where we merge feature branches for testing.
- **Release Branch**: Branch off from develop for final checks and adjustments before merging into main.
- **Feature Branches**: All new features should be developed in their own branch, branched off from develop.

## Branching Strategy

### Getting Started

1. If you are not on the development team for this branch, please fork the repo and create your branch from `develop`.
2. If you are a member of the development team, create your branch from `develop` instead of forking the repo.
3. If you've added code that should be tested, add tests.
4. Ensure the test suite passes.
5. Make sure your code lints.

### Making Changes

1. **Create a feature branch**: Branch from `develop` and name it to reflect the feature or issue you're addressing.

    ```bash
    git checkout -b feature/<your_feature_name> develop
    ```

2. **Make your changes**: Implement your feature or bug fix.

3. **Keep your branch updated**: Regularly pull in the latest changes from the develop branch to avoid conflicts.

    ```bash
    git pull origin develop
    ```

4. **Commit your changes**: Make sure your commits are clear and follow the project's commit message conventions.

### Submitting Changes

1. **Push your changes**: Upload your branch to GitHub.

    ```bash
    git push origin feature/<your_feature_name>
    ```

2. **Open a Pull Request (PR)**: Go to the repository on GitHub and open a new pull request from your feature branch to the develop branch. Provide a detailed description of your changes and reference any related issue numbers.

### After Your Pull Request is Merged

After your pull request is merged, you can pull the changes from develop to your local repo and delete your feature branch if you wish.

## Reporting Bugs

Create a Jira issue to report bugs. Be as descriptive as possible and include as much information as you can. Screenshots and step-by-step instructions are greatly appreciated.

## Proposing Features

We welcome feature proposals. Please:
1. Fork the repo and create your branch from `develop`.
2. Write up your idea in a clear and persuasive manner.
3. Submit a pull request, referencing any relevant issues.

## Questions or Additional Help

If you need further assistance or have any questions, feel free to open a Jira issue or contact a project maintainer.

Thank you for contributing to our project!
