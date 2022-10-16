# OpenGS / GS Online

A neat little tool to document your IT environment in a structured way and map your system to the *BSI Grundschutz* requirements.

As a result you can see which requirements you need to fullfill.

## How to run it

### Docker Compose

1) Build the app container with `docker build -t gsonline:dev .`

2) Create an `.env` file like so:
```
MYSQL_ROOT_PASSWORD=YourAppPassWordHere
MYSQL_USER=gsonline
MYSQL_PASSWORD=YourRootPassWordHere
MYSQL_DATABASE=opengs

DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/${MYSQL_DATABASE}
SECRET_KEY=SomeSecretKeyWhichIForgotWhatItIsGoodFor

MAIL_SERVER=localhost
MAIL_PORT=8025

ADMINS = ['your@email.here']
```

3) Execute `docker-compose up -d`

4) Access the app at <http://localhost:5000>. Register a user, login and go for it :)