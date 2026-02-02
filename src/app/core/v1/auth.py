# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Core library functions for authentication and authorization."""

import json
import logging
from typing import Literal

from fastapi import HTTPException
from nmtfast.auth.v1.acl import AuthSuccess
from nmtfast.auth.v1.api_keys import authenticate_api_key
from nmtfast.auth.v1.exceptions import AuthenticationError
from nmtfast.auth.v1.hash import fingerprint_hash
from nmtfast.auth.v1.jwt import authenticate_token
from nmtfast.cache.v1.base import AppCacheBase
from nmtfast.settings.v1.schemas import SectionACL
from pydantic_core import to_jsonable_python

from app.core.v1.settings import AppSettings

logger = logging.getLogger(__name__)


async def process_api_key_header(
    api_key: str,
    settings: AppSettings,
    cache: AppCacheBase,
    mode: Literal["authn", "authz"],
) -> list[SectionACL]:
    """
    Authenticate using an API key.

    ACLs are captured even for "authn" mode because it is quicker to cache them rather
    than calling authenticate_api_key() twice.

    Args:
        api_key: The API key from the request header.
        settings: The application settings.
        cache: An implementation of AppCacheBase, which can cache API credentials.
        mode: Determine whether to create an authentication or authorization log entry.

    Returns:
        list[SectionACL]: A list of ACLs associated with the API key.

    Raises:
        HTTPException: If the API key is not valid.
    """
    if not api_key:
        raise HTTPException(status_code=403, detail="Invalid API key (no permissions)")

    acls: list[SectionACL] = []
    auth_hash = fingerprint_hash(api_key.encode("utf-8"))

    if cached_auth_info := cache.fetch_app_cache(auth_hash):
        auth_info = AuthSuccess.model_validate_json(cached_auth_info)
        acls = [SectionACL.model_validate(acl) for acl in auth_info.acls]
        if mode == "authn":
            logger.info(f"API key authentication for '{auth_info.name}' (cached)")
        elif mode == "authz":
            logger.info(f"API key authorization for '{auth_info.name}' (cached)")
        return acls

    try:
        if auth_info := await authenticate_api_key(api_key, settings.auth):
            # TODO: get TTL from config
            acls = auth_info.acls
            serial_auth_info = json.dumps(to_jsonable_python(auth_info))
            cache.store_app_cache(auth_hash, serial_auth_info, 900)
            if mode == "authn":
                logger.info(f"API key authentication for '{auth_info.name}'")
            elif mode == "authz":
                logger.info(f"API key authorization for '{auth_info.name}'")
    except AuthenticationError as exc:
        raise HTTPException(status_code=403, detail=f"Invalid API key: {exc}")

    return acls


async def process_bearer_token(
    token: str,
    settings: AppSettings,
    cache: AppCacheBase,
    mode: Literal["authn", "authz"],
) -> list[SectionACL]:
    """
    Authenticate using a Bearer (JWT) token.

    ACLs are captured even for "authn" mode because it is quicker to cache them rather
    than calling authenticate_token() twice.

    Args:
        token: The OAuth2 token from the request header.
        settings: The application settings.
        cache: An implementation of AppCacheBase, which can cache API credentials.
        mode: Determine whether to create an authentication or authorization log entry.

    Returns:
        list[SectionACL]: A list of ACLs associated with the API key.

    Raises:
        HTTPException: If the token is not valid.
    """
    token = token.replace("Bearer ", "")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )
    if len(token.split(".")) != 3:
        raise HTTPException(status_code=403, detail="Invalid token")

    acls: list[SectionACL] = []
    auth_hash = fingerprint_hash(token.encode("utf-8"))

    if cached_auth_info := cache.fetch_app_cache(auth_hash):
        auth_info = AuthSuccess.model_validate_json(cached_auth_info)
        acls = [SectionACL.model_validate(item) for item in auth_info.acls]
        if mode == "authn":
            logger.info(f"JWT authentication for '{auth_info.name}' (cached)")
        elif mode == "authz":
            logger.info(f"JWT authorization for '{auth_info.name}' (cached)")
        return acls

    try:
        if auth_info := await authenticate_token(token, settings.auth):
            # TODO: get TTL from config
            acls = auth_info.acls
            serial_auth_info = json.dumps(to_jsonable_python(auth_info))
            cache.store_app_cache(auth_hash, serial_auth_info, 900)
            if mode == "authn":
                logger.info(f"JWT authentication for '{auth_info.name}'")
            elif mode == "authz":
                logger.info(f"JWT authorization for '{auth_info.name}'")
    except AuthenticationError as exc:
        raise HTTPException(status_code=403, detail=f"Invalid token: {exc}")

    if not acls:
        # NOTE: this should never reached because authenticate_token will raise an
        #   exception if acls is empty, but it exists to prevent unauthorized access
        #   in the event that authenticate_token is bugged
        raise HTTPException(status_code=403, detail="Invalid client (no permissions)")

    return acls
