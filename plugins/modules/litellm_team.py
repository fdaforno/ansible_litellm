#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Federico Daforno
# MIT License

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: litellm_team

short_description: Manages teams in LiteLLM

version_added: "1.0.0"

description:
    - This module allows you to create, modify, and delete teams in LiteLLM
    - Supports complete team management including metadata and configurations

options:
    api_url:
        description:
            - URL of the LiteLLM instance
        required: true
        type: str
    api_key:
        description:
            - API key for authentication with LiteLLM
        required: true
        type: str
    team_id:
        description:
            - Unique team ID (used for update/delete)
        required: false
        type: str
    name:
        description:
            - Team name
        required: false
        type: str
    metadata:
        description:
            - Additional metadata for the team
        required: false
        type: dict
        default: {}
    max_budget:
        description:
            - Maximum budget for the team
        required: false
        type: float
    models:
        description:
            - List of allowed models for the team
        required: false
        type: list
        elements: str
    state:
        description:
            - Desired state of the team
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
# Create a new team
- name: Create data science team
  fdaforno.ansible_collection_litellm.litellm_team:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_api_key }}"
    name: "data-science-team"
    max_budget: 1000.0
    models:
      - gpt-4
      - gpt-3.5-turbo
    metadata:
      department: "AI Research"
    state: present

# Update an existing team
- name: Update team budget
  fdaforno.ansible_collection_litellm.litellm_team:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_api_key }}"
    team_id: "team-123"
    max_budget: 2000.0
    state: present

# Delete a team
- name: Delete team
  fdaforno.ansible_collection_litellm.litellm_team:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_api_key }}"
    team_id: "team-123"
    state: absent
'''

RETURN = r'''
team:
    description: Information about the created/modified team
    type: dict
    returned: when state is present
    sample:
        team_id: "team-123"
        name: "data-science-team"
        max_budget: 1000.0
        models: ["gpt-4", "gpt-3.5-turbo"]
        metadata:
            department: "AI Research"
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


class LiteLLMTeamManager:
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

    def get_team(self, team_id):
        """Recupera le informazioni di un team"""
        response = self._make_request('GET', f'/team/{team_id}')
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            self.module.fail_json(msg=f"Errore nel recupero del team: {response.status_code} - {response.text}")

    def get_team_by_name(self, name):
        """Cerca un team per nome"""
        response = self._make_request('GET', '/team/list')
        
        if response.status_code == 200:
            data = response.json()
            # Gestisci sia il caso in cui la risposta è una lista diretta, sia un dict con chiave 'teams'
            if isinstance(data, list):
                teams = data
            else:
                teams = data.get('teams', [])
            
            for team in teams:
                if team.get('team_alias') == name or team.get('team_name') == name:
                    return team
            return None
        else:
            self.module.fail_json(msg=f"Errore nella ricerca del team: {response.status_code} - {response.text}")

    def create_team(self, name, metadata, max_budget, models):
        """Crea un nuovo team"""
        data = {
            'team_alias': name,
        }
        
        if metadata:
            data['metadata'] = metadata
        if max_budget is not None:
            data['max_budget'] = max_budget
        if models:
            data['models'] = models
        
        response = self._make_request('POST', '/team/new', data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nella creazione del team: {response.status_code} - {response.text}")

    def update_team(self, team_id, name, metadata, max_budget, models):
        """Aggiorna un team esistente"""
        data = {
            'team_id': team_id
        }
        
        if name:
            data['team_alias'] = name
        if metadata is not None:
            data['metadata'] = metadata
        if max_budget is not None:
            data['max_budget'] = max_budget
        if models is not None:
            data['models'] = models
        
        response = self._make_request('POST', '/team/update', data)
        
        if response.status_code == 200:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nell'aggiornamento del team: {response.status_code} - {response.text}")

    def delete_team(self, team_id):
        """Elimina un team"""
        data = {'team_ids': [team_id]}
        response = self._make_request('POST', '/team/delete', data)
        
        if response.status_code == 200:
            return True
        else:
            self.module.fail_json(msg=f"Errore nell'eliminazione del team: {response.status_code} - {response.text}")

    def team_needs_update(self, current_team, name, metadata, max_budget, models):
        """Verifica se il team necessita di aggiornamenti"""
        needs_update = False
        
        if name and current_team.get('team_alias') != name:
            needs_update = True
        
        if metadata is not None and current_team.get('metadata') != metadata:
            needs_update = True
        
        if max_budget is not None and current_team.get('max_budget') != max_budget:
            needs_update = True
        
        if models is not None:
            current_models = set(current_team.get('models', []))
            new_models = set(models)
            if current_models != new_models:
                needs_update = True
        
        return needs_update


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type='str', required=True),
            api_key=dict(type='str', required=True, no_log=True),
            team_id=dict(type='str', required=False),
            name=dict(type='str', required=False),
            metadata=dict(type='dict', required=False, default={}),
            max_budget=dict(type='float', required=False),
            models=dict(type='list', elements='str', required=False),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            validate_certs=dict(type='bool', default=True),
        ),
        required_if=[
            ('state', 'present', ('name',), False),
            ('state', 'absent', ('team_id',), False),
        ],
        supports_check_mode=True,
    )

    if not HAS_REQUESTS:
        module.fail_json(msg=missing_required_lib('requests'), exception=REQUESTS_IMPORT_ERROR)

    manager = LiteLLMTeamManager(module)
    
    state = module.params['state']
    team_id = module.params['team_id']
    name = module.params['name']
    metadata = module.params['metadata']
    max_budget = module.params['max_budget']
    models = module.params['models']
    
    result = {
        'changed': False,
        'team': {}
    }

    # Trova il team esistente
    existing_team = None
    if team_id:
        existing_team = manager.get_team(team_id)
    elif name:
        existing_team = manager.get_team_by_name(name)
    
    if state == 'present':
        if existing_team:
            # Team esiste, verifica se serve aggiornamento
            if manager.team_needs_update(existing_team, name, metadata, max_budget, models):
                if not module.check_mode:
                    current_team_id = existing_team.get('team_id')
                    result['team'] = manager.update_team(current_team_id, name, metadata, max_budget, models)
                result['changed'] = True
                result['message'] = 'Team aggiornato con successo'
            else:
                result['team'] = existing_team
                result['message'] = 'Team già esistente con le configurazioni richieste'
        else:
            # Team non esiste, crealo
            if not module.check_mode:
                result['team'] = manager.create_team(name, metadata, max_budget, models)
            result['changed'] = True
            result['message'] = 'Team creato con successo'
    
    elif state == 'absent':
        if existing_team:
            if not module.check_mode:
                current_team_id = existing_team.get('team_id')
                manager.delete_team(current_team_id)
            result['changed'] = True
            result['message'] = 'Team eliminato con successo'
        else:
            result['message'] = 'Team non trovato, nessuna azione necessaria'
    
    module.exit_json(**result)


if __name__ == '__main__':
    main()
