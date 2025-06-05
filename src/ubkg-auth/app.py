import os
import sys
import logging
from pathlib import Path
from flask import Flask

from routes.auth.auth_controller import auth_blueprint

# Set up logging.
logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s', level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


class UbkgAuth:

    """
    Class for authenticating a consumer of UBKG resources against the UMLS API, using
    the UMLS API key associated with the user's UMLS UTS profile.
    """

    def __init__(self, config, package_base_dir):
        """
        If config is a string then it will be treated as a local file path from which to load a file, e.g.
        ubkg_app = UbkgAuth'./app.cfg', package_base_dir).app

        If config is a Flask.config then it will be used directly, e.g.
        config =  Flask(__name__,
                instance_path=path.join(path.abspath(path.dirname(__file__)), 'instance'),
                instance_relative_config=True)\
            .config.from_pyfile('app.cfg')

        The 'package_base_dir' is the base directory of the package (e.g., the directory in which
        the VERSION and BUILD files are located.
        """

        self.app = Flask(__name__,
                         instance_path=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance'),
                         instance_relative_config=True)

        self.app.package_base_dir = package_base_dir
        logger.info(f"package_base_dir: {package_base_dir}")

        # Load the app.cfg file.
        self.app.config.from_pyfile(config)

        self.app.register_blueprint(auth_blueprint)

        @self.app.route('/', methods=['GET'])
        def index():
            return "Hello! This is UBKG UMLS authenticaton service."


####################################################################################################
## For local development/testing
####################################################################################################

if __name__ == "__main__":
    try:
        ubkg_app = UbkgAuth('./ubkg-auth-app.cfg', Path(__file__).absolute().parent.parent.parent).app
        ubkg_app.run(host='0.0.0.0', port="5002")
    except Exception as e:
        print("Error during starting debug server.")
        print(str(e))
        logger.error(e, exc_info=True)
        print("Error during startup check the log file for further information")
