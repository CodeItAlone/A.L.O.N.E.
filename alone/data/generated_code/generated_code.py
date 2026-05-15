import yaml

def read_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

print(read_config())