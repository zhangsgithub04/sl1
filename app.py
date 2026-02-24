import os
import streamlit as st
import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

# Option A (recommended): use Streamlit secrets in production
# Put these in .streamlit/secrets.toml:
# REDIS_HOST="xxx.redis-cloud.com"
# REDIS_PORT=12345
# REDIS_PASSWORD="xxxx"
# REDIS_USERNAME="default"   # sometimes required
#
# Option B: environment variables
# export REDIS_HOST=...
# export REDIS_PORT=...
# export REDIS_PASSWORD=...
# export REDIS_USERNAME=default

def _get_cfg():
    # Prefer Streamlit secrets if available, else fall back to env vars
    if hasattr(st, "secrets") and "REDIS_HOST" in st.secrets:
        host = st.secrets["REDIS_HOST"]
        port = int(st.secrets.get("REDIS_PORT", 6379))
        password = st.secrets.get("REDIS_PASSWORD")
        username = st.secrets.get("REDIS_USERNAME")  # optional
    else:
        host = os.getenv("REDIS_HOST")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD")
        username = os.getenv("REDIS_USERNAME")  # optional
    return host, port, username, password

@st.cache_resource
def get_redis_client():
    host, port, username, password = _get_cfg()
    if not host:
        raise RuntimeError("Missing REDIS_HOST (set Streamlit secrets or env vars).")

    # Redis Cloud usually requires TLS
    # Healthier behavior: retries + timeouts
    retry = Retry(ExponentialBackoff(cap=2, base=0.1), retries=5)

    client = redis.Redis(
        host=host,
        port=port,
        username=username,     # include if your Redis Cloud instance uses ACL users
        password=password,
        ssl=True,              # Redis Cloud typically requires TLS
        decode_responses=True, # strings instead of bytes
        socket_timeout=5,
        socket_connect_timeout=5,
        retry=retry,
        retry_on_timeout=True,
        health_check_interval=30,
    )

    # Fail fast if credentials/network are wrong
    client.ping()
    return client

# ---- Streamlit usage example ----
st.title("Streamlit ↔ Redis Cloud")

try:
    r = get_redis_client()
    st.success("Connected to Redis Cloud ✅")
except Exception as e:
    st.error(f"Redis connection failed: {e}")
    st.stop()

key = st.text_input("Key", "demo:key")
val = st.text_input("Value", "hello redis cloud")

col1, col2 = st.columns(2)
with col1:
    if st.button("SET"):
        r.set(key, val)
        st.success("Saved.")
with col2:
    if st.button("GET"):
        st.write("Value:", r.get(key))
