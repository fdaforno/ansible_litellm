#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Federico Daforno
# MIT License

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: litellm_virtual_key

short_description: Manages virtual keys in LiteLLM

version_added: "1.0.0"

description:
    - This module allows you to create, modify, and delete virtual keys in LiteLLM
    - Supports key association with teams and limit configuration

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
    key_id:
        description:
            - Unique virtual key ID (used for update/delete)
        required: false
        type: str
    key_alias:
        description:
            - Alias/name of the virtual key
        required: false
        type: str
    team_id:
        description:
            - ID of the team to associate the key with
        required: false
        type: str
    models:
        description:
            - List of allowed models for this key
        required: false
        type: list
        elements: str
    max_budget:
        description:
            - Maximum budget for this key
        required: false
        type: float
    budget_duration:
        description:
            - Budget duration (e.g. 30d, 1h)
        required: false
        type: str
    metadata:
        description:
            - Additional metadata for the key
        required: false
        type: dict
        default: {}
    expires:
        description:
            - Key expiration date (ISO format)
        required: false
        type: str
    max_parallel_requests:
        description:
            - Maximum number of parallel requests
        required: false
        type: int
    tpm_limit:
        description:
            - Token per minute limit
        required: false
        type: int
    rpm_limit:
        description:
            - Requests per minute limit
        required: false
        type: int
    state:
        description:
            - Desired state of the virtual key
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
# Create a new virtual key
- name: Create virtual key for the team
  fdaforno.ansible_collection_litellm.litellm_virtual_key:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    key_alias: "ds-team-prod-key"
    team_id: "team-123"
    models:
      - gpt-4
      - gpt-3.5-turbo
    max_budget: 500.0
    budget_duration: "30d"
    tpm_limit: 100000
    rpm_limit: 1000
    metadata:
      environment: "production"
      owner: "data-science"
    state: present

# Create a virtual key with expiration
- name: Create temporary virtual key
  fdaforno.ansible_collection_litellm.litellm_virtual_key:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    key_alias: "temp-key"
    team_id: "team-123"
    expires: "2025-12-31T23:59:59"
    state: present

# Update an existing virtual key
- name: Update key budget
  fdaforno.ansible_collection_litellm.litellm_virtual_key:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    key_id: "key-456"
    max_budget: 1000.0
    state: present

# Delete a virtual key
- name: Delete virtual key
  fdaforno.ansible_collection_litellm.litellm_virtual_key:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    key_id: "key-456"
    state: absent
'''

RETURN = r'''
virtual_key:
    description: Information about the created/modified virtual key
    type: dict
    returned: when state is present
    sample:
        key: "sk-xxxxxxxxxxxxxxxxx"
        key_name: "ds-team-prod-key"
        team_id: "team-123"
        max_budget: 500.0
        models: ["gpt-4", "gpt-3.5-turbo"]
        tpm_limit: 100000
        rpm_limit: 1000
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


