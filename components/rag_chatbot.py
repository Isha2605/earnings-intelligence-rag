import json
import os
import re
import sys
from html import escape

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECTORSTORE_PATH = os.path.join(BASE_DIR, "vectorstore", "chroma_db")
KPI_PATH         = os.path.join(BASE_DIR, "data", "kpis.json")

COLORS = {
    "primary":  "#5B7CFA",
    "positive": "#85D478",
    "negative": "#F16672",
    "accent":   "#F5BE4F",
    "cyan":     "#43C6E8",
    "text":     "#F3F7FC",
    "subtext":  "#A7B4C7",
    "muted":    "#93A4BB",
    "card":     "#101826",
    "card2":    "#121D2E",
    "border":   "rgba(148,163,184,0.18)",
}

SUGGESTED_QUESTIONS = [
    "What drove Azure revenue growth in FY2024?",
    "How did operating margins change across the three years?",
    "What was the impact of the Activision Blizzard acquisition?",
    "Compare Microsoft Cloud revenue growth from FY2022 to FY2024",
]

SYSTEM_PROMPT = (
    "You are a concise financial analyst assistant for Microsoft's FY2022-FY2024 performance. "
    "Use the provided KPI snapshot as verified structured data and the retrieved 10-K excerpts as supporting context. "
    "Give a direct answer first. Do not lead with caveats unless the question truly cannot be answered from the KPI snapshot "
    "or excerpts. Never say the context lacks financial figures if the KPI snapshot contains relevant figures. "
    "Cite fiscal years for specific claims. Keep the response practical and analyst-like: direct answer, key numbers, "
    "brief interpretation, and only then caveats if needed."
)


@st.cache_data
def load_kpis():
    with open(KPI_PATH, "r") as f:
        return json.load(f)


# Heavy imports live here — only run on the first query, then cached by @st.cache_resource.
# This keeps page load time near-instant even after a Streamlit restart.
@st.cache_resource(show_spinner="Loading filing index…")
def load_index():
    from chromadb import PersistentClient
    from llama_index.core import Settings, VectorStoreIndex
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.embed_model = embed_model
    Settings.llm = None

    chroma_client = PersistentClient(path=VECTORSTORE_PATH)
    collection    = chroma_client.get_collection("msft_10k")
    vector_store  = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreIndex.from_vector_store(vector_store)


def _get_client():
    import anthropic

    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BASE_DIR, ".env"))
        api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        st.error(
            "ANTHROPIC_API_KEY not found. Add it to `.streamlit/secrets.toml` "
            "or a `.env` file in the project root."
        )
        st.stop()

    return anthropic.Anthropic(api_key=api_key)


def _retrieve(index, query, top_k=5):
    try:
        return index.as_retriever(similarity_top_k=top_k).retrieve(query)
    except Exception as exc:
        st.error(f"Retrieval error: {exc}")
        return []


def _confidence(nodes):
    if not nodes:
        return 0.0, "Low"

    scores    = [n.score for n in nodes if n.score is not None]
    raw_avg   = sum(scores) / len(scores) if scores else 0.5
    # BGE-small cosine similarities cluster around 0.45–0.65 even for good matches.
    # Square-root scaling maps that range to a more intuitive 0.67–0.80 band.
    avg_score = raw_avg ** 0.5

    years      = [n.metadata.get("fiscal_year") for n in nodes]
    counts: dict = {}
    for y in years:
        if y is not None:
            counts[y] = counts.get(y, 0) + 1
    max_count        = max(counts.values()) if counts else 1
    source_agreement = max_count / len(nodes)

    score = max(0.0, min(1.0, 0.75 * avg_score + 0.25 * source_agreement))
    label = "High" if score > 0.72 else ("Medium" if score > 0.55 else "Low")
    return score, label


def _build_context(nodes):
    parts = []
    for i, node in enumerate(nodes):
        year = node.metadata.get("fiscal_year", "Unknown")
        parts.append(f"[Excerpt {i + 1} - FY{year}]\n{node.text.strip()}")
    return "\n\n---\n\n".join(parts)


