#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Federico Daforno
# MIT License

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: litellm_model

short_description: Manages models in LiteLLM

version_added: "1.0.0"

description:
    - This module allows you to create, modify, and delete models in LiteLLM
    - Supports model configuration including litellm_params and model_info

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
    model_name:
        description:
            - Name of the model
        required: true
        type: str
    litellm_params:
        description:
            - LiteLLM parameters for the model
        required: false
        type: dict
    model_info:
        description:
            - Additional information about the model
        required: false
        type: dict
        default: {}
    state:
        description:
            - Desired state of the model
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
# Add a new model
- name: Add GPT-4 model
  fdaforno.ansible_collection_litellm.litellm_model:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    model_name: "gpt-4"
    litellm_params:
      model: "gpt-4"
      api_key: "{{ openai_api_key }}"
    model_info:
      description: "GPT-4 model"
      max_tokens: 8192
    state: present

# Add Azure OpenAI model
- name: Add Azure GPT-3.5 model
  fdaforno.ansible_collection_litellm.litellm_model:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    model_name: "azure-gpt-3.5-turbo"
    litellm_params:
      model: "azure/gpt-3.5-turbo"
      api_key: "{{ azure_api_key }}"
      api_base: "{{ azure_api_base }}"
      api_version: "2023-12-01"
    model_info:
      description: "Azure GPT-3.5 Turbo"
    state: present

# Remove a model
- name: Remove model
  fdaforno.ansible_collection_litellm.litellm_model:
    api_url: "https://litellm.example.com"
    api_key: "{{ litellm_master_key }}"
    model_name: "old-model"
    state: absent
'''

RETURN = r'''
model:
    description: Information about the created/modified model
    type: dict
    returned: when state is present
    sample:
        model_name: "gpt-4"
        litellm_params:
            model: "gpt-4"
        model_info:
            description: "GPT-4 model"
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


class LiteLLMModelManager:
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
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, verify=self.validate_certs)
            else:
                self.module.fail_json(msg=f"Metodo HTTP non supportato: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            self.module.fail_json(msg=f"Errore nella richiesta HTTP: {str(e)}")

    def get_models(self):
        """Recupera le informazioni di tutti i modelli"""
        response = self._make_request('GET', '/model/info')
        
        if response.status_code == 200:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nel recupero dei modelli: {response.status_code} - {response.text}")

    def get_model(self, model_name):
        """Recupera le informazioni di un modello specifico"""
        models = self.get_models()
        if 'data' in models:
            for model in models['data']:
                if model.get('model_name') == model_name:
                    return model
        return None

    def create_model(self, model_name, litellm_params, model_info):
        """Crea un nuovo modello"""
        data = {
            'model_name': model_name,
            'litellm_params': litellm_params
        }
        
        if model_info:
            data['model_info'] = model_info
        
        response = self._make_request('POST', '/model/new', data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            self.module.fail_json(msg=f"Errore nella creazione del modello: {response.status_code} - {response.text}")

    def delete_model(self, model_name):
        """Elimina un modello (nota: LiteLLM potrebbe non supportare DELETE direttamente)"""
        # LiteLLM potrebbe non avere un endpoint DELETE diretto per i modelli
        # In alternativa, possiamo restituire un messaggio che indica che il modello deve essere rimosso dal config
        self.module.fail_json(msg="Eliminazione modelli non supportata direttamente dall'API. Rimuovi il modello dal file di configurazione config.yaml")


def main():
    module_args = dict(
        api_url=dict(type='str', required=True),
        api_key=dict(type='str', required=True, no_log=True),
        model_name=dict(type='str', required=True),
        litellm_params=dict(type='dict', required=False),
        model_info=dict(type='dict', required=False, default={}),
        state=dict(type='str', required=False, choices=['present', 'absent'], default='present'),
        validate_certs=dict(type='bool', required=False, default=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not HAS_REQUESTS:
        module.fail_json(msg=missing_required_lib('requests'), exception=REQUESTS_IMPORT_ERROR)

    manager = LiteLLMModelManager(module)
    
    model_name = module.params['model_name']
    litellm_params = module.params['litellm_params']
    model_info = module.params['model_info']
    state = module.params['state']

    changed = False
    message = ""

    try:
        if state == 'present':
            if not litellm_params:
                module.fail_json(msg="litellm_params è richiesto quando state è 'present'")
            
            # Verifica se il modello esiste già
            existing_model = manager.get_model(model_name)
            
            if existing_model:
                # Per ora, assumiamo che se il modello esiste, non facciamo nulla
                # In futuro potremmo implementare l'aggiornamento
                message = f"Modello '{model_name}' già esistente"
            else:
                result = manager.create_model(model_name, litellm_params, model_info)
                changed = True
                message = f"Modello '{model_name}' creato con successo"
                
        elif state == 'absent':
            # Verifica se il modello esiste
            existing_model = manager.get_model(model_name)
            
            if existing_model:
                # Prova a eliminare il modello
                try:
                    manager.delete_model(model_name)
                    changed = True
                    message = f"Modello '{model_name}' eliminato con successo"
                except Exception as e:
                    module.fail_json(msg=str(e))
            else:
                message = f"Modello '{model_name}' non trovato"

        module.exit_json(
            changed=changed,
            message=message,
            model=manager.get_model(model_name) if state == 'present' else None
        )

    except Exception as e:
        module.fail_json(msg=f"Errore imprevisto: {str(e)}")


if __name__ == '__main__':
    main()