class LiteLLMVirtualKeyManager:
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

    def get_key(self, key_id):
        """Recupera le informazioni di una virtual key"""
        response = self._make_request('GET', f'/key/info?key={key_id}')
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            self.module.fail_json(msg=f"Errore nel recupero della key: {response.status_code} - {response.text}")

    def get_key_by_alias(self, alias):
        """Cerca una virtual key per alias"""
        response = self._make_request('GET', '/key/list')
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Gestisci sia il caso in cui la risposta è una lista diretta, sia un dict con chiave 'keys'
                if isinstance(data, list):
                    keys = data
                elif isinstance(data, dict):
                    keys = data.get('keys', [])
                else:
                    # Se non è né lista né dict, potrebbe essere una risposta di errore
                    self.module.fail_json(msg=f"Risposta API non valida per /key/list: {data}")
                    return None
            except ValueError:
                # Se response.json() fallisce, la risposta potrebbe essere testo semplice
                self.module.fail_json(msg=f"Risposta non JSON valida da /key/list: {response.text}")
                return None
            
            for key in keys:
                if isinstance(key, dict) and (key.get('key_alias') == alias or key.get('key_name') == alias):
                    return key
            return None
        else:
            self.module.fail_json(msg=f"Errore nella ricerca della key: {response.status_code} - {response.text}")

    def create_key(self, key_alias, team_id, models, max_budget, budget_duration, 
                   metadata, expires, max_parallel_requests, tpm_limit, rpm_limit):
        """Crea una nuova virtual key"""
        data = {}
        
        if key_alias:
            data['key_alias'] = key_alias
        if team_id:
            data['team_id'] = team_id
        if models:
            data['models'] = models
        if max_budget is not None:
            data['max_budget'] = max_budget
        if budget_duration:
            data['budget_duration'] = budget_duration
        if metadata:
            data['metadata'] = metadata
        if expires:
            data['expires'] = expires
        if max_parallel_requests is not None:
            data['max_parallel_requests'] = max_parallel_requests
        if tpm_limit is not None:
            data['tpm_limit'] = tpm_limit
        if rpm_limit is not None:
            data['rpm_limit'] = rpm_limit
        
        response = self._make_request('POST', '/key/generate', data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nella creazione della key: {response.status_code} - {response.text}")

    def update_key(self, key_id, key_alias, team_id, models, max_budget, budget_duration,
                   metadata, expires, max_parallel_requests, tpm_limit, rpm_limit):
        """Aggiorna una virtual key esistente"""
        data = {
            'key': key_id
        }
        
        if key_alias:
            data['key_alias'] = key_alias
        if team_id:
            data['team_id'] = team_id
        if models is not None:
            data['models'] = models
        if max_budget is not None:
            data['max_budget'] = max_budget
        if budget_duration:
            data['budget_duration'] = budget_duration
        if metadata is not None:
            data['metadata'] = metadata
        if expires:
            data['expires'] = expires
        if max_parallel_requests is not None:
            data['max_parallel_requests'] = max_parallel_requests
        if tpm_limit is not None:
            data['tpm_limit'] = tpm_limit
        if rpm_limit is not None:
            data['rpm_limit'] = rpm_limit
        
        response = self._make_request('POST', '/key/update', data)
        
        if response.status_code == 200:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nell'aggiornamento della key: {response.status_code} - {response.text}")

    def delete_key(self, key_id):
        """Elimina una virtual key"""
        data = {'keys': [key_id]}
        response = self._make_request('POST', '/key/delete', data)
        
        if response.status_code == 200:
            return True
        else:
            self.module.fail_json(msg=f"Errore nell'eliminazione della key: {response.status_code} - {response.text}")

    def key_needs_update(self, current_key, key_alias, team_id, models, max_budget, 
                        budget_duration, metadata, expires, max_parallel_requests, 
                        tpm_limit, rpm_limit):
        """Verifica se la key necessita di aggiornamenti"""
        needs_update = False
        
        if key_alias and current_key.get('key_alias') != key_alias:
            needs_update = True
        
        if team_id and current_key.get('team_id') != team_id:
            needs_update = True
        
        if models is not None:
            current_models = set(current_key.get('models', []))
            new_models = set(models)
            if current_models != new_models:
                needs_update = True
        
        if max_budget is not None and current_key.get('max_budget') != max_budget:
            needs_update = True
        
        if budget_duration and current_key.get('budget_duration') != budget_duration:
            needs_update = True
        
        if metadata is not None and current_key.get('metadata') != metadata:
            needs_update = True
        
        if expires and current_key.get('expires') != expires:
            needs_update = True
        
        if max_parallel_requests is not None and current_key.get('max_parallel_requests') != max_parallel_requests:
            needs_update = True
        
        if tpm_limit is not None and current_key.get('tpm_limit') != tpm_limit:
            needs_update = True
        
        if rpm_limit is not None and current_key.get('rpm_limit') != rpm_limit:
            needs_update = True
        
        return needs_update


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type='str', required=True),
            api_key=dict(type='str', required=True, no_log=True),
            key_id=dict(type='str', required=False),
            key_alias=dict(type='str', required=False),
            team_id=dict(type='str', required=False),
            models=dict(type='list', elements='str', required=False),
            max_budget=dict(type='float', required=False),
            budget_duration=dict(type='str', required=False),
            metadata=dict(type='dict', required=False, default={}),
            expires=dict(type='str', required=False),
            max_parallel_requests=dict(type='int', required=False),
            tpm_limit=dict(type='int', required=False),
            rpm_limit=dict(type='int', required=False),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            validate_certs=dict(type='bool', default=True),
        ),
        required_if=[
            ('state', 'absent', ('key_id',), False),
        ],
        supports_check_mode=True,
    )

    if not HAS_REQUESTS:
        module.fail_json(msg=missing_required_lib('requests'), exception=REQUESTS_IMPORT_ERROR)

    manager = LiteLLMVirtualKeyManager(module)
    
    state = module.params['state']
    key_id = module.params['key_id']
    key_alias = module.params['key_alias']
    team_id = module.params['team_id']
    models = module.params['models']
    max_budget = module.params['max_budget']
    budget_duration = module.params['budget_duration']
    metadata = module.params['metadata']
    expires = module.params['expires']
    max_parallel_requests = module.params['max_parallel_requests']
    tpm_limit = module.params['tpm_limit']
    rpm_limit = module.params['rpm_limit']
    
    result = {
        'changed': False,
        'virtual_key': {}
    }

    # Trova la key esistente
    existing_key = None
    if key_id:
        existing_key = manager.get_key(key_id)
    elif key_alias:
        existing_key = manager.get_key_by_alias(key_alias)
    
    if state == 'present':
        if existing_key:
            # Key esiste, verifica se serve aggiornamento
            if manager.key_needs_update(existing_key, key_alias, team_id, models, 
                                       max_budget, budget_duration, metadata, expires,
                                       max_parallel_requests, tpm_limit, rpm_limit):
                if not module.check_mode:
                    current_key_id = existing_key.get('token') or existing_key.get('key')
                    result['virtual_key'] = manager.update_key(
                        current_key_id, key_alias, team_id, models, max_budget, 
                        budget_duration, metadata, expires, max_parallel_requests, 
                        tpm_limit, rpm_limit
                    )
                result['changed'] = True
                result['message'] = 'Virtual key aggiornata con successo'
            else:
                result['virtual_key'] = existing_key
                result['message'] = 'Virtual key già esistente con le configurazioni richieste'
        else:
            # Key non esiste, creala
            if not module.check_mode:
                result['virtual_key'] = manager.create_key(
                    key_alias, team_id, models, max_budget, budget_duration, 
                    metadata, expires, max_parallel_requests, tpm_limit, rpm_limit
                )
            result['changed'] = True
            result['message'] = 'Virtual key creata con successo'
    
    elif state == 'absent':
        if existing_key:
            if not module.check_mode:
                current_key_id = existing_key.get('token') or existing_key.get('key')
                manager.delete_key(current_key_id)
            result['changed'] = True
            result['message'] = 'Virtual key eliminata con successo'
        else:
            result['message'] = 'Virtual key non trovata, nessuna azione necessaria'
    
    module.exit_json(**result)


if __name__ == '__main__':
    main()
