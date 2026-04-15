"""
Bancolombia RAG — Streamlit frontend.

Layout:
  Sidebar  — list of past conversations + "Nueva conversación" button.
  Main     — chat history (st.chat_message) + st.chat_input at the bottom.
             Assistant messages include source URLs as clickable links.

State managed via st.session_state:
  chat_id   str | None   — active conversation identifier.
  messages  list[dict]   — displayed messages [{role, content, sources}].
"""

from datetime import datetime

import streamlit as st

from api_client import AgentClient, ChatClient

# Config
st.set_page_config(
    page_title="Asistente Bancolombia",
    page_icon="🏦",
    layout="centered",
)

agent = AgentClient()
chat_client = ChatClient()

# Session state defaults
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None          # None = nueva conversación
if "messages" not in st.session_state:
    st.session_state.messages = []           # [{role, content, sources}]
if "pending_load" not in st.session_state:
    st.session_state.pending_load = None     # chat_id a cargar desde sidebar


# Sidebar
def _load_chat(chat_id: str) -> None:
    """Callback: load a past conversation into session state."""
    st.session_state.chat_id = chat_id
    msgs = chat_client.get_messages(chat_id)
    st.session_state.messages = [
        {"role": m["role"], "content": m["content"], "sources": m.get("sources", [])}
        for m in msgs
    ]


def _new_chat() -> None:
    """Callback: clear state to start a fresh conversation."""
    st.session_state.chat_id = None
    st.session_state.messages = []


with st.sidebar:
    st.markdown("### 🏦 Bancolombia")
    st.markdown("---")
    st.button("➕ Nueva conversación", on_click=_new_chat, use_container_width=True)
    st.markdown("---")
    st.subheader("Conversaciones")

    chats = chat_client.list_chats()
    if not chats:
        st.caption("No hay conversaciones aún.")
    else:
        for c in chats:
            # Format label: date + message count
            try:
                dt = datetime.fromisoformat(c["started_at"].replace("Z", "+00:00"))
                label = f"{dt.strftime('%d/%m/%Y %H:%M')}  •  {c['message_count']} msgs"
            except Exception:
                label = c["chat_id"][:16]

            is_active = c["chat_id"] == st.session_state.chat_id
            st.button(
                label,
                key=f"chat_{c['chat_id']}",
                on_click=_load_chat,
                args=(c["chat_id"],),
                use_container_width=True,
                type="primary" if is_active else "secondary",
            )



st.title("Asistente Bancolombia 🏦")
st.caption("Consulta sobre productos y servicios de Bancolombia para personas naturales.")

# Render existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        sources = msg.get("sources") or []
        if msg["role"] == "assistant" and sources:
            with st.expander("Ver fuentes"):
                for url in sources:
                    st.markdown(f"- [{url}]({url})")


# Chat input
if prompt := st.chat_input("Escribe tu pregunta sobre Bancolombia…"):
    # 1 — Show user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "sources": []}
    )

    # 2 — Call agent and stream reply
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Consultando…_")

        try:
            result = agent.chat(prompt, st.session_state.chat_id)
            reply: str = result["reply"]
            sources: list[str] = result.get("sources") or []
            st.session_state.chat_id = result["chat_id"]

            placeholder.markdown(reply)
            if sources:
                with st.expander("Ver fuentes"):
                    for url in sources:
                        st.markdown(f"- [{url}]({url})")

        except Exception:
            reply = "Lo siento, ocurrió un error al procesar tu pregunta. Por favor intenta de nuevo."
            sources = []
            placeholder.warning(reply)

    # 3 — Persist in session state
    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "sources": sources}
    )