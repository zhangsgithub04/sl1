import json
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://petstore.swagger.io/v2"


# ---------------------------
# Helpers
# ---------------------------
def api_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Tuple[int, Any, str]:
    """
    Returns: (status_code, parsed_json_or_text, raw_text)
    """
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            data=data,
            timeout=timeout,
        )
        raw = resp.text
        try:
            return resp.status_code, resp.json(), raw
        except Exception:
            return resp.status_code, raw, raw
    except requests.RequestException as e:
        return 0, {"error": str(e)}, str(e)


def show_response(status_code: int, payload: Any, raw_text: str):
    if status_code == 0:
        st.error("Request failed (network/connection error).")
        st.code(raw_text)
        return

    if 200 <= status_code < 300:
        st.success(f"Success ({status_code})")
    else:
        st.error(f"Error ({status_code})")

    # Prefer pretty JSON if possible
    if isinstance(payload, (dict, list)):
        st.json(payload)
    else:
        st.code(str(payload))


def pet_to_row(pet: Dict[str, Any]) -> Dict[str, Any]:
    tags = pet.get("tags") or []
    tag_names = []
    for t in tags:
        if isinstance(t, dict) and t.get("name") is not None:
            tag_names.append(str(t["name"]))
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "status": pet.get("status"),
        "category": (pet.get("category") or {}).get("name"),
        "tags": ", ".join(tag_names),
        "photoUrls": ", ".join(pet.get("photoUrls") or []),
    }


def ensure_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


# Cache ONLY search results (safe-ish); CRUD should be live.
@st.cache_data(ttl=30, show_spinner=False)
def cached_find_by_status(status: str):
    code, payload, raw = api_request("GET", "/pet/findByStatus", params={"status": status})
    return code, payload, raw


@st.cache_data(ttl=30, show_spinner=False)
def cached_find_by_tags(tags: List[str]):
    # Petstore expects repeated tags= param; requests can do {"tags": [...]}.
    code, payload, raw = api_request("GET", "/pet/findByTags", params={"tags": tags})
    return code, payload, raw


# ---------------------------
# App config
# ---------------------------
st.set_page_config(page_title="Petstore SCRUD", page_icon="🐾", layout="wide")
st.title("🐾 Petstore SCRUD (Search • Create • Read • Update • Delete)")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Go to",
        ["Search", "Create", "Read", "Update", "Delete"],
        index=0,
    )
    st.divider()
    st.caption(f"API: {BASE_URL}")

# A place to keep last-used pet (handy for demo flows)
if "last_pet" not in st.session_state:
    st.session_state.last_pet = None


# ---------------------------
# SEARCH
# ---------------------------
if page == "Search":
    st.subheader("S — Search")

    tab1, tab2 = st.tabs(["Find by status", "Find by tags"])

    with tab1:
        status = st.selectbox("Status", ["available", "pending", "sold"], index=0)
        limit = st.slider("Limit results", 1, 50, 10)

        colA, colB = st.columns([1, 2])
        with colA:
            do_fetch = st.button("Search by status", use_container_width=True)

        if do_fetch:
            with st.spinner("Calling /pet/findByStatus ..."):
                code, payload, raw = cached_find_by_status(status)

            show_response(code, payload, raw)

            if isinstance(payload, list) and payload:
                df = pd.DataFrame([pet_to_row(p) for p in payload[:limit]])
                st.dataframe(df, use_container_width=True)

                # store last pet
                st.session_state.last_pet = payload[0]
                st.info(f"Saved the first result to session as last_pet (id={payload[0].get('id')}).")

    with tab2:
        tags_text = st.text_input("Tags (comma-separated)", value="dog,cute")
        limit2 = st.slider("Limit results ", 1, 50, 10, key="limit_tags")
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]

        colA, colB = st.columns([1, 2])
        with colA:
            do_fetch2 = st.button("Search by tags", use_container_width=True)

        if do_fetch2:
            if not tags:
                st.warning("Enter at least one tag.")
            else:
                with st.spinner("Calling /pet/findByTags ..."):
                    code, payload, raw = cached_find_by_tags(tags)

                show_response(code, payload, raw)

                if isinstance(payload, list) and payload:
                    df = pd.DataFrame([pet_to_row(p) for p in payload[:limit2]])
                    st.dataframe(df, use_container_width=True)
                    st.session_state.last_pet = payload[0]
                    st.info(f"Saved the first result to session as last_pet (id={payload[0].get('id')}).")


