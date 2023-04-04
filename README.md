# Server Manager

A simple self-service for students and staff alike,
which aims to cover about 80% of the routine stuff.

There is currently no possibility to access the status/stats
through an api, which might come in handy in the future,
when we want a independent dashboard.

## Development

The development is all done **inside** docker containers.

This is to ensure deployment and development do not run apart too far.
It also makes some parts more self-describing,
like system dependencies.

### Prerequisites

You need docker with the compose plugin installed.

### Setup

1. Clone this repository
2. Copy .env-dist to .env and enter the required variables into the .env
3. build the images: docker compose build --pull
4. start the stack: docker compose up
5. create a superuser (in a new command window): `docker compose run --rm backend poetry run ./manage.py createsuperuser` (enter your new superuser)

Navigate to [https://localhost:8000/admin/](https://localhost:8000/admin/) (and accept the insecure certificate)
then login using the user you created above.

### Note

To facilitate development, it helps to be inside the container.
This can easily be achieved by starting a poetry shell:
`docker compose run --rm backend poetry shell`.

This even remembers the shell commands that have been run before, how nice is that
(it just creates a .bash_history file that happens to be included in the mounted directory
inside the container) ;-)

### Parts

* The frontend: [https://localhost:8000](https://localhost:8000)
* The admin interface: [https://localhost:8000/admin/](https://localhost:8000/admin/)

There are some development helpers:

* The flower (celery queue watcher): [https://localhost:8000/flower/](https://localhost:8000/flower/)
* Local Email: [https://localhost:8000/maildev/](https://localhost:8000/maildev/)
* Broker insight (RabbitMQ Console): [http://localhost:15672](https://localhost:15672) (Login with user:pass)

These helpers should not be deployed as is in production!

### Changing dependencies

To change/update dependencies, you should do it inside the docker container.

For example, to update the dependencies, you can run:

```bash
docker compose run --rm backend poetry update
```

### Setting up your IDE

If you are on Linux, you can use the .venv that is created
as a basis to point the IDE to the right environment.
This might work on MacOSX as well and has not been
confirmed to be working on windows.
