from flask import Blueprint, jsonify, current_app, make_response, request
import requests
from app_utils.error import bad_request_error

auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.route('/umls-auth', methods=['POST'])
def umls_auth():

    # Get the UMLS API key from the submitting form.
    umls_key = request.form['umls-key']
    if umls_key is None:
        bad_request_error("Must include parameter 'umls-key'")

    """
    Although the 'Validating UMLS Licensees for Third-Party Application Developers'
    page (https://documentation.uts.nlm.nih.gov/validating-licensees.html)
    indicates that two separate UMLS API keys are required for validation,
    the same API key can be used for both.
    """

    base_url = current_app.config['UMLS_VALIDATE_URL']
    url = base_url + '?validatorApiKey=' + umls_key + '&apiKey=' + umls_key

    # The UMLS API returns either "true" or "false".
    result = requests.get(url=url)
    if result.json():
        return jsonify(True), 200
    else:
        return jsonify(False), 403  # forbidden
