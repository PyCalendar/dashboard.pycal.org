"""A page as HTML, or its public information as JSON at ``<page>.json``."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render


def wants_json(request: HttpRequest) -> bool:
    """Whether the request asks for the JSON of a page, see :mod:`pycal_dashboard.public_json`.

    Parameters:
        request: The request.

    Returns:
        True for ``<page>.json``.
    """
    return getattr(request, "public_json", False)


def page(
    request: HttpRequest,
    template: str,
    context: dict,
    data: Callable[[], dict],
    status: int = 200,
):
    """Answer with the page, or with its data for ``<page>.json``.

    Parameters:
        request: The request.
        template: The template of the page.
        context: The context of the template.
        data: A function without arguments that returns the public information of the
            page; called only for the JSON.
        status: The HTTP status.

    Returns:
        The page or the JSON.
    """
    if wants_json(request):
        return JsonResponse(data(), status=status, json_dumps_params={"ensure_ascii": False})
    return render(request, template, context, status=status)
