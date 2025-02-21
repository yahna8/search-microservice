"""
Author: Abigail Yahn
Created: 2025

Description:
---------------
This FastAPI-based microservice provides a search functionality for both
external APIs (e.g., Open Library) and local data sources (e.g., a user's
library, inventory or store database).

Features:
---------------
- Searches external sources like Open Library for books.
- Searches local user data (e.g., inventory, store items) with fuzzy matching.
- Uses `rapidfuzz` for approximate string matching.
- Follows microservice architecture by communicating with other services over HTTP.
"""

from fastapi import FastAPI, HTTPException, Query
import requests
from rapidfuzz import process, fuzz

# Initialize FastAPI application
app = FastAPI()

# External API source
EXTERNAL_API = "https://openlibrary.org/search.json"

# Main Program API Endpoint
MAIN_APP_API = "http://127.0.0.1:5001/get_data"


def search_external_api(source: str, query: str, limit: int):
    """
    Searches an external API based on the specified source.

    Args:
    source (str): The type of external data source (e.g., "books").
    query (str): The search term.
    limit (int): Maximum number of results to return.

    Returns:
    list: A list of matched items from the external API.
    """
    if source not in EXTERNAL_API:
        return []

    try:
        response = requests.get(EXTERNAL_API[source], params={"q": query})
        response.raise_for_status()
        data = response.json()

         # Extract relevant data based on source type
        return [
            {"title": item.get("title", "Unknown Item"), "author": ", ".join(item.get("author_name", ["Unknown Author"]))}
            for item in data.get("docs", [])[:limit]
        ] if source == "books" else data[:limit]

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error contacting external API: {str(e)}")


def get_local_data(source: str):
    """
    Fetches locally stored data from the main program's API.

    Args:
        source (str): The type of local data source (e.g., "inventory").

    Returns:
        list: A list of locally stored items.
    """
    if source not in MAIN_APP_API:
        return []

    try:
        response = requests.get(MAIN_APP_API[source])
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error contacting main app API: {str(e)}")


def search_local_data(source: str, query: str, fuzz_threshold: int, limit: int):
    """
    Searches local data from the main program API using fuzzy matching.

    Args:
        source (str): The type of local data source (e.g., "inventory").
        query (str): The search term.
        fuzz_threshold (int): The minimum match threshold (0-100) for fuzzy matching.
        limit (int): Maximum number of results to return.

    Returns:
        list: A list of matched local items.
    """
    local_data = get_local_data(source)
    if not local_data:
        return []

    filtered_data = [
        item for item in local_data
        if process.extractOne(query, [item["title"]], scorer=fuzz.partial_ratio)[1] >= fuzz_threshold
    ]
    return filtered_data[:limit]


@app.get("/search_external")
def search_external_endpoint(
    source: str = Query(..., description="Source type (e.g., books, store)"),
    query: str = Query(..., description="Search term"),
    limit: int = Query(5, description="Number of results to return")
):
    """
    API endpoint to search external APIs dynamically.

    Example request:
        GET /search_external?source=books&query=harry+potter&limit=5

    Args:
        source (str): The external data source type.
        query (str): The search term.
        limit (int): The maximum number of results to return.

    Returns:
        dict: JSON response containing search results.
    """
    results = search_external_api(source, query, limit)
    return {"results": results} if results else {"message": "No results found."}


@app.get("/search_local")
def search_local_endpoint(
    source: str = Query(..., description="Source type (e.g., books, inventory)"),
    query: str = Query(..., description="Search term"),
    fuzz_threshold: int = Query(80, description="Fuzzy match threshold (0-100)"),
    limit: int = Query(5, description="Number of results to return")
):
    """
    API endpoint to search locally stored user data from the main program.

    Example request:
        GET /search_local?source=inventory&query=potion&fuzz_threshold=80&limit=3

    Args:
        source (str): The local data source type.
        query (str): The search term.
        fuzz_threshold (int): Minimum similarity score for fuzzy matching (0-100).
        limit (int): Maximum number of results to return.

    Returns:
        dict: JSON response containing search results.
    """
    results = search_local_data(source, query, fuzz_threshold, limit)
    return {"results": results} if results else {"message": "No results found."}