def _format_billions(value):
    return f"${value / 1000:.1f}B"


def _kpi_context():
    kpis = load_kpis()
    rows = []
    for year, data in sorted(kpis.items()):
        rows.append(
            f"FY{year}: revenue {_format_billions(data['total_revenue'])}; "
            f"operating income {_format_billions(data['operating_income'])}; "
            f"net income {_format_billions(data['net_income'])}; "
            f"diluted EPS ${data['diluted_eps']:.2f}; "
            f"gross margin {_format_billions(data['gross_margin'])}; "
            f"Microsoft Cloud revenue {_format_billions(data['microsoft_cloud_revenue'])}; "
            f"Intelligent Cloud revenue {_format_billions(data['intelligent_cloud_revenue'])}; "
            f"Productivity and Business Processes revenue {_format_billions(data['productivity_and_business_processes_revenue'])}; "
            f"More Personal Computing revenue {_format_billions(data['more_personal_computing_revenue'])}; "
            f"Azure and other cloud services revenue growth {data['azure_growth_yoy_pct']:.0f}%."
        )
    return "\n".join(rows)


def _badge(label, score):
    color = {"High": COLORS["positive"], "Medium": COLORS["accent"],
             "Low": COLORS["negative"]}.get(label, "#999")
    return (
        f"<span style='display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,0.04);"
        f"border:1px solid {COLORS['border']};color:#D8E3F3;padding:5px 10px;"
        f"border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.02em;'>"
        f"<span style='width:7px;height:7px;border-radius:999px;background:{color};box-shadow:0 0 0 3px {color}22;'></span>"
        f"Confidence: {label} ({score:.0%})</span>"
    )


def _inline_markdown(text):
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = text.replace("`", "")
    return text


def _message_html(content):
    lines = content.strip().splitlines()
    html_parts = []
    in_list = False

    for raw in lines:
        line = raw.strip()
        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        if line.startswith(("# ", "## ", "### ")):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            level = min(3, len(line) - len(line.lstrip("#")))
            text = line[level:].strip()
            html_parts.append(f"<h{level}>{_inline_markdown(text)}</h{level}>")
        elif line.startswith(("- ", "* ", "• ")):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline_markdown(line[2:].strip())}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{_inline_markdown(line)}</p>")

    if in_list:
        html_parts.append("</ul>")
    return "".join(html_parts)


