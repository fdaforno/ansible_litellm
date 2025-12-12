# Ansible Collection - fdaforno.ansible_collection_litellm

This collection provides Ansible modules to manage LiteLLM, focusing on:
- Team management
- Virtual key management
- Model management
- Endpoint management

## Installation

```bash
ansible-galaxy collection install fdaforno.ansible_collection_litellm
```

## Requirements

- Ansible >= 2.9
- Python >= 3.8
- API access to LiteLLM

## Available Modules

### litellm_team
Manages teams in LiteLLM

### litellm_virtual_key
Manages virtual keys in LiteLLM

### litellm_model
Manages models in LiteLLM

### litellm_endpoint
Manages endpoints in LiteLLM

## Usage Example

```yaml
---
- name: Manage LiteLLM
  hosts: localhost
  collections:
    - fdaforno.litellm
  
  tasks:
    - name: Create a team
      litellm_team:
        api_url: "https://your-litellm-instance.com"
        api_key: "{{ litellm_api_key }}"
        name: "data-science-team"
        state: present
    
    - name: Create a virtual key
      litellm_virtual_key:
        api_url: "https://your-litellm-instance.com"
        api_key: "{{ litellm_api_key }}"
        team_id: "{{ team_id }}"
        key_alias: "ds-team-key"
        state: present

    - name: Add a model
      litellm_model:
        api_url: "https://your-litellm-instance.com"
        api_key: "{{ litellm_api_key }}"
        model_name: "gpt-4"
        litellm_params:
          model: "gpt-4"
          api_key: "{{ openai_api_key }}"
        state: present

    - name: Add an endpoint
      litellm_endpoint:
        api_url: "https://your-litellm-instance.com"
        api_key: "{{ litellm_api_key }}"
        endpoint_name: "openai-prod"
        api_base: "https://api.openai.com/v1"
        provider: "openai"
        state: present
```

## License

MIT
