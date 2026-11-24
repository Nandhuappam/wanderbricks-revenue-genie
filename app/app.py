"""Revenue & Booking Analyst: a Databricks App (Streamlit) over a Genie space.

The app sends each user question to the Genie Conversation API and shows:
  * Genie's text answer
  * the result table
  * the generated SQL (for trust and verification)

Config (set in app.yaml):
  GENIE_SPACE_ID: injected from the app resource with key "genie-space"
"""

import os

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient

SPACE_ID = os.getenv("GENIE_SPACE_ID", "")

SAMPLE_QUESTIONS = [
    "What was total booking revenue last quarter?",
    "Which destinations had the most confirmed bookings?",
    "What's the average booking value by property type?",
    "Who are the top 10 hosts by total revenue?",
    "What share of bookings come from business users?",
]

st.set_page_config(page_title="Revenue & Booking Analyst", page_icon="📊", layout="wide")


@st.cache_resource
def get_client() -> WorkspaceClient:
    # Inside a Databricks App, credentials for the app's service principal are injected automatically.
    return WorkspaceClient()


def fetch_result(w: WorkspaceClient, conversation_id: str, message_id: str, attachment_id: str):
    """Return the query result of a Genie attachment as a DataFrame, or None."""
    try:
        resp = w.genie.get_message_attachment_query_result(
            SPACE_ID, conversation_id, message_id, attachment_id
        )
    except AttributeError:  # older databricks-sdk versions
        resp = w.genie.get_message_query_result_by_attachment(
            SPACE_ID, conversation_id, message_id, attachment_id
        )
    stmt = resp.statement_response
    if not stmt or not stmt.result or not stmt.result.data_array:
        return None
    cols = [c.name for c in stmt.manifest.schema.columns]
    return pd.DataFrame(stmt.result.data_array, columns=cols)


def ask_genie(question: str) -> dict:
    w = get_client()
    conv_id = st.session_state.get("conversation_id")
    if conv_id:
        msg = w.genie.create_message_and_wait(SPACE_ID, conv_id, question)
    else:
        msg = w.genie.start_conversation_and_wait(SPACE_ID, question)
        st.session_state.conversation_id = msg.conversation_id

    out = {"text": "", "sql": None, "df": None}
    for att in msg.attachments or []:
        if att.text and att.text.content:
            out["text"] += att.text.content
        if att.query:
            out["sql"] = att.query.query
            if att.query.description:
                out["text"] += ("\n\n" if out["text"] else "") + att.query.description
            out["df"] = fetch_result(w, msg.conversation_id, msg.id, att.attachment_id)
    return out


def render_answer(ans: dict):
    if ans.get("text"):
        st.markdown(ans["text"])
    if ans.get("df") is not None:
        st.dataframe(ans["df"], use_container_width=True, hide_index=True)
    if ans.get("sql"):
        with st.expander("Show SQL"):
            st.code(ans["sql"], language="sql")


# ---------------- UI ----------------
st.title("📊 Revenue & Booking Analyst")
st.caption("Ask plain-English questions about Wanderbricks bookings and revenue. "
           "Revenue counts confirmed bookings only.")

if not SPACE_ID:
    st.error("GENIE_SPACE_ID is not set. Add the Genie space as an app resource (key: genie-space).")
    st.stop()

with st.sidebar:
    st.subheader("Try asking")
    for q in SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            st.session_state.pending = q
    st.divider()
    if st.button("New conversation", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.session_state.setdefault("history", [])
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["q"])
    with st.chat_message("assistant"):
        render_answer(turn["a"])

question = st.chat_input("e.g. What was revenue by destination last month?") or st.session_state.pop("pending", None)
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Genie is thinking…"):
            try:
                answer = ask_genie(question)
            except Exception as e:  # show errors to the user instead of crashing the app
                answer = {"text": f"⚠️ Sorry, something went wrong: `{e}`", "sql": None, "df": None}
        render_answer(answer)
    st.session_state.history.append({"q": question, "a": answer})
