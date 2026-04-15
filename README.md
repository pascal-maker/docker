# Docker demos

## Networking demo

```yaml
services:
    my-storage-api:
        build:
            context: api
        image: ghcr.io/nathansegers/backend-demo-volume_api 
        ports: 
            - 8888:80
        volumes:
            - ./data:/mnt/data/storage
    client:
        hostname: client
        build:
            context: client
        image: ghcr.io/nathansegers/backend-demo-volume_client
        ports: 
            - 8001:80 
```

1. Start the services, and build if necessary.
2. Change the image names if you want to push it to any repository later on.

- Go to the client and use the "/images" endpoint.
- Fill in a path you want to try
  - localhost:80
  - localhost:8888
  - api:80
  - api:8888
  - my-storage-api:80
  - my-storage-api:8888

- Change the ports and try again
- Remove the ports and try again
- Add a hostname and try again
- Change the service name and keep the hostname
- Remove the hostname

## Volumes demo

- Remove the volumes section of the API
- Demonstrate by stopping the API with **docker compose down**
- Add a named volume to the services
- Find out where the files are now

## Exec demo for debugging

- Change `command: tail -f /dev/null`
- Exec using commands

## Docker init

- `docker init` creates 4 useful files that you can use in your project for a very basic and quick to use Docker setup.
- Use it when you already have your code written, and your project setup, so you can leverage the detection of your software.

## Docker watch

- `docker watch` makes it easier for you to develop your application and use auto-reloading and auto-rebuilding tools included in Docker Compose.
Use this when you want to automatically rebuild your application into a new Docker image as soon as your requirements or your config files are changed and your app needs to be restarted and rebuilt.
Docker watch can also detect file changes to sync and restart your container if needed. These are not copied into the build of your app.

## .dockerignore demo

- Go to `dockerignore_demo/` and run `docker compose up --build`.
- Compare the output of `without-ignore` and `with-ignore`.
- `with-ignore` excludes `secret.env` and `tmp/` from the image build context.

## depends_on + healthcheck demo

- Go to `depends_on_health_demo/` and run `docker compose up --build`.
- Open `http://localhost:8090` for an always-on UI that polls API health and shows an orange dot while the API warms up.
- The same status UI also reads container state for `api` and `delayed-ui` via a Docker socket-backed internal API.
- Open `http://localhost:8091` for a frontend that starts only after API health is `healthy` using `depends_on` with `condition: service_healthy`.
