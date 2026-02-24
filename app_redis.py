import streamlit as st
import redis

st.title("Streamlit ↔ Redis Cloud")

@st.cache_resource
def get_redis():
    host = st.secrets["REDIS_HOST"]
    port = int(st.secrets["REDIS_PORT"])
    password = st.secrets["REDIS_PASSWORD"]
    username = st.secrets.get("REDIS_USERNAME", "default")

    # NON-TLS connection (important for this port)
    r = redis.Redis(
        host=host,
        port=port,
        username=username,
        password=password,
        ssl=False,              # ✅ IMPORTANT
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    r.ping()  # test connection
    return r

try:
    r = get_redis()
    st.success("Connected to Redis Cloud ✅")
except Exception as e:
    st.error(f"Redis connection failed: {e}")
    st.stop()

# ---- Demo ----
key = st.text_input("Key", "demo:key")
value = st.text_input("Value", "Hello Redis")

col1, col2 = st.columns(2)

with col1:
    if st.button("SET"):
        r.set(key, value)
        st.success("Saved!")

with col2:
    if st.button("GET"):
        st.write("Stored value:", r.get(key))
