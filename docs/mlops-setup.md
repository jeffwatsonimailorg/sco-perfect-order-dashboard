# MLOps Setup Guide
[(back to main README)](../README.md)

## Table of contents
* [Intro](#intro)
* [Create a hosted Git repo](#create-a-hosted-git-repo)
* [Configure CI/CD](#configure-cicd---github-actions)
* [Merge PR with initial ML code](#merge-a-pr-with-your-initial-ml-code)
* [Create release branch](#create-release-branch)

* [Deploy ML resources and enable production jobs](#deploy-ml-resources-and-enable-production-jobs)
* [Next steps](#next-steps)

## Intro
This page explains how to productionize the current project, setting up CI/CD and
ML resource deployment, and deploying ML training and inference jobs.

After following this guide, data scientists can follow the [ML Pull Request](ml-pull-request.md) guide to make changes to ML code or deployed jobs.

## Create a hosted Git repo
Create a hosted Git repo to store project code, if you haven't already done so. From within the project
directory, initialize Git and add your hosted Git repo as a remote:
```
git init --initial-branch=main
```

```
git remote add upstream <hosted-git-repo-url>
```

Commit the current `README.md` file and other docs to the `main` branch of the repo, to enable forking the repo:
```

git add README.md docs .gitignore PROJECT_NAME_CHANGE_ME/resources/README.md
git commit -m "Adding project README"

git push upstream main
```

### Set up authentication for CI/CD
#### Set up Azure Managed Identities

Add a managed identity for the new repo by submitting a PR to the appropriate Terraform EDP repos by adding your repo to these files:  
  - [test](https://bitbucket.org/intermountainhealthcare/tfp-ent-edp-tst/src/main/edp_core/managed_identities_mlops.tf)  
  - [prod](https://bitbucket.org/intermountainhealthcare/tfp-ent-edp-prd/src/main/edp_core/managed_identities_mlops.tf)



#### Configure Service Principal (SP) permissions 
If the created project uses **Unity Catalog**, we expect a catalog to exist with the name of the deployment target by default. 
For example, if the deployment target is dev, we expect a catalog named dev to exist in the workspace. 
If you want to use different catalog names, please update the target names declared in the[PROJECT_NAME_CHANGE_ME/databricks.yml](../PROJECT_NAME_CHANGE_ME/databricks.yml) file.
If changing the staging, prod, or test deployment targets, you'll also need to update the workflows located in the .github/workflows directory.

The SP must have proper permission in each respective environment and the catalog for the environments.

For the integration test and the ML training job, the SP must have permissions to read the input Delta table and create experiment and models. 
i.e. for each environment:
- USE_CATALOG
- USE_SCHEMA
- MODIFY
- CREATE_MODEL
- CREATE_TABLE

For the batch inference job, the SP must have permissions to read input Delta table and modify the output Delta table. 
i.e. for each environment
- USAGE permissions for the catalog and schema of the input and output table.
- SELECT permission for the input table.
- MODIFY permission for the output table if it pre-dates your job.


#### Set secrets for CI/CD

After creating the managed identities and adding them to the respective staging and prod workspace, add the following secrets to GitHub:
- `MI_TENANT_ID`
- `MI_CLIENT_ID`
- `MI_SUBSCRIPTION_ID`


## Merge a PR with your initial ML code
Create and push a PR branch adding the ML code to the repository.

```
git checkout -b add-ml-code
git add .
git commit -m "Add ML Code"
git push upstream add-ml-code
```

Open a PR from the newly pushed branch. CI will run to ensure that tests pass
on your initial ML code. Fix tests if needed, then get your PR reviewed and merged.
After the pull request merges, pull the changes back into your local `main`
branch:

```
git checkout main
git pull upstream main
```

## Create release branch
Create and push a release branch called `release/*` off of the `main` branch of the repository:
```
git checkout -b release/* main
git push upstream release/*
git checkout main
```

Your production jobs (model training, batch inference) will pull ML code against this branch, while your staging jobs will pull ML code against the `main` branch. Note that the `main` branch will be the source of truth for ML resource configs and CI/CD workflows.

For future ML code changes, iterate against the `main` branch and regularly deploy your ML code from staging to production by merging code changes from the `main` branch into the `release/*` branch.

## Deploy ML resources and enable production jobs
Follow the instructions in [PROJECT_NAME_CHANGE_ME/resources/README.md](../PROJECT_NAME_CHANGE_ME/resources/README.md) to deploy ML resources
and production jobs.

## Next steps
After you configure CI/CD and deploy training & inference pipelines, notify data scientists working
on the current project. They should now be able to follow the
[ML pull request guide](ml-pull-request.md) and 
[ML resource config guide](../PROJECT_NAME_CHANGE_ME/resources/README.md)  to propose, test, and deploy
ML code and pipeline changes to production.
