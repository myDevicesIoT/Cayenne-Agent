DEPLOY_DIR=Cayenne-Agent
mkdir $DEPLOY_DIR
cp -rf myDevices $DEPLOY_DIR
cp -rf scripts $DEPLOY_DIR
cp -rf setup.py $DEPLOY_DIR
BUILD_NAME="myDevices-test.tar.gz"
tar -czf $BUILD_NAME $DEPLOY_DIR
rm -rf $DEPLOY_DIR