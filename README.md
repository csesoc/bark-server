# Bark Server

## Development

#### Dependencies
You will need

- OpenLDAP
- [pipenv](https://github.com/pypa/pipenv). Pipenv takes care of installing and managing Python dependencies.

#### Pre-Running
**Set Envvars**

You will need to set the environment vars for local development

```
cp .env.example.sh .env.sh
vim .env.sh

# Add envvars to the local environment
source .env.sh
```

**Initialize the DB**

The database for the website is stored in `data/bark.db`.

```bash
$ pipenv run python init_db.py
```

#### Running
```
pipenv run python bark_server
```

This will start a development server with automatic reloading on code changes

## Running the Docker Container

### Volumes:
 - `/app/data`: Data directory for the app. Contains sqlite db

### Ports:
The container exposes the server on port 8080.

### Environment:
You need to specify the environment vars outlined in `.env.example.sh`

```
# Run the container
docker run --rm -it --name bark-server -p 8080:8080 \
  -v $PWD/data:/app/data \
  -e SECRET_KEY="" \
  -e UDB_PASSWORD="" \
  csesoc/bark-server
```

## Building the Docker Container
```
# Build the container
docker build -t csesoc/bark-server

# Push the container
docker push csesoc/bark-server
```

## LDAP
To test Bark outside of UNSW's network, you'll need to make sure that `ldap_auth.py` connects to `localhost` (instead of `ad.unsw.edu.au`), and that you forward a connection to UNSW's LDAP server over SSH:

```
sudo ssh -N -L 389:ad.unsw.edu.au:389 <cse username>@login.cse.unsw.edu.au
```

(`sudo` is required since 389 is a privileged port... or you could always forward to a different port.)
