from flask import Blueprint, jsonify, current_app, make_response  #, request
from ..common_neo4j_logic import (codes_code_id_codes_get_logic, codes_code_id_concepts_get_logic,
                                  codes_code_id_terms_get_logic)
from utils.http_error_string import get_404_error_string, validate_query_parameter_names, \
    validate_parameter_value_in_enum
from utils.http_parameter import parameter_as_list

codes_blueprint = Blueprint('codes', __name__, url_prefix='/codes')

# February 2025
# S3 redirect functions
from utils.s3_redirect import redirect_if_large

@codes_blueprint.route('/<code_id>/codes', methods=['GET'])
def codes_code_id_codes_get(code_id):
    """Returns a list of code_ids {Concept, Code, SAB} that code the same concept(s) as the code_id,
    optionally restricted to source (SAB)

    :param code_id: The code identifier
    :type code_id: str
    """
    # Validate sab parameter.
    err = validate_query_parameter_names(parameter_name_list=['sab'])
    if err != 'ok':
        return make_response(err, 400)

    # Obtain a list of sab parameter values.
    sab = parameter_as_list(param_name='sab')

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    result = codes_code_id_codes_get_logic(neo4j_instance, code_id, sab)
    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string='No Codes sharing the Concept linked to the Code specified',
                                   custom_request_path=f'CodeID = {code_id}',
                                   timeout = neo4j_instance.timeout)
        return make_response(err, 404)

    # February 2025
    return redirect_if_large(resp=result)


@codes_blueprint.route('/<code_id>/concepts', methods=['GET'])
def codes_code_id_concepts_get(code_id):
    """Returns a list of Concept objects {Concept, Prefterm} linked to the specified Code node.

    :param code_id: The code identifier
    :type code_id: str

    :rtype: Union[List[ConceptDetail], Tuple[List[ConceptDetail], int], Tuple[List[ConceptDetail], int, Dict[str, str]]
    """
    neo4j_instance = current_app.neo4jConnectionHelper.instance()
    result = codes_code_id_concepts_get_logic(neo4j_instance, code_id)

    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string='No Concepts linked to the Code specified',
                                   custom_request_path=f'CodeID = {code_id}',
                                   timeout = neo4j_instance.timeout)
        return make_response(err, 404)

    # February 2025
    return redirect_if_large(resp=result)

@codes_blueprint.route('/<code_id>/terms', methods=['GET'])
def codes_code_id_terms_get(code_id):
    """
    Returns an array of terms linked to the specified Code node.
    :param code_id: the code identifier
    """

    # Validate parameters.
    # Validate sab parameter.
    err = validate_query_parameter_names(parameter_name_list=['term_type'])
    if err != 'ok':
        return make_response(err, 400)

    # Obtain a list of sab parameter values.
    term_type = parameter_as_list(param_name='term_type')

    neo4j_instance = current_app.neo4jConnectionHelper.instance()
    result = codes_code_id_terms_get_logic(neo4j_instance, code_id=code_id,term_type=term_type)

    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string='No Terms linked to the Code specified',
                                   custom_request_path=f'CodeID = {code_id}',
                                   timeout = neo4j_instance.timeout)
        return make_response(err, 404)

    # February 2025
    return redirect_if_large(resp=result)