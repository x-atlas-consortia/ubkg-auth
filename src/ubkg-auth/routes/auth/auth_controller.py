from flask import Blueprint, jsonify, current_app, make_response, request, Response
import requests
from app_utils.error import bad_request_error, unauthorized_error

auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.route('/umls-auth', methods=['POST', 'GET'])
def umls_auth():

    if request.method == 'POST':
        # Get the UMLS API key from the submitting form.
        umls_key = request.form['umls-key']
        if umls_key is None:
            bad_request_error("Must include parameter 'umls-key'")
    if request.method == 'GET':
        # Get the UMLS API key from the request argument.
        umls_key = request.args.get('umls-key')
        if umls_key is None:
            unauthorized_error("Must include parameter 'umls-key'")

    """
    Although the 'Validating UMLS Licensees for Third-Party Application Developers'
    page (https://documentation.uts.nlm.nih.gov/validating-licensees.html)
    indicates that two separate UMLS API keys are required for validation,
    the same API key can be used for both.
    """

    base_url = current_app.config['UMLS_VALIDATE_URL']
    url = base_url + '?validatorApiKey=' + umls_key + '&apiKey=' + umls_key

    # The UMLS API returns either "true" or "false".
    # Nginx auth_request ignores the response body.
    # We use body here only for direct visit to this endpoint.

    result = requests.get(url=url)

    if result.status_code != 200:
        # The UMLS API returns a 401 if the key is not valid.
        err_msg = "Invalid UMLS API key."
        return make_response(jsonify({"message": "UMLS-API: Not authorized"}), 401)
    if result.json():
        return make_response(jsonify({"message": "UMLS-API: Authorized"}), 200)
    else:
        return make_response(jsonify({"message": "UMLS-API: Not authorized"}), 401)

