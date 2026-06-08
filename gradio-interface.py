import gradio as gr
from query import ask

def handle_query(question):
    if not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    # Deduplicate sources while preserving order
    seen = set()
    unique_sources = []
    for s in result["sources"]:
        if s not in seen:
            seen.add(s)
            unique_sources.append(s)
    sources = "\n".join(f"• {s}" for s in unique_sources)
    return result["answer"], sources

with gr.Blocks(title="The Unofficial Guide") as demo:
    gr.Markdown("# The Unofficial Guide\nAsk anything about dorms at Ivy League universities.")
    inp = gr.Textbox(label="Your question", placeholder="e.g. Which freshman dorms have AC at Cornell?")
    btn = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

demo.launch()