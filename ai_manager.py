import os
import json
from pathlib import Path
from shared.openai_config import get_openai_client

class AgentBuilder:
    
    def __init__(self, client):
        self.client = client
        self.existing_assistants = {}
        self.agents_path = "agents"
        self.ai_tool = self.initialize_ai_tool()

    def initialize_ai_tool(self):
        # Placeholder for AI tool initialization
        return None

    def get_existing_assistants(self):
        if not self.existing_assistants:
            assistants = self.client.beta.assistants.list(limit=100)
            self.existing_assistants = {assistant.name: assistant for assistant in assistants}

    def analyze_agent_folder(self, agent_folder):
        # AI-powered analysis of the agent folder
        return self.ai_tool.analyze_folder(agent_folder) if self.ai_tool else {}

    def read_file(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

    def load_json(self, json_path):
        with open(json_path, 'r') as f:
            return json.load(f)

    def get_files_from_folder(self, folder_path):
        files = []
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'rb') as file_data:
                    file_object = self.client.files.create(file=file_data, purpose='assistants')
                    files.append({"name": filename, "id": file_object.id})
        return files

    def update_existing_agent(self, agent_name, existing_agent, settings, instructions, files, requested_files):
        update_params = {}
        existing_files = {file.filename: file for file in existing_agent.files}
        requested_files_set = set(requested_files)
        existing_files_set = set(existing_files.keys())

        if existing_agent.model != settings["model"]:
            update_params["model"] = settings["model"]
        if existing_agent.instructions != instructions:
            update_params["instructions"] = instructions
        if existing_agent.description != settings["description"]:
            update_params["description"] = settings["description"]
        if files or requested_files_set != existing_files_set:
            all_file_ids = [existing_files[key].id for key in existing_files_set.intersection(requested_files_set)]
            all_file_ids += [file['id'] for file in files]
            update_params['file_ids'] = all_file_ids
            if not any(tool.type == "retrieval" for tool in existing_agent.tools):
                update_params['tools'] = existing_agent.tools + [{'type': 'retrieval'}]
        if any(
            tool.type != setting_tool["type"]
            for tool, setting_tool in zip(existing_agent.tools, settings["tools"])
        ):
            update_params['tools'] = settings["tools"]
            if files:
                update_params['tools'].append({'type': 'retrieval'})

        if update_params:
            update_params['assistant_id'] = existing_agent.id
            self.client.beta.assistants.update(**update_params)
        else:
            print(f"{agent_name} is up to date")

    def create_assistant(self, agent_name):
        current_file_path = Path(__file__).absolute().parent
        agent_folder = os.path.join(current_file_path, self.agents_path, agent_name)

        if not os.path.exists(agent_folder) or not os.path.isdir(agent_folder) or not os.listdir(agent_folder):
            raise ValueError(f'{agent_folder} is missing, not a directory, or empty.')

        existing_agent = self.existing_assistants.get(agent_name, {})
        instructions = self.read_file(os.path.join(agent_folder, "instructions.md")) if os.path.isfile(os.path.join(agent_folder, "instructions.md")) else ""
        settings = self.load_json(os.path.join(agent_folder, 'settings.json')) if os.path.isfile(os.path.join(agent_folder, 'settings.json')) else {}
        files = self.get_files_from_folder(os.path.join(agent_folder, 'files'))
        requested_files = [file['name'] for file in files]

        if existing_agent:
            print(f"{agent_name} already exists... validating properties")
            self.update_existing_agent(agent_name, existing_agent, settings, instructions, files, requested_files)
        else:
            create_params = {
                "name": agent_name,
                "instructions": instructions,
                "description": settings["description"],
                "model": settings["model"],
                "tools": settings["tools"]
            }
            if files:
                create_params['tools'].append({'type': 'retrieval'})
                create_params['file_ids'] = [file['id'] for file in files]
            self.client.beta.assistants.create(**create_params)
        print("***********************************************")

    def create_assistants(self):
        agents_path = os.path.join(Path(__file__).absolute().parent, self.agents_path)

        if not os.path.exists(agents_path) or not os.path.isdir(agents_path) or not os.listdir(agents_path):
            raise ValueError(f'The "{self.agents_path}" folder is missing, not a directory, or empty.')

        self.get_existing_assistants()

        for agent_name in os.listdir(agents_path):
            self.create_assistant(agent_name)

if __name__ == '__main__':
    client = get_openai_client()
    agent_builder = AgentBuilder(client=client)
    agent_builder.create_assistants()
