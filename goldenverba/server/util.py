import os
import shelve
from fastapi import HTTPException

from wasabi import msg  # type: ignore[import]

def get_openai_api_config():
    return {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "api_type": os.getenv("OPENAI_API_TYPE"),
        "api_base": os.getenv("OPENAI_API_BASE"),
        "api_version": os.getenv("OPENAI_API_VERSION"),
        "model": os.getenv("VERBA_MODEL", default="gpt-4")
    }

def check_api_key():
    if "OPENAI_API_KEY" in os.environ:
        return True
    weaviate_tenant = os.getenv('WEAVIATE_TENANT',default='default_tenant')
    with shelve.open(f"shelve/key_cache_{weaviate_tenant}") as db:
        key = db.get("api_key",None)
    if key:
        os.environ["OPENAI_API_KEY"] = key
        return True
    return False


def check_manager_initialized(manager):
    if manager == None:
        raise HTTPException(503, "Verba not initialized. Please upload a key using /api/set_openai_key")


def store_api_key(key):
    weaviate_tenant = os.getenv('WEAVIATE_TENANT', default='default_tenant')
    with shelve.open(f"shelve/key_cache_{weaviate_tenant}") as db:
        db["api_key"] = key
    
    msg.info(f"Open AI API key for tenant {weaviate_tenant} stored in shelve/key_cache_{weaviate_tenant}")


def remove_api_key():
    os.environ.pop("OPENAI_API_KEY", None)
    msg.info("OPENAI_API_KEY removed for env variables")

    weaviate_tenant = os.getenv("WEAVIATE_TENANT", default="default_tenant")
    with shelve.open(f"shelve/key_cache_{weaviate_tenant}") as db:
        if "api_key" in db:
            del db["api_key"]
            msg.info(f"OPENAI_API_KEY for tenant {weaviate_tenant} removed for shelve: shelve/key_cache_{weaviate_tenant}")
        else:
            msg.info(f"{weaviate_tenant} is not in the shelve database.")

def get_api_key_preview(api_key: str, preview_length: int = 3) -> str:
    if len(api_key) < 2 * preview_length + 1:
        # API Key is too short to provide a meaningful preview that hides anything.
        return "*" * len(api_key)
    return (
        api_key[:preview_length]
        + "*" * (len(api_key) - 2 * preview_length)
        + api_key[-preview_length:]
    )

def setup_managers(
    manager, config_manager, readers, chunker, embedders, retrievers, generators
):
    if not check_api_key():
        msg.info("OPENAI_API_KEY is not set, managers will not setup")
        return
    
    if config_manager.get_reader() == "":
        for reader in readers:
            available, message = manager.check_verba_component(readers[reader])
            if available:
                manager.reader_set_reader(reader)
                config_manager.set_reader(reader)
                break
    else:
        if config_manager.get_reader() in readers:
            available, message = manager.check_verba_component(
                readers[config_manager.get_reader()]
            )
            if available:
                manager.reader_set_reader(config_manager.get_reader())
            else:
                for reader in readers:
                    available, message = manager.check_verba_component(readers[reader])
                    if available:
                        manager.reader_set_reader(reader)
                        config_manager.set_reader(reader)
                        break

    if config_manager.get_chunker() == "":
        for chunk in chunker:
            available, message = manager.check_verba_component(chunker[chunk])
            if available:
                manager.chunker_set_chunker(chunk)
                config_manager.set_chunker(chunk)
                break
    else:
        if config_manager.get_chunker() in chunker:
            available, message = manager.check_verba_component(
                chunker[config_manager.get_chunker()]
            )
            if available:
                manager.chunker_set_chunker(config_manager.get_chunker())
            else:
                for chunk in chunker:
                    available, message = manager.check_verba_component(chunker[chunk])
                    if available:
                        manager.chunker_set_chunker(chunk)
                        config_manager.set_chunker(chunk)
                        break

    if config_manager.get_embedder() == "":
        for embedder in embedders:
            available, message = manager.check_verba_component(embedders[embedder])
            if available:
                manager.embedder_set_embedder(embedder)
                config_manager.set_embedder(embedder)
                break
    else:
        if config_manager.get_embedder() in embedders:
            available, message = manager.check_verba_component(
                embedders[config_manager.get_embedder()]
            )
            if available:
                manager.embedder_set_embedder(config_manager.get_embedder())
            else:
                for embedder in embedders:
                    available, message = manager.check_verba_component(
                        embedders[embedder]
                    )
                    if available:
                        manager.embedder_set_embedder(embedder)
                        config_manager.set_embedder(embedder)
                        break

    if config_manager.get_retriever() == "":
        for retriever in retrievers:
            available, message = manager.check_verba_component(retrievers[retriever])
            if available:
                manager.retriever_set_retriever(retriever)
                config_manager.set_retriever(retriever)
                break
    else:
        if config_manager.get_retriever() in retrievers:
            available, message = manager.check_verba_component(
                retrievers[config_manager.get_retriever()]
            )
            if available:
                manager.retriever_set_retriever(config_manager.get_retriever())
            else:
                for retriever in retrievers:
                    available, message = manager.check_verba_component(
                        retrievers[retriever]
                    )
                    if available:
                        manager.retriever_set_retriever(retriever)
                        config_manager.set_retriever(retriever)
                        break

    if config_manager.get_generator() == "":
        for generator in generators:
            available, message = manager.check_verba_component(generators[generator])
            if available:
                manager.generator_set_generator(generator)
                config_manager.set_generator(generator)
                break
    else:
        if config_manager.get_generator() in generators:
            available, message = manager.check_verba_component(
                generators[config_manager.get_generator()]
            )
            if available:
                manager.generator_set_generator(config_manager.get_generator())
            else:
                for generator in generators:
                    available, message = manager.check_verba_component(
                        generators[generator]
                    )
                    if available:
                        manager.generator_set_generator(generator)
                        config_manager.set_generator(generator)
                        break
