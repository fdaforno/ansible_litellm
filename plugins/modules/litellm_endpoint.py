#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Federico Daforno
# MIT License

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: litellm_endpoint

short_description: Manages endpoints in LiteLLM

version_added: "1.0.0"

description:
    - This module allows you to create, modify, and delete endpoints in LiteLLM
    - Endpoints are API base URLs that can be associated with models

options:
    api_url:
        description:
            - URL of the LiteLLM instance
        required: true
        type: str
    api_key:
        description:
            - Master API key for authentication with LiteLLM
        required: true
        type: str
    endpoint_name:
        description:
            - Name/identifier of the endpoint
        required: true
        type: str
    api_base:
        description:
            - Base URL of the endpoint
        required: false
        type: str
    provider:
        description:
            - Provider type (e.g., openai, azure, anthropic)
        required: false
        type: str
    api_key:
        description:
            - API key for this endpoint (optional, can use environment variables)
        required: false
        type: str
    api_version:
        description:
            - API version for the endpoint
        required: false
        type: str
    metadata:
        description:
            - Additional metadata for the endpoint
        required: false
        type: dict
        default: {}
    state:
        description:
            - Desired state of the endpoint
        required: false
        type: str
        choices: ['present', 'absent']
        default: present
    validate_certs:
        description:
            - Verify SSL certificates
        required: false
        type: bool
        default: true

author:
    - Federico Daforno

requirements:
    - python >= 3.8
    - requests
'''

EXAMPLES = r'''
# Add a new endpoint
- name: Add OpenAI endpoint
  fdaforno.ansible_collection_litellm.litellm_endpoint:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    endpoint_name: "openai-prod"
    api_base: "https://api.openai.com/v1"
    provider: "openai"
    api_key: "{{ openai_api_key }}"
    metadata:
      environment: "production"
      region: "us-east-1"
    state: present

# Add Azure OpenAI endpoint
- name: Add Azure endpoint
  fdaforno.ansible_collection_litellm.litellm_endpoint:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    endpoint_name: "azure-eastus"
    api_base: "{{ azure_api_base }}"
    provider: "azure"
    api_key: "{{ azure_api_key }}"
    api_version: "2023-12-01"
    metadata:
      environment: "production"
      region: "eastus"
    state: present

# Remove an endpoint
- name: Remove endpoint
  fdaforno.ansible_collection_litellm.litellm_endpoint:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    endpoint_name: "old-endpoint"
    state: absent
'''

RETURN = r'''
endpoint:
    description: Information about the created/modified endpoint
    type: dict
    returned: when state is present
    sample:
        endpoint_name: "openai-prod"
        api_base: "https://api.openai.com/v1"
        provider: "openai"
        metadata:
            environment: "production"
changed:
    description: Indicates if changes were made
    type: bool
    returned: always
message:
    description: Descriptive message of the operation
    type: str
    returned: always
