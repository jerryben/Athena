from backend.services.memory_service import memory_service


def get_user_memory(query: str):
    results = memory_service.search(query=query)

    return {
        "query": query,
        "results": results,
    }