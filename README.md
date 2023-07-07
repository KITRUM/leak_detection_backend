# About

This documents includes the information about setting up and adjusting the leak detection backend project locally.

⚠️ Before you do this it is highly recommended go to the Github Wiki page and read about the project.
There you'll find the Git flow, database strcture, glossary and a lot more information that is updating with higher frequency that the `README.md` file 😄

<br>

# 🔨 Setup the project locally

> 💡 It includes 2 possible guides: for setting up it with docker 🐳 or without it.

## 🚧 Mandatory steps

Clone the project from GitHub
```bash
git clone git@github.com:KitRUM/leak_detection_backend.git
```

<br>

## ✖️ 🐳 Without docker

### 🔧 Setup the environment

For running the application locally without a tool like Docker you would need to install all dependencies by yourself.
First of all you have to install Python3.11 and SQLite3 on your machine since they are main infrastructure components.
More information about the installation process you can find _[HERE](https://github.com/KitRUM/leak_detection_backend/wiki/The-project-is-powered-by)_

Then you have to install Python dependencies that are used for running the application. For doing this we recommend using `pipenv` as a tool for managing your virtual environment and project dependencies (_but if you prefer using conda for example feel free to do this_).

```bash
# install the pipenv tool
pip install pipenv

# activate the virtual environment
pipenv shell

# install dependencies from the Pipfile.lock file
pipenv sync --dev
```

### 🗃️ Setup the database

For working with database the alembic too is used. To initiate a new database, run:

```bash
alembic upgrade head
```

**More alembic commands**

Generate a new migration file based on SQLAlchemy models
```bash
alembic revision --autogenerate -m "MESSAGE"
```

Upgrade database according to the last version of migrations
```bash
alembic upgrade head
```

Downgrade to the specific migration version
```bash
alembic downgrade 0e43c346b90d
```

*P.S. This hash is taken from the generated file in the migrations folder*

> ⚠️ Do not forget that alembic saves the migration version into the database. Then, when you do crusial database updates you might need to remove the revision ID from the database.</i>

```bash
sqlite3 leak_detection.sqlite3
> delete from alembic_version;
```



### 🏃‍♂️ Run the application

For running the application locally you can use Uvicorn Python ASGI server. More information _[HERE](https://github.com/KitRUM/leak_detection_backend/wiki/The-project-is-powered-by)_

```bash
uvicorn src.main:app --reload
```

The reload parameter will reload the Uvicorn server on any change in the project root

<br>

## 🐳 Using Docker

Since developers may use different operating system the Docker system is used in order to resolve the issue: "not working on my computer".
If more specifically, the Docker compose is used for better experience.

### 🛠️ Setting up the project
For setting up the project you just need to complete only a few steps:

* Install Docker [[_download page_](https://docs.docker.com/get-docker/)]
* Run Docker containers using docker-compose:

### 🏃‍♂️ Running docker containers

> ⚠️ This command should be ran in the project root folder (_leak_detection_backend/_)

```bash
docker-compose up -d
```

The `-d` means `--detach` that allows you to run the container in a background

**More Docker commands:**

```
# Shut down docker containers
docker-compose down

# Show logs
docker-compose logs

# Show logs in a real time
docker-compose logs -f
```

<br>


## 🔧 Configure the project

The project could be configurable by using the environment variables.

For better development experience - the pydantic Config feature is used (*described in the config.py file*). It means that you can configure any variable that is encapsulated in the `src/config.py:setting` object by setting the environment variable in the session where you run the application.

Read more about [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/)

The example:
```
# on Unix
export DATABASE__NAME=leak_detection.sqlite3

# on Windows
$env:DATABASE__NAME = "leak_detection.sqlite3";
```

#### Using `.env` file

Or as a preffered alternative you may use the `.env` that is automatically complete the stuff above for you if you use `pipenv` tool.

It means you jsut need to complete next steps:
```bash
# create the .env file base on the .env.default file
cp .env.default .env

# activate the virtual environment & export all environment variables automatically ༼ つ ◕_◕ ༽つ━☆ﾟ.*･｡ﾟ
pipenv shell
```


<br>


## 🤔 Summary

* So now, the project is ready to be used as a backend API.
Just use your favorite Http requests client (_such as Postman or Advanced Rest Client_) for making queries.

* The `http://localhost:8000/docs` is available in your browser for reaching the API documentation (_Swagger_)

* `leak_detection_backend/http/` folder contains http requests examples


<br>

# 🏗️ Project layout

We were inspired by Eric Evans's layered architecture and DDD when we were creating the project structure.

For more details read about [DDD](https://en.wikipedia.org/wiki/Domain-driven_design)

```bash
└─ leak_detection_backend       # Project root
    ├─ .gitignore               # Exclude files and directories that match patterns in it before Git will index the root
    ├─ .env.default             # Contains default project configurations
    ├─ .pyproject.toml          # Development dependencies configuration file
    ├─ Pipfile                  # The Pipenv configuration file for managing dependencies
    ├─ Pipfile.lock             # Managed by the Pipenv automatically
    ├─ alembic.ini              # The alembic (migration tool) configuration file
    ├─ Makefile                 # Contains Bash scripts for comfortable work from the terminal
    ├─ logs                     # Local folder that aggregates all application logs
    ├─ seed                     # Contains seed files that are mandatory for running the application
    ├─ http                     # Contains Api endpoints requests examples
    ├─ mock                     # The mock data for running the application in `Debug` mode
    └─ src                      # The sources root
        ├─ presentation         # Includes controllers that represent each application entrypoint
            ├─ platforms        # Platforms API endpoints
            └─ templates        # Templates API endpoints
        ├─ application          # Operation layer outlines the business features on the highest level
            ├─ tsd              # Time series data global feature package
            ├─ database         # Includes database operations on the high level such as transaction, ...
            └─ data_lake        # Includes the producer/consumer implementation for this project
        ├─ domain               # Includes sub-domains that include entities, values-objects, aggregates and services
            ├─ tsd              # Time series data sub-domain
                ├─ repository   # Repository pattern implementation
                ├─ constants    # Specific time series data constants
                ├─ services     # Includes specific platofms services
                └─ models       # Includes all kind of entities, contracts, values-objects, etc
            └─ platforms        # Platforms sub-domain
        ├─ infrastructure       # Contains services, factories and components that are needed by domain and presentation layers
            ├─ application      # Application components (framework factories, shared entities(aggregates, values objects))
            ├─ errors           # Application errors
            ├─ models           # Shared models
            ├─ constants        # Shared constants
            └─ database         # Database components (migrations, session factories, etc...)
                └─ migrations   # Managed by the migration tool automatically
        ├─ static               # Static files for the frontend layer: CSS, JS, Images
        └─ templates            # Includes Jinja2 templates for the Server-side rendering
```

