# check if the mongodb-test docker container is running and stop it
if [ "$(docker ps -q -f name=mongodb-test)" ]; then
    echo "Stopping the existing mongodb-test container"
    docker stop mongodb-test > /dev/null
fi

# check if the mongodb-test docker container exists and remove it
if [ "$(docker ps -aq -f name=mongodb-test)" ]; then
    echo "Removing the existing mongodb-test container"
    docker rm mongodb-test > /dev/null
fi

# create a new mongodb-test docker container
echo "Creating a new mongodb-test container"
docker run -d --name mongodb-test -p 27017:27017 -e MONGO_INITDB_DATABASE=sennet mongo:8 > /dev/null

# run the tests with the test configuration
echo "Running tests"
export SENOTYPE_CONFIG_FILE=$(realpath tests/config/app.test.cfg)
pytest -W ignore::DeprecationWarning

# stop and remove the mongodb-test container after tests are done
echo "Stopping and removing the mongodb-test container"
docker stop mongodb-test > /dev/null
docker rm --volumes mongodb-test > /dev/null