'''

import json
import traceback

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    REQUESTS_IMPORT_ERROR = traceback.format_exc()

from ansible.module_utils.basic import AnsibleModule, missing_required_lib


class LiteLLMEndpointManager:
    def __init__(self, module):
        self.module = module
        self.api_url = module.params['api_url'].rstrip('/')
        self.api_key = module.params['api_key']
        self.validate_certs = module.params['validate_certs']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method, endpoint, data=None):
        """Effettua una richiesta HTTP all'API LiteLLM"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, verify=self.validate_certs)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, verify=self.validate_certs)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, verify=self.validate_certs)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, verify=self.validate_certs)
            else:
                self.module.fail_json(msg=f"Metodo HTTP non supportato: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            self.module.fail_json(msg=f"Errore nella richiesta HTTP: {str(e)}")

    def get_endpoints(self):
        """Recupera le informazioni di tutti gli endpoint (modelli con api_base)"""
        response = self._make_request('GET', '/model/info')
        
        if response.status_code == 200:
            data = response.json()
            endpoints = []
            if 'data' in data:
                for model in data['data']:
                    if 'litellm_params' in model and 'api_base' in model['litellm_params']:
                        # Consideriamo questo come un endpoint
                        endpoint_info = {
                            'endpoint_name': model.get('model_name', 'unknown'),
                            'api_base': model['litellm_params']['api_base'],
                            'provider': self._extract_provider(model['litellm_params']),
                            'metadata': model.get('model_info', {})
                        }
                        endpoints.append(endpoint_info)
            return {'endpoints': endpoints}
        else:
            self.module.fail_json(msg=f"Errore nel recupero degli endpoint: {response.status_code} - {response.text}")

    def get_endpoint(self, endpoint_name):
        """Recupera le informazioni di un endpoint specifico"""
        endpoints = self.get_endpoints()
        for endpoint in endpoints.get('endpoints', []):
            if endpoint.get('endpoint_name') == endpoint_name:
                return endpoint
        return None

    def _extract_provider(self, litellm_params):
        """Estrae il provider dai parametri litellm"""
        model = litellm_params.get('model', '')
        if '/' in model:
            return model.split('/')[0]
        return 'unknown'

    def create_endpoint(self, endpoint_name, api_base, provider, api_key, api_version, metadata):
        """Crea un nuovo endpoint come modello LiteLLM"""
        # Creiamo un modello che rappresenta l'endpoint
        litellm_params = {
            'model': f"{provider}/endpoint-{endpoint_name}",
            'api_base': api_base
        }
        
        if api_key:
            litellm_params['api_key'] = api_key
        if api_version:
            litellm_params['api_version'] = api_version
        
        model_info = metadata or {}
        model_info['endpoint_type'] = 'managed_endpoint'
        
        data = {
            'model_name': endpoint_name,
            'litellm_params': litellm_params,
            'model_info': model_info
        }
        
        response = self._make_request('POST', '/model/new', data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nella creazione dell'endpoint: {response.status_code} - {response.text}")

    def delete_endpoint(self, endpoint_name):
        """Elimina un endpoint (nota: richiede rimozione manuale dal config)"""
        self.module.fail_json(msg="Eliminazione endpoint non supportata direttamente dall'API. Rimuovi l'endpoint dal file di configurazione config.yaml")


def main():
    module_args = dict(
        api_url=dict(type='str', required=True),
        api_key=dict(type='str', required=True, no_log=True),
        endpoint_name=dict(type='str', required=True),
        api_base=dict(type='str', required=False),
        provider=dict(type='str', required=False),
        endpoint_api_key=dict(type='str', required=False, no_log=True),
        api_version=dict(type='str', required=False),
        metadata=dict(type='dict', required=False, default={}),
        state=dict(type='str', required=False, choices=['present', 'absent'], default='present'),
        validate_certs=dict(type='bool', required=False, default=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not HAS_REQUESTS:
        module.fail_json(msg=missing_required_lib('requests'), exception=REQUESTS_IMPORT_ERROR)

    manager = LiteLLMEndpointManager(module)
    
    endpoint_name = module.params['endpoint_name']
    api_base = module.params['api_base']
    provider = module.params['provider']
    endpoint_api_key = module.params['endpoint_api_key']
    api_version = module.params['api_version']
    metadata = module.params['metadata']
    state = module.params['state']

    changed = False
    message = ""

    try:
        if state == 'present':
            if not api_base or not provider:
                module.fail_json(msg="api_base e provider sono richiesti quando state è 'present'")
            
            # Verifica se l'endpoint esiste già
            existing_endpoint = manager.get_endpoint(endpoint_name)
            
            if existing_endpoint:
                message = f"Endpoint '{endpoint_name}' già esistente"
            else:
                result = manager.create_endpoint(endpoint_name, api_base, provider, endpoint_api_key, api_version, metadata)
                changed = True
                message = f"Endpoint '{endpoint_name}' creato con successo"
                
        elif state == 'absent':
            # Verifica se l'endpoint esiste
            existing_endpoint = manager.get_endpoint(endpoint_name)
            
            if existing_endpoint:
                # Prova a eliminare l'endpoint
                try:
                    manager.delete_endpoint(endpoint_name)
                    changed = True
                    message = f"Endpoint '{endpoint_name}' eliminato con successo"
                except Exception as e:
                    module.fail_json(msg=str(e))
            else:
                message = f"Endpoint '{endpoint_name}' non trovato"

        module.exit_json(
            changed=changed,
            message=message,
            endpoint=manager.get_endpoint(endpoint_name) if state == 'present' else None
        )

    except Exception as e:
        module.fail_json(msg=f"Errore imprevisto: {str(e)}")


if __name__ == '__main__':
    main()