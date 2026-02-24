import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Petstore API Demo", page_icon="🐶")

st.title("🐶 Swagger Petstore API Demo")

BASE_URL = "https://petstore.swagger.io/v2"

# Sidebar controls
with st.sidebar:
    st.header("Search Options")
    status = st.selectbox(
        "Pet Status",
        ["available", "pending", "sold"]
    )
    limit = st.slider("Number of results", 1, 20, 5)

# Button to trigger API call
if st.button("Fetch Pets"):
    url = f"{BASE_URL}/pet/findByStatus"
    params = {"status": status}

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            pets = response.json()

            if not pets:
                st.warning("No pets found.")
            else:
                # Limit results
                pets = pets[:limit]

                # Convert to dataframe
                data = []
                for pet in pets:
                    data.append({
                        "ID": pet.get("id"),
                        "Name": pet.get("name"),
                        "Status": pet.get("status"),
                        "Category": pet.get("category", {}).get("name"),
                        "Tags": ", ".join(
                            tag["name"] for tag in pet.get("tags", [])
                        )
                    })

                df = pd.DataFrame(data)

                st.success(f"Found {len(df)} pets")
                st.dataframe(df, use_container_width=True)

        else:
            st.error(f"Error: {response.status_code}")

    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