# ---------------------------
# CREATE
# ---------------------------
elif page == "Create":
    st.subheader("C — Create (POST /pet)")

    with st.form("create_pet_form"):
        st.caption("Creates a new pet. Tip: use a unique numeric ID to avoid collisions.")
        col1, col2, col3 = st.columns(3)

        with col1:
            pet_id = st.text_input("Pet ID (number)", value="")
            name = st.text_input("Name", value="Fido")
        with col2:
            status = st.selectbox("Status", ["available", "pending", "sold"], index=0)
            category_name = st.text_input("Category name", value="Dogs")
        with col3:
            tags_text = st.text_input("Tags (comma-separated)", value="friendly")
            photo_urls_text = st.text_input("Photo URLs (comma-separated)", value="")

        submit = st.form_submit_button("Create pet", use_container_width=True)

    if submit:
        pid = ensure_int(pet_id)
        if pid is None:
            st.warning("Please provide a numeric Pet ID.")
        elif not name.strip():
            st.warning("Name is required.")
        else:
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]
            photo_urls = [u.strip() for u in photo_urls_text.split(",") if u.strip()]

            payload = {
                "id": pid,
                "name": name.strip(),
                "status": status,
                "category": {"id": 1, "name": category_name.strip() or "Unknown"},
                "tags": [{"id": i + 1, "name": t} for i, t in enumerate(tags)],
                "photoUrls": photo_urls,
            }

            with st.spinner("Calling POST /pet ..."):
                code, out, raw = api_request("POST", "/pet", json_body=payload)

            show_response(code, out, raw)
            if 200 <= code < 300 and isinstance(out, dict):
                st.session_state.last_pet = out
                st.info(f"Saved created pet to session as last_pet (id={out.get('id')}).")


# ---------------------------
# READ
# ---------------------------
elif page == "Read":
    st.subheader("R — Read (GET /pet/{petId})")

    default_id = ""
    if isinstance(st.session_state.last_pet, dict) and st.session_state.last_pet.get("id") is not None:
        default_id = str(st.session_state.last_pet.get("id"))

    col1, col2 = st.columns([2, 1])
    with col1:
        pet_id = st.text_input("Pet ID", value=default_id, placeholder="e.g. 123456")
    with col2:
        do_read = st.button("Read pet", use_container_width=True)

    if do_read:
        pid = ensure_int(pet_id)
        if pid is None:
            st.warning("Please enter a numeric Pet ID.")
        else:
            with st.spinner(f"Calling GET /pet/{pid} ..."):
                code, out, raw = api_request("GET", f"/pet/{pid}")

            show_response(code, out, raw)
            if 200 <= code < 300 and isinstance(out, dict):
                st.session_state.last_pet = out
                st.info("Saved result to session as last_pet.")


