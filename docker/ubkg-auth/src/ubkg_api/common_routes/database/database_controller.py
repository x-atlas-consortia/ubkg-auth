from flask import Blueprint, jsonify, current_app, request, make_response
from ..common_neo4j_logic import database_info_server_get_logic
# S3 redirect functions
from utils.s3_redirect import redirect_if_large

database_blueprint = Blueprint('database', __name__, url_prefix='/database')


@database_blueprint.route('server', methods=['GET'])
def database_info_server_get():

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    # Obtain neo4j database name, server, edition
    result =  database_info_server_get_logic(neo4j_instance)
    # Mar 2025
    return redirect_if_large(resp=result)