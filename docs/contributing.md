# Contributing to your project

This guide outlines the contribution standards for the AI Center of Excellence (AI CoE) ML model deployment template project.

In general, certain features of GitHub have been disabled. For example, "Issues" are disabled as Intermountain emphasizes the use of Jira or Service Now for issue tracking. The wiki is also disabled as Intermountain uses Confluence or SharePoint for documentation. Likewise, the "Projects" feature is disabled as Intermountain uses Jira and/or Service Now for project management.

Standards for the following should be documented:
- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Project Development GitFlow

We use a specific Git workflow designed for ML model deployments that integrates with our CI/CD pipeline. Here's an overview of our branch hierarchy and workflow:

- **Main Branch**: All new branches should be created using main.
- **Release Branches**: Branches prefixed with `release/` are used for production deployments. Code merged into release branches is automatically deployed to the production workspace.
- **Feature Branches**: All new features, bug fixes, and model configuration changes should be developed in their own branch.

## Branching Strategy

### Getting Started

1. If you are not on the development team for this project, please fork the repo and create your branch from `main`.
2. If you are a member of the development team, create your branch from `main` instead of forking the repo.
3. If you've added code that should be tested, add tests.
4. Ensure the test suite passes.
5. Make sure your code lints and follows project standards.

### Making Changes

1. **Create a feature branch**: Branch from `main` and name it to reflect the feature, bug fix, or configuration change you're addressing.

    ```bash
    git checkout -b feature/<your_feature_name> main
    ```

    Examples:
    ```bash
    git checkout -b feature/update-model-config main
    git checkout -b bugfix/fix-deployment-issue main
    git checkout -b config/update-serving-endpoint main
    ```

2. **Make your changes**: Implement your feature or bug fix.

3. **Keep your branch updated**: Regularly pull in the latest changes from the main branch to avoid conflicts.

    ```bash
    git pull origin main
    ```

4. **Commit your changes**: Make sure your commits are clear and follow the project's commit message conventions.

### Testing Your Changes

Before submitting a pull request:

1. **Local Testing**: Test your changes locally using the dev environment:
   ```bash
   cd PROJECT_NAME_CHANGE_ME
   databricks bundle validate
   databricks bundle deploy
   ```

2. **Integration Testing**: Pull requests automatically trigger integration tests that:
   - Run unit tests for any Python code
   - Deploy ML model resources to the test environment in the staging workspace
   - Validate model deployment and configuration

### Submitting Changes

1. **Push your changes**: Upload your branch to GitHub.

    ```bash
    git push origin feature/<your_feature_name>
    ```

2. **Open a Pull Request (PR)**: Go to the repository on GitHub and open a new pull request from your feature branch to the `main` branch. 

   **Important**: PRs must target the `main` branch, not `develop`. This triggers:
   - Automated unit tests
   - Integration tests in the staging workspace
   - ML model resource validation

3. **PR Description**: Provide a detailed description including:
   - What changes were made
   - Why the changes were necessary
   - Any configuration updates
   - Testing performed
   - Reference any related Jira tickets

### Deployment Process

Our CI/CD pipeline automatically handles deployments:

1. **PR Testing**: When you open a PR against `main`:
   - Unit tests run automatically
   - Integration tests deploy and validate model resources in the test environment

2. **Production Deployment**: For production releases:
   - Create a release branch: `git checkout -b release/v1.0.0 main`
   - Merging the release branch triggers automatic deployment to the production workspace

### After Your Pull Request is Merged

After your pull request is merged to `main`:

1. **Cleanup**: Delete your feature branch if desired:
   ```bash
   git branch -d feature/<your_feature_name>
   git push origin --delete feature/<your_feature_name>
   ```

### Production Releases

For production releases:

1. **Create Release Branch**:
   ```bash
   git checkout -b release/v1.0.0 main
   git push origin release/v1.0.0
   ```

2. **Automatic Production Deployment**: Pushing to a `release/*` branch triggers automatic deployment to production workspace

3. **Monitor Production**: Verify the deployment succeeded and app resources are functioning correctly

## ML App Configuration Changes

When making changes to ML model configurations:

1. **Bundle Validation**: Always validate bundle configurations locally
2. **Resource Testing**: Test resource changes in dev environment first
3. **Incremental Changes**: Make small, incremental changes for easier troubleshooting
4. **Documentation**: Update any relevant documentation for configuration changes



## Questions or Additional Help

If you need further assistance or have any questions, feel free to email the [MLOps Team](mailto:mlops-support@imail.org).

Thank you for contributing to our project!