# ---------------------------
# UPDATE
# ---------------------------
elif page == "Update":
    st.subheader("U — Update")
    st.caption("Two options: full replace (PUT /pet) or partial update (POST /pet/{petId}).")

    tab_put, tab_post = st.tabs(["Full update (PUT /pet)", "Partial update (POST /pet/{petId})"])

    # Full PUT
    with tab_put:
        last = st.session_state.last_pet if isinstance(st.session_state.last_pet, dict) else {}
        default_json = json.dumps(
            {
                "id": last.get("id", 123456),
                "name": last.get("name", "Fido (updated)"),
                "status": last.get("status", "pending"),
                "category": last.get("category", {"id": 1, "name": "Dogs"}) or {"id": 1, "name": "Dogs"},
                "tags": last.get("tags", [{"id": 1, "name": "friendly"}]) or [{"id": 1, "name": "friendly"}],
                "photoUrls": last.get("photoUrls", []) or [],
            },
            indent=2,
        )

        pet_json_text = st.text_area("Pet JSON", value=default_json, height=260)

        do_put = st.button("Update via PUT /pet", use_container_width=True, key="do_put")
        if do_put:
            try:
                payload = json.loads(pet_json_text)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
                payload = None

            if payload is not None:
                with st.spinner("Calling PUT /pet ..."):
                    code, out, raw = api_request("PUT", "/pet", json_body=payload)
                show_response(code, out, raw)
                if 200 <= code < 300 and isinstance(out, dict):
                    st.session_state.last_pet = out
                    st.info("Saved updated pet to session as last_pet.")

    # Partial POST (form)
    with tab_post:
        default_id = ""
        if isinstance(last, dict) and last.get("id") is not None:
            default_id = str(last.get("id"))

        col1, col2, col3 = st.columns(3)
        with col1:
            pet_id = st.text_input("Pet ID", value=default_id, key="partial_pet_id")
        with col2:
            new_name = st.text_input("New name (optional)", value="", key="partial_name")
        with col3:
            new_status = st.selectbox("New status (optional)", ["", "available", "pending", "sold"], index=0)

        do_post = st.button("Update via POST /pet/{petId}", use_container_width=True, key="do_post")
        if do_post:
            pid = ensure_int(pet_id)
            if pid is None:
                st.warning("Please enter a numeric Pet ID.")
            else:
                form_data = {}
                if new_name.strip():
                    form_data["name"] = new_name.strip()
                if new_status.strip():
                    form_data["status"] = new_status.strip()

                if not form_data:
                    st.warning("Provide at least a new name or new status.")
                else:
                    with st.spinner(f"Calling POST /pet/{pid} ..."):
                        code, out, raw = api_request("POST", f"/pet/{pid}", data=form_data)

                    show_response(code, out, raw)
                    st.info("Tip: This endpoint may return a simple message. Use the Read page to verify updates.")


# ---------------------------
# DELETE
# ---------------------------
elif page == "Delete":
    st.subheader("D — Delete (DELETE /pet/{petId})")
    st.warning("This will delete a pet by ID on the demo server (best effort).")

    default_id = ""
    last = st.session_state.last_pet if isinstance(st.session_state.last_pet, dict) else {}
    if last.get("id") is not None:
        default_id = str(last.get("id"))

    col1, col2 = st.columns([2, 1])
    with col1:
        pet_id = st.text_input("Pet ID", value=default_id, placeholder="e.g. 123456", key="delete_id")
        api_key = st.text_input("api_key header (optional)", value="", placeholder="some-key", key="delete_key")
    with col2:
        confirm = st.checkbox("I understand", value=False)

    do_delete = st.button("Delete pet", use_container_width=True, disabled=not confirm)

    if do_delete:
        pid = ensure_int(pet_id)
        if pid is None:
            st.warning("Please enter a numeric Pet ID.")
        else:
            headers = {}
            if api_key.strip():
                headers["api_key"] = api_key.strip()

            # Use requests directly here to include optional header cleanly
            url = f"{BASE_URL}/pet/{pid}"
            try:
                with st.spinner(f"Calling DELETE /pet/{pid} ..."):
                    resp = requests.delete(url, headers=headers, timeout=15)
                raw = resp.text
                try:
                    payload = resp.json()
                except Exception:
                    payload = raw
                show_response(resp.status_code, payload, raw)

                # Clear last_pet if it matches
                if isinstance(last, dict) and last.get("id") == pid:
                    st.session_state.last_pet = None
            except requests.RequestException as e:
                st.error(f"Request failed: {e}")
