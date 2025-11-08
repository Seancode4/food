"""
Helpers that call HSWS XML endpoints and return JSON-friendly dicts.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests

BASE_URL = os.getenv("FOOD_API_BASE_URL", "https://diningfeed.dartmouth.edu/hsws/")


def _build_url(path: str) -> str:
    base = BASE_URL.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def _clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _request_xml(path: str, params: Optional[Dict[str, Any]] = None) -> ET.Element:
    response = requests.get(_build_url(path), params=params)
    response.raise_for_status()
    return ET.fromstring(response.content)


def _format_date(value: str) -> str:
    stripped = value.strip()
    return stripped.replace("-", "")


def _xml_to_dict(element: ET.Element) -> Any:
    children = list(element)
    node: Dict[str, Any] = {}

    if element.attrib:
        node.update(element.attrib)

    if children:
        for child in children:
            child_value = _xml_to_dict(child)
            tag = child.tag
            if tag in node:
                current = node[tag]
                if isinstance(current, list):
                    current.append(child_value)
                else:
                    node[tag] = [current, child_value]
            else:
                node[tag] = child_value
    text = (element.text or "").strip()
    if text:
        if node:
            node["value"] = text
        else:
            return text
    if not node:
        return None
    return node


def list_nutrients() -> Dict[str, Any]:
    root = _request_xml("nutrient/list")
    return {root.tag: _xml_to_dict(root)}


def list_menus(
    date: str,
    meal_id: Optional[int] = None,
    menu_type_id: Optional[str] = None,
) -> Dict[str, Any]:
    params = _clean_params(
        {
            "date": _format_date(date),
            "meal": meal_id,
            "menutype": menu_type_id,
        }
    )
    root = _request_xml("menu/list", params=params)
    return {root.tag: _xml_to_dict(root)}


def get_menu_detail(
    menu_id: str,
    *,
    exclude_subingredients: bool = False,
    nutrients: str = "none",
    rounding: str = "raw",
) -> Dict[str, Any]:
    params = _clean_params(
        {
            "id": menu_id,
            "exclude_subingredients": "t" if exclude_subingredients else "f",
            "nutrients": nutrients,
            "roundingmethod": rounding,
        }
    )
    root = _request_xml("menu", params=params)
    return {root.tag: _xml_to_dict(root)}


def get_recipe_detail(
    recipe_id: str,
    *,
    include_ingredients: bool = False,
    include_method: bool = False,
    include_ldas: bool = False,
    nutrients: str = "none",
    rounding: str = "raw",
) -> Dict[str, Any]:
    params = _clean_params(
        {
            "id": recipe_id,
            "ingredients": "True" if include_ingredients else None,
            "methods": "text" if include_method else None,
            "ldas": "True" if include_ldas else None,
            "nutrients": nutrients,
            "roundingmethod": rounding,
        }
    )
    root = _request_xml("recipe", params=params)
    return {root.tag: _xml_to_dict(root)}
