from flask import Blueprint, jsonify, current_app, request, make_response

# Cypher query functions
from ..common_neo4j_logic import concepts_concept_id_codes_get_logic, concepts_concept_id_concepts_get_logic,\
    concepts_concept_id_definitions_get_logic, concepts_expand_get_logic,\
    concepts_shortestpath_get_logic, concepts_trees_get_logic, concepts_subgraph_get_logic, \
    concepts_identfier_node_get_logic, concepts_subgraph_sequential_get_logic
# Functions to validate query parameters
from utils.http_error_string import get_404_error_string, validate_query_parameter_names, \
    validate_parameter_value_in_enum, validate_required_parameters, validate_parameter_is_numeric, \
    validate_parameter_is_nonnegative, validate_parameter_range_order, check_payload_size, \
    check_neo4j_version_compatibility,check_max_mindepth,wrap_message
# Functions to format query parameters for use in Cypher queries
from utils.http_parameter import parameter_as_list, set_default_minimum, set_default_maximum

# S3 redirect functions
from utils.s3_redirect import redirect_if_large

concepts_blueprint = Blueprint('concepts', __name__, url_prefix='/concepts')


@concepts_blueprint.route('<concept_id>/codes', methods=['GET'])
def concepts_concept_id_codes_get(concept_id):
    """Returns a distinct list of code_id(s) that code the concept

    :param concept_id: The concept identifier
    :type concept_id: str

    :rtype: Union[List[str], Tuple[List[str], int], Tuple[List[str], int, Dict[str, str]]
    """

    # Validate sab parameter.
    err = validate_query_parameter_names(parameter_name_list=['sab'])
    if err != 'ok':
        return make_response(err, 400)

    # Obtain a list of sab parameter values.
    sab = parameter_as_list(param_name='sab')

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    result = concepts_concept_id_codes_get_logic(neo4j_instance, concept_id, sab)
    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string='No Codes with link to the specified Concept',
                                   custom_request_path=f'concept_id = {concept_id}',
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # February 2025
    return redirect_if_large(resp=result)


@concepts_blueprint.route('<concept_id>/concepts', methods=['GET'])
def concepts_concept_id_concepts_get(concept_id):
    """Returns a list of concepts {Sab, Relationship, Concept, Prefterm} related to the concept

    :param concept_id: The concept identifier
    :type concept_id: str

    :rtype: Union[List[SabRelationshipConceptTerm], Tuple[List[SabRelationshipConceptTerm], int],
     Tuple[List[SabRelationshipConceptTerm], int, Dict[str, str]]
    """
    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    result = concepts_concept_id_concepts_get_logic(neo4j_instance, concept_id)
    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string='No Concepts with relationships to the specified Concept',
                                   custom_request_path=f'concept_id = {concept_id}',
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

@concepts_blueprint.route('<concept_id>/definitions', methods=['GET'])
def concepts_concept_id_definitions_get(concept_id):
    """Returns a list of definitions {Sab, Definition} of the concept

    :param concept_id: The concept identifier
    :type concept_id: str
    """
    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    result = concepts_concept_id_definitions_get_logic(neo4j_instance, concept_id)
    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string='No Definitions for specified Concept',
                                   custom_request_path=f"concept_id='{concept_id}'",
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

# JAS January 2024 Converted from POST to GET.
@concepts_blueprint.route('<concept_id>/paths/expand', methods=['GET'])
def concepts_paths_expand_get(concept_id):

    """
    Returns the set of paths that begins with the concept <concept_id>, in neo4j graph format ({nodes, paths, edges}).

    """

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    # Validate parameters.
    # Check for invalid parameter names.
    err = validate_query_parameter_names(parameter_name_list=['sab', 'rel', 'mindepth', 'maxdepth', 'skip', 'limit'])
    if err != 'ok':
        return make_response(err, 400)

    # Check for required parameters.
    err = validate_required_parameters(required_parameter_list=['sab', 'rel', 'maxdepth'])
    if err != 'ok':
        return make_response(err, 400)

    # Check that the maximum path depth is non-negative.
    maxdepth = request.args.get('maxdepth')
    err = validate_parameter_is_nonnegative(param_name='maxdepth', param_value=maxdepth)
    if err != 'ok':
        return make_response(err, 400)

    # Check that the minimum path depth is non-negative.
    mindepth = request.args.get('mindepth')
    err = validate_parameter_is_nonnegative(param_name='mindepth', param_value=mindepth)
    if err != 'ok':
        return make_response(err, 400)

    # APR 2024 - Check range after setting defaults.
    # Set default mininum.
    mindepth = set_default_minimum(param_value=mindepth, default=1)

    # MAY 2024 - moved mindepth !> maxdepth check up.
    # Validate that mindepth is not greater than maxdepth.
    err = validate_parameter_range_order(min_name='mindepth', min_value=mindepth, max_name='maxdepth',
                                         max_value=maxdepth)
    # Set default maximum.
    maxdepth = str(int(mindepth) + 2)

    if err != 'ok':
        return make_response(err, 400)

    # Check that the non-default skip is non-negative.
    skip = request.args.get('skip')
    err = validate_parameter_is_nonnegative(param_name='skip', param_value=skip)
    if err != 'ok':
        return make_response(err, 400)

    # Set default mininum.
    skip = set_default_minimum(param_value=skip, default=0)

    # Check that non-default limit is non-negative.
    limit = request.args.get('limit')
    err = validate_parameter_is_nonnegative(param_name='limit', param_value=limit)
    if err != 'ok':
        return make_response(err, 400)
    # Set default row limit.
    limit = set_default_maximum(param_value=limit, default=1000)

    # Get remaining parameter values from the path or query string.
    query_concept_id = concept_id
    sab = parameter_as_list(param_name='sab')
    rel = parameter_as_list(param_name='rel')

    result = concepts_expand_get_logic(neo4j_instance, query_concept_id=query_concept_id, sab=sab, rel=rel,
                                       mindepth=mindepth, maxdepth=maxdepth, skip=skip, limit=limit)

    iserr = result is None or result == {}

    if iserr:
        err = get_404_error_string(prompt_string=f"No expanded paths found for specified parameters",
                                   custom_request_path=f"query_concept_id='{query_concept_id}'",
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

# JAS February 2024 Replaced POST with GET
@concepts_blueprint.route('<origin_concept_id>/paths/shortestpath/<terminus_concept_id>', methods=['GET'])
def concepts_shortestpath_get(origin_concept_id, terminus_concept_id):

    """
    Returns the shortest path between a pair of concepts. View the docstring for the concepts_expand_get for an example
    of a return.

    origin_concept_id: origin of the shortest path
    terminus_concept_id: terminus of the shortest path

    """
    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    # Validate parameters.
    # Check for invalid parameter names.
    err = validate_query_parameter_names(parameter_name_list=['sab', 'rel'])
    if err != 'ok':
        return make_response(err, 400)

    # Check for required parameters.
    err = validate_required_parameters(required_parameter_list=['sab', 'rel'])
    if err != 'ok':
        return make_response(err, 400)

    # Get remaining parameter values from the path or query string.
    origin_concept_id = origin_concept_id
    terminus_concept_id = terminus_concept_id
    sab = parameter_as_list(param_name='sab')
    rel = parameter_as_list(param_name='rel')

    result = concepts_shortestpath_get_logic(neo4j_instance, origin_concept_id=origin_concept_id,
                                             terminus_concept_id=terminus_concept_id, sab=sab, rel=rel)
    if result is None or result == {}:
        # Empty result
        err = get_404_error_string(prompt_string=f"No paths found between Concepts",
                                   custom_request_path=f"origin_concept_id='{origin_concept_id}' and "
                                                       f"terminus_concept_id='{terminus_concept_id}'",
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

@concepts_blueprint.route('<concept_id>/paths/trees', methods=['GET'])
def concepts_trees_get(concept_id):
    """Return nodes in a spanning tree from a specified concept, based on
    the relationship pattern specified within the selected sources, to a specified path depth.

    Refer to the docstring for the concept_expand_get function for details on the return.
    """

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    # Validate parameters.
    # Check for invalid parameter names.
    err = validate_query_parameter_names(parameter_name_list=['sab', 'rel', 'mindepth', 'maxdepth', 'skip', 'limit'])
    if err != 'ok':
        return make_response(err, 400)

    # Check for required parameters.
    err = validate_required_parameters(required_parameter_list=['sab', 'rel', 'maxdepth'])
    if err != 'ok':
        return make_response(err, 400)

    # Check that the maximum path depth is non-negative.
    maxdepth = request.args.get('maxdepth')
    err = validate_parameter_is_nonnegative(param_name='maxdepth', param_value=maxdepth)
    if err != 'ok':
        return make_response(err, 400)

    # Check that the minimum path depth is non-negative.
    mindepth = request.args.get('mindepth')
    err = validate_parameter_is_nonnegative(param_name='mindepth', param_value=mindepth)
    if err != 'ok':
        return make_response(err, 400)

    mindepth = set_default_minimum(param_value=mindepth, default=0)

    # Limit the minimum to 0 or 1.
    if int(mindepth) > 1:
        err = f"Invalid value for 'mindepth' {mindepth}. The 'mindepth' parameter value for a spanning tree " \
              f"can be either 0 or 1."
        return make_response(err, 400)

    # MAY 2024 - moved the mindepth !> maxdepth check before setting the default maxdepth.
    # Validate that mindepth is not greater than maxdepth.
    err = validate_parameter_range_order(min_name='mindepth', min_value=mindepth, max_name='maxdepth',
                                             max_value=maxdepth)
    if err != 'ok':
        return make_response(err, 400)

    # Set default maximum.
    maxdepth = str(int(mindepth) + 2)

    # Check that the non-default skip is non-negative.
    skip = request.args.get('skip')
    err = validate_parameter_is_nonnegative(param_name='skip', param_value=skip)
    if err != 'ok':
        return make_response(err, 400)

    # Set default mininum for the skip.
    skip = set_default_minimum(param_value=skip, default=0)

    # Check that non-default limit is non-negative.
    limit = request.args.get('limit')
    err = validate_parameter_is_nonnegative(param_name='limit', param_value=limit)
    if err != 'ok':
        return make_response(err, 400)
    # Set default row limit.
    limit = set_default_maximum(param_value=limit, default=1000)

    # Get remaining parameter values from the path or query string.
    query_concept_id = concept_id
    sab = parameter_as_list(param_name='sab')
    rel = parameter_as_list(param_name='rel')

    result = concepts_trees_get_logic(neo4j_instance, query_concept_id=query_concept_id, sab=sab, rel=rel,
                                      mindepth=mindepth, maxdepth=maxdepth, skip=skip, limit=limit)
    if result is None or result == {}:
        # Empty result
        err = get_404_error_string(prompt_string=f"No spanning tree found for specified parameters",
                                   custom_request_path=f"query_concept_id='{query_concept_id}'",
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

@concepts_blueprint.route('paths/subgraph', methods=['GET'])
def concepts_subgraph_get():
    """
    Returns the paths in the subgraph specified by relationship types and SABs, constrained by
    depth parameters.

    Refer to the docstring for the concept_expand_get function for details on the return.
    """

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    # The query for this endpoint relies on db.index.fulltext.queryRelationships, which was introduced in version 5 of
    # neo4j.
    err = check_neo4j_version_compatibility(query_version='5.11.0', instance_version=neo4j_instance.database_version)
    if err != 'ok':
        return make_response(err, 400)

    # Validate parameters.
    # Check for invalid parameter names.
    err = validate_query_parameter_names(parameter_name_list=['sab', 'rel', 'skip', 'limit'])
    if err != 'ok':
        return make_response(err, 400)

    # Check for required parameters.
    err = validate_required_parameters(required_parameter_list=['sab', 'rel'])
    if err != 'ok':
        return make_response(err, 400)

    # Check that the non-default skip is non-negative.
    skip = request.args.get('skip')
    err = validate_parameter_is_nonnegative(param_name='skip', param_value=skip)
    if err != 'ok':
        return make_response(err, 400)

    # Set default mininum for the skip.
    skip = set_default_minimum(param_value=skip, default=0)

    # Check that non-default limit is non-negative.
    limit = request.args.get('limit')
    err = validate_parameter_is_nonnegative(param_name='limit', param_value=limit)
    if err != 'ok':
        return make_response(err, 400)
    # Set default row limit.
    limit = set_default_maximum(param_value=limit, default=1000)

    # Get remaining parameter values from the path or query string.
    sab = parameter_as_list(param_name='sab')
    rel = parameter_as_list(param_name='rel')

    result = concepts_subgraph_get_logic(neo4j_instance, sab=sab, rel=rel,
                                         skip=skip, limit=limit)
    if result is None or result == {}:
        # Empty result
        err = get_404_error_string(prompt_string=f"No subgraphs (pairs of Concepts linked by relationships) found for "
                                                 f"specified relationship types",
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

@concepts_blueprint.route('<search>/nodeobjects', methods=['GET'])
def concepts_concept_identifier_nodes_get(search):
    """
    Returns a "nodes" object representing a set of "Concept node" object.
    Each Concept node object translates and consolidates information about a Concept node in the UBKG.
    (Each Concept node is the origin of a subgraph that includes Code, Term, Definition, and Semantic Type nodes.)

    :param search: A string that can correspond to one or more of the following:
    1. The preferred term for a Concept.
    2. A term linked to a Code that is linked to a Concept.
    3. The CodeId of a Code that is linked to a Concept.
    4. The CUI of a Concept.
    """

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    result = concepts_identfier_node_get_logic(neo4j_instance, search=search)
    if result is None or result == []:
        # Empty result
        err = get_404_error_string(prompt_string=f"No nodeobjects for concepts with identifier",
                                   custom_request_path=f"identifier='{search}'",
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)

@concepts_blueprint.route('/paths/subgraph/sequential', methods=['GET'])
def concepts_paths_subgraphs_sequential_get_endpoint():
    return concepts_paths_subraphs_sequential_get(concept_id=None)

@concepts_blueprint.route('<concept_id>/paths/subgraph/sequential', methods=['GET'])
def concepts_paths_subgraphs_name_sequential_get_endpoint(concept_id):
    return concepts_paths_subraphs_sequential_get(concept_id=concept_id)

def concepts_paths_subraphs_sequential_get(concept_id=None):

    """
    Returns the set of paths that begins with the concept <concept_id> and has relationships in a specified
    sequence.

    If no concept_id is specified, then return all paths that begin with the first specified relationship.

    Response is in neo4j graph format ({nodes, paths, edges}).

    The relsequence request parameter is an ordered list that specifies a sequence of relationships in a path.
    The format of each element in relsequence is <SAB>:<relationship type>.
    For example, ['UBERON:isa','PATO:has_part'] specifies the set of paths that start from the concept with CUI
    <concept_id> with relationships that match the pattern

    (concept_id: Concept)-[r1:isa]-(c1:Concept)-[r2:has_part]->(c2:Concept)

    in which r1.SAB = 'UBERON' and r2.SAB = 'PATO'

    """

    neo4j_instance = current_app.neo4jConnectionHelper.instance()

    # Validate parameters.
    # Check for invalid parameter names.
    err = validate_query_parameter_names(parameter_name_list=['relsequence', 'skip', 'limit'])
    if err != 'ok':
        return make_response(err, 400)

    # Check for required parameters.
    err = validate_required_parameters(required_parameter_list=['relsequence'])
    if err != 'ok':
        return make_response(err, 400)

    # Check that the non-default skip is non-negative.
    skip = request.args.get('skip')
    err = validate_parameter_is_nonnegative(param_name='skip', param_value=skip)
    if err != 'ok':
        return make_response(err, 400)

    # Set default mininum.
    skip = set_default_minimum(param_value=skip, default=0)

    # Check that non-default limit is non-negative.
    limit = request.args.get('limit')
    err = validate_parameter_is_nonnegative(param_name='limit', param_value=limit)
    if err != 'ok':
        return make_response(err, 400)
    # Set default row limit, based on the app configuration.
    limit = set_default_maximum(param_value=limit, default=1000)

    # Get remaining parameter values from the path or query string.
    relsequence = parameter_as_list(param_name='relsequence')
    reltypes = []
    relsabs = []
    for rs in relsequence:
        if not ':' in rs:
            err = f'Invalid parameter value for \'relsequence\': {rs}. Format relationships as <SAB>:<relationship_type>'
            return make_response(wrap_message(key="message", msg=err), 400)

        relsabs.append(rs.split(':')[0].upper())
        reltypes.append(rs.split(':')[1])


    result = concepts_subgraph_sequential_get_logic(neo4j_instance, startCUI=concept_id, reltypes=reltypes, relsabs=relsabs,
                                       skip=skip, limit=limit)

    iserr = result is None or result == {}

    if concept_id == None:
        custom_request_path = f'any concept'
    else:
        custom_request_path = f"concept with identifier '{concept_id}'"
    custom_request_path = custom_request_path + f" with sequential relationships '{relsequence}'"

    if iserr:
        err = get_404_error_string(prompt_string=f"No sequential paths found starting",
                                   custom_request_path=custom_request_path,
                                   timeout=neo4j_instance.timeout)
        return make_response(err, 404)

    # Feb 2025
    return redirect_if_large(resp=result)