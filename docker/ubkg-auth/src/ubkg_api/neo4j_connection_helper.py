"""
Neo4jConnectionHelper class

This class works around Python limitations in passing data between processes to
set up a connection to a neo4j instance as a class property of a ubkg-api instance.

This addresses the use case in which the ubkg-api is imported as a library by a
child api. A single neo4j connection instance is kept active in the ubkg-api, so that
the child api does not need to manage the neo4 connection.

At least that's what I think all of this does.

Instead of accessing the class as a "normal" attribute of the ubkg-api, the
instance() and create() methods maintain a pointer to the single static property. A global
variable named "instance" is also involved.

"""

import logging
import neo4j

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

instance = None


class Neo4jConnectionHelper(object):
    @staticmethod
    def create(server, username, password, timeout, payloadlimit):
        if instance is not None:
            raise Exception(
                "An instance of Neo4jConnectionHelper exists already. "
                "Use the Neo4jConnectionHelper.instance() method to retrieve it.")

        return Neo4jConnectionHelper(server, username, password, timeout, payloadlimit)

    @staticmethod
    def instance():
        if instance is None:
            raise Exception(
                "An instance of Neo4jConnectionHelper does not yet exist. "
                "Use Neo4jConnectionHelper.create() to create a new instance")

        return instance

    @staticmethod
    def is_initialized():
        return instance is not None

    def _get_version(self) -> dict:
        # Obtains database version information.
        with self.driver.session() as session:
            query = 'CALL dbms.components() yield name, ' \
                    'versions, edition unwind versions ' \
                    'as version return {name:name, version:version, edition:edition} as info'
            result = session.run(query)

            for record in result:
                return record.get('info')

    def __init__(self, server, username, password, timeout, payloadlimit):

        global instance
        self.driver = neo4j.GraphDatabase.driver(server, auth=(username, password))
        if instance is None:
            instance = self
        # Mar 2025
        if timeout < 0:
            logger.info(f'The timeout in the app.cfg ({timeout}) is negative. Setting to 0.')
            timeout = 0
        self._timeout = timeout
        self._payloadlimit = payloadlimit
        info = self._get_version()
        # The default database name should always be neo4j. The SHOW databases command is administrative, and cannot
        # be called from the driver via apoc.cypher.run(). Hard code the value.
        self._database_name = 'neo4j'
        self._database_version = info.get('version')
        self._database_edition = info.get('edition')

        logger.info('Database information:')
        logger.info(f'-- name: {self._database_name}')
        logger.info(f'-- version: {self._database_version}')
        logger.info(f'-- edition: {self._database_edition}')

        logger.info('Constraints:')
        logger.info(f'-- timeout: {self._timeout} seconds')
        logger.info(f'-- payload limit (large response threshold): {self._payloadlimit} bytes')
        if self._payloadlimit == 0:
            logger.info('-- (Response size will not be checked.)')

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self):
        self.driver.close()

    def check_connection(self):
        record_field_name = 'result'
        query = f"RETURN 1 AS {record_field_name}"

        # Sessions will often be created and destroyed using a with block context
        with self.driver.session() as session:
            # Returned type is a Record object
            records = session.run(query)

            # When record[record_field_name] is not None (namely the cypher result is not null)
            # and the value equals 1
            for record in records:
                if record and record[record_field_name] and (record[record_field_name] == 1):
                    logger.info("Neo4j is connected :)")
                    return True

        logger.info("Neo4j is NOT connected :(")

        return False

    @property
    def timeout(self):
        """Gets the timeout of this Neo4jConnectionHelper

        :return: The timeout of this Neo4jConnectionHelper.
        :rtype: int
        """
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Sets the timeout of this Neo4jConnectionHelper.

        :param timeout: The timeout of this Neo4jConnectionHelper.
        :type timeout: int
        """

        self._timeout = timeout

    @property
    def payloadlimit(self):
        """Gets the payloadlimit of this Neo4jConnectionHelper

        :return: The payloadlimit of this Neo4jConnectionHelper.
        :rtype: int
        """
        return self._payloadlimit

    @payloadlimit.setter
    def payloadlimit(self, payloadlimit):
        """Sets the payloadlimit of this Neo4jConnectionHelper.

        :param payloadlimit: The payloadlimit of this Neo4jConnectionHelper.
        :type payloadlimit: int
        """

        self._payloadlimit = payloadlimit

    @property
    def database_name(self):
        """Gets the database_name of this Neo4jConnectionHelper

        :return: The database_name of this Neo4jConnectionHelper.
        :rtype: str
        """
        return self._database_name

    @database_name.setter
    def database_name(self, database_name):
        """Sets the database_name of this Neo4jConnectionHelper.

        :param database_name: The database_name of this Neo4jConnectionHelper.
        :type database_name: str
        """

        self._database_name = database_name

    @property
    def database_version(self):
        """Gets the database_version of this Neo4jConnectionHelper

        :return: The database_version of this Neo4jConnectionHelper.
        :rtype: str
        """
        return self._database_version

    @database_version.setter
    def database_version(self, database_version):
        """Sets the database_version of this Neo4jConnectionHelper.

        :param database_version: The database_version of this Neo4jConnectionHelper.
        :type database_version: str
        """
        self._database_version = database_version

    @property
    def database_edition(self):
        """Gets the database_edition of this Neo4jConnectionHelper

        :return: The database_edition of this Neo4jConnectionHelper.
        :rtype: str
        """
        return self._database_edition

    @database_edition.setter
    def database_edition(self, database_edition):
        """Sets the database_edition of this Neo4jConnectionHelper.

        :param database_edition: The database_edition of this Neo4jConnectionHelper.
        :type database_edition: str
        """
        self._database_edition = database_edition