def _render_chat_styles():
    st.markdown(
        f"""
        <style>
        .chat-shell {{
            background:
                radial-gradient(circle at 20% 0%, rgba(67,198,232,0.12), transparent 30%),
                linear-gradient(180deg, rgba(18,29,46,0.68), rgba(16,24,38,0.42));
            border: 1px solid {COLORS['border']};
            border-radius: 18px;
            padding: 18px;
            margin-top: 8px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 18px 40px rgba(0,0,0,0.18);
        }}
        .chat-row {{
            display: flex;
            align-items: flex-end;
            gap: 10px;
            margin: 12px 0;
        }}
        .chat-row.user {{
            justify-content: flex-end;
        }}
        .chat-row.assistant {{
            justify-content: flex-start;
        }}
        .chat-avatar {{
            width: 30px;
            height: 30px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 15px;
            flex: 0 0 auto;
            box-shadow: 0 8px 18px rgba(0,0,0,0.22);
        }}
        .chat-row.assistant .chat-avatar {{
            background: linear-gradient(135deg, {COLORS['cyan']}, {COLORS['primary']});
            color: white;
        }}
        .chat-row.user .chat-avatar {{
            background: linear-gradient(135deg, #28D17C, #1F9DFF);
            color: white;
        }}
        .chat-bubble {{
            max-width: 78%;
            padding: 13px 15px;
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.62;
            border: 1px solid rgba(148,163,184,0.14);
        }}
        .chat-row.assistant .chat-bubble {{
            color: #EAF2FF;
            background: linear-gradient(180deg, rgba(20,33,53,0.98), rgba(15,26,43,0.98));
            border-top-left-radius: 6px;
            box-shadow: 0 14px 32px rgba(0,0,0,0.20), 0 0 28px rgba(67,198,232,0.06);
        }}
        .chat-row.user .chat-bubble {{
            color: #FFFFFF;
            background: linear-gradient(135deg, rgba(91,124,250,0.96), rgba(67,198,232,0.72));
            border-top-right-radius: 6px;
            box-shadow: 0 14px 30px rgba(91,124,250,0.22);
        }}
        .chat-bubble p {{
            margin: 0 0 9px 0;
            color: inherit;
        }}
        .chat-bubble p:last-child {{
            margin-bottom: 0;
        }}
        .chat-bubble h1, .chat-bubble h2, .chat-bubble h3 {{
            margin: 0 0 10px 0;
            color: #FFFFFF;
            letter-spacing: 0;
            line-height: 1.18;
        }}
        .chat-bubble h1 {{ font-size: 22px; }}
        .chat-bubble h2 {{ font-size: 19px; }}
        .chat-bubble h3 {{ font-size: 16px; }}
        .chat-bubble ul {{
            margin: 6px 0 0 18px;
            padding: 0;
        }}
        .chat-bubble li {{
            margin: 5px 0;
            color: inherit;
        }}
        .chat-meta {{
            margin: 4px 0 14px 42px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            color: {COLORS['subtext']};
            font-size: 12px;
        }}
        .chat-empty {{
            border: 1px dashed rgba(67,198,232,0.25);
            background: rgba(67,198,232,0.045);
            border-radius: 16px;
            padding: 18px;
            color: {COLORS['subtext']};
            font-size: 13px;
            margin-top: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _chat_bubble(role, content):
    avatar = "⌁" if role == "assistant" else "↗"
    bubble = _message_html(content)
    return (
        f"<div class='chat-row {role}'>"
        f"{'' if role == 'user' else f'<div class=\"chat-avatar\">{avatar}</div>'}"
        f"<div class='chat-bubble'>{bubble}</div>"
        f"{f'<div class=\"chat-avatar\">{avatar}</div>' if role == 'user' else ''}"
        f"</div>"
    )


def _render_intro():
    st.markdown(
        f"""
        <div style="border:1px solid {COLORS['border']};border-radius:18px;padding:22px 24px;margin:2px 0 18px 0;
                    background:
                        radial-gradient(circle at 85% 10%, rgba(67,198,232,0.18), transparent 30%),
                        linear-gradient(180deg,{COLORS['card2']},{COLORS['card']});
                    box-shadow:0 18px 42px rgba(0,0,0,.20);">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:18px;">
            <div>
              <div style="font-size:12px;font-weight:850;letter-spacing:.12em;text-transform:uppercase;color:{COLORS['cyan']};margin-bottom:8px;">
                Filing chat
              </div>
              <div style="font-size:28px;font-weight:850;line-height:1.15;color:{COLORS['text']};letter-spacing:0;margin-bottom:8px;">
                Ask the filings like a conversation
              </div>
              <div style="font-size:14px;line-height:1.65;color:{COLORS['subtext']};max-width:760px;">
                Grounded answers from FY2022-FY2024 10-Ks, with confidence and source passages when available.
              </div>
            </div>
            <div style="width:58px;height:58px;border-radius:20px;display:flex;align-items:center;justify-content:center;
                        background:linear-gradient(135deg,{COLORS['primary']},{COLORS['cyan']});
                        box-shadow:0 0 28px rgba(67,198,232,0.28);font-size:28px;">💬</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_prompt_label():
    st.markdown(
        f"<div style='font-size:12px;color:{COLORS['muted']};font-weight:850;"
        f"letter-spacing:0.12em;text-transform:uppercase;margin:2px 0 8px 0;'>Suggested prompts</div>",
        unsafe_allow_html=True,
    )


def _render_message(msg):
    st.markdown(_chat_bubble(msg["role"], msg["content"]), unsafe_allow_html=True)
    if msg["role"] == "assistant" and "confidence" in msg:
        sources = msg.get("sources", [])
        cited = sorted({str(s["year"]) for s in sources})
        source_text = f"Sources: {', '.join('FY' + y for y in cited)}" if cited else ""
        st.markdown(
            f"<div class='chat-meta'>{_badge(msg['confidence_label'], msg['confidence'])}"
            f"<span>{source_text}</span></div>",
            unsafe_allow_html=True,
        )
        if sources:
            with st.expander("View source passages"):
                for s in sources:
                    st.markdown(f"**FY{s['year']}** (relevance: {max(0.0, min(1.0, s['score'])):.0%})")
                    st.markdown(f"> {s['text'][:400]}{'…' if len(s['text']) > 400 else ''}")
                    st.divider()


def render():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    _, main, _ = st.columns([1.1, 2.4, 1.1])

    with main:
        _render_chat_styles()
        _render_intro()

        # Suggested questions
        _render_prompt_label()
        sq_cols    = st.columns(2)
        selected_q = None
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            if sq_cols[i % 2].button(q, key=f"sq_{i}", use_container_width=True):
                selected_q = q

        st.markdown("<div class='chat-shell'>", unsafe_allow_html=True)

        for msg in st.session_state.messages:
            _render_message(msg)

        if not st.session_state.messages:
            st.markdown(
                "<div class='chat-empty'>Start with one of the prompts above, or ask your own question about Microsoft's filings.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        user_input = st.chat_input("Ask about Microsoft's 10-K filings…")
        query = selected_q or user_input

        if not query:
            return

        # Load index and client only on first query — cached after that.
        index  = load_index()
        client = _get_client()

        st.session_state.messages.append({"role": "user", "content": query})
        st.markdown(_chat_bubble("user", query), unsafe_allow_html=True)

        with st.spinner("Searching filings…"):
            nodes = _retrieve(index, query)

        confidence, conf_label = _confidence(nodes)
        context                = _build_context(nodes) if nodes else "No highly relevant excerpts were retrieved for this query."
        kpi_context            = _kpi_context()

        placeholder   = st.empty()
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Verified KPI snapshot extracted from Microsoft filings:\n\n{kpi_context}"
                        f"\n\nRetrieved context excerpts from Microsoft 10-K filings:\n\n{context}"
                        f"\n\nAnalyst question: {query}"
                    ),
                }],
            ) as stream:
                for chunk in stream.text_stream:
                    full_response += chunk
                    placeholder.markdown(_chat_bubble("assistant", full_response + "▌"), unsafe_allow_html=True)
            placeholder.markdown(_chat_bubble("assistant", full_response), unsafe_allow_html=True)
        except Exception as exc:
            full_response = f"Error: {exc}"
            placeholder.markdown(_chat_bubble("assistant", full_response), unsafe_allow_html=True)

        sources = [
            {"year": n.metadata.get("fiscal_year", "?"),
             "score": n.score if n.score is not None else 0.0,
             "text": n.text}
            for n in nodes
        ]
        cited = sorted({str(s["year"]) for s in sources})
        source_line = f"Sources: {', '.join('FY' + y for y in cited)}" if cited else "Source: verified KPI snapshot"
        st.markdown(
            f"<div class='chat-meta'>{_badge(conf_label, confidence)}"
            f"<span>{source_line}</span></div>",
            unsafe_allow_html=True,
        )

        if sources:
            with st.expander("View source passages"):
                for s in sources:
                    st.markdown(f"**FY{s['year']}** (relevance: {max(0.0, min(1.0, s['score'])):.0%})")
                    st.markdown(f"> {s['text'][:400]}{'…' if len(s['text']) > 400 else ''}")
                    st.divider()

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "confidence": confidence,
            "confidence_label": conf_label,
            "sources": sources,
        })
