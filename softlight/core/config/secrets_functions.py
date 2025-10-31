import json
import os

import boto3
from botocore.exceptions import ClientError
from dotenv import find_dotenv, load_dotenv
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


def get_softlight_secret_name() -> str:
    load_dotenv(find_dotenv())
    return os.getenv("SOFTLIGHT_SECRET_NAME", "")


def get_softlight_env() -> dict[str, str]:
    return resolve_secret(get_softlight_secret_name())


def load_softlight_env():
    # Suppress logfire warnings early
    os.environ["LOGFIRE_IGNORE_NO_CONFIG"] = "1"
    
    if os.getenv("SOFTLIGHT_SECRET_LOADED", "false").lower() == "false":        
        logger.debug("Loading softlight environment variables")
        env = get_softlight_env()
        for key, value in env.items():
            os.environ[key] = value
        os.environ["SOFTLIGHT_SECRET_LOADED"] = "true"
        load_dotenv(find_dotenv(), override = True) # overlay env vars from local .env


def get_secret_key_value(secret_name: str, key: str) -> str:
    secret = resolve_secret(secret_name)
    return secret.get(key, "")


def get_secretsmanager_client():  # pyright: ignore [reportUnknownParameterType]
    load_dotenv(find_dotenv())
    return boto3.client(
        service_name="secretsmanager",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        region_name=os.getenv("AWS_REGION", "us-west-2"),
    )


def list_secrets() -> list[str]:
    try:
        client = get_secretsmanager_client()
        response = client.list_secrets(MaxResults=100)
        return response.get("SecretList", [])
    except ClientError:
        return []


def search_secrets(prefix: str = "conexio") -> list[str]:
    try:
        client = get_secretsmanager_client()
        response = client.list_secrets(MaxResults=100, Filters=[{"Key": "name", "Values": [prefix]}])
        return [r["Name"] for r in response.get("SecretList", [])]
    except ClientError:
        return []


def get_secret_value(secret_name: str) -> str | None:
    client = get_secretsmanager_client()
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response.get("SecretString")
    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_name}: {e}")
        return None


def get_secret_dict(secret_name: str) -> dict[str, str]:
    secret = get_secret_value(secret_name)
    if secret is None:
        return {}
    return json.loads(secret)


def get_secret_with_overrides(secret_name: str, overrides: dict[str, str]) -> dict[str, str]:
    secret_dict = get_secret_dict(secret_name)
    secret_dict.update(overrides)
    return secret_dict


def resolve_secret(secret_name: str) -> dict[str, str]:
    parents = list_secret_parents(secret_name)
    parents_env = {}
    for parent in parents:
        parent_dict = get_secret_dict(parent)
        parents_env.update(parent_dict)

    secret_dict = parents_env.copy()
    secret_dict.update(get_secret_dict(secret_name))
    return secret_dict


def list_secret_parents(secret_name: str) -> list[str]:
    parents = []
    client = get_secretsmanager_client()
    tokens = secret_name.split("/")
    for i in range(1, len(tokens)):
        parent = "/".join(tokens[:i])
        try:
            client.describe_secret(SecretId=parent)
            parents.append(parent)
        except ClientError:
            continue
    return sorted(parents, key=lambda x: x.count("/"))


def dry_secret(secret_name: str):
    parents = list_secret_parents(secret_name)
    parents_env = {}
    for parent in parents:
        parent_dict = get_secret_dict(parent)
        parents_env.update(parent_dict)

    secret_dict = get_secret_dict(secret_name)
    for key, value in parents_env.items():
        if key in secret_dict and secret_dict[key] == value:
            del secret_dict[key]

    print(secret_dict)
    set_secret(secret_name, dict(sorted(secret_dict.items())))


def dry_tree(secret_name: str):
    secret_list = search_secrets(secret_name)
    nodes = sorted(secret_list, key=lambda x: x.count("/"), reverse=True)
    for node in nodes:
        print(f"Drying {node}")
        dry_secret(node)


def set_secret(secret_name: str, items: dict[str, str]):
    client = get_secretsmanager_client()
    try:
        client.put_secret_value(SecretId=secret_name, SecretString=json.dumps(items))
    except ClientError as e:
        logger.error(f"Error setting secret {secret_name}: {e}")


def update_secret(secret_name: str, items: dict[str, str]):
    client = get_secretsmanager_client()
    try:
        secret = get_secret_value(secret_name)
        if secret is None:
            return
        secret_dict = json.loads(secret)
        secret_dict.update(items)
        client.put_secret_value(SecretId=secret_name, SecretString=json.dumps(secret_dict))
    except ClientError as e:
        logger.error(f"Error updating secret {secret_name}: {e}")


def clone_secret(source: str, destination: str):
    client = get_secretsmanager_client()
    try:
        response = client.describe_secret(SecretId=source)
        description = response.get("Description")
        response = client.get_secret_value(SecretId=source)
        secret = response.get("SecretString")
        client.create_secret(Name=destination, SecretString=secret, Description=description)
    except ClientError as e:
        logger.error(f"Error cloning secret {source} to {destination}: {e}")


def delete_secret(secret_name: str, dryrun: bool=True, delete_without_recovery: bool=False):
    client = get_secretsmanager_client()
    try:
        if dryrun:
            logger.info("Dry run: secret not deleted")
            return
        client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=delete_without_recovery)
    except ClientError as e:
        logger.error(f"Error deleting secret {secret_name}: {e}")


def restore_secret(secret_name: str) -> None:
    client = get_secretsmanager_client()
    try:
        client.restore_secret(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"Error restoring secret {secret_name}: {e}")


def add_env_variable_to_secret(secret_name: str, key: str, value: str):
    logger.info(f"Adding key: {key} to secret: {secret_name}")
    update_secret(secret_name, {key: value})
    logger.success(f"Added/Updated {key} in {secret_name}")

def delete_and_add_secret_key(secret_name: str, old_key: str, new_key: str, new_value: str):
    secret = get_secret_dict(secret_name)

    if old_key in secret:
        print(f"Deleting key: {old_key}")
        del secret[old_key]
    else:
        print(f"Old key '{old_key}' not found, skipping delete")

    print(f"Adding key: {new_key} = {new_value}")
    secret[new_key] = new_value

    set_secret(secret_name, secret)
    print(f"Updated secret '{secret_name}' with new key '{new_key}' and removed '{old_key}'")

def delete_secret_key(secret_name: str, old_key: str):
    secret = get_secret_dict(secret_name)

    if old_key in secret:
        print(f"Deleting key: {old_key}")
        del secret[old_key]
    else:
        print(f"Old key '{old_key}' not found, skipping delete")

    set_secret(secret_name, secret)

if __name__ == "__main__":
    secret_name = "conexio/coco"
    dry_tree(secret_name)
