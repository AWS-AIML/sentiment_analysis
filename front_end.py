import gradio as gr
from sentiment_analysis import analyze_text

# Load external CSS file
with open("styles.css", "r") as f:
    custom_css = f.read()

with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:
    # === Title Section ===
    gr.Markdown("""
        # 🎙️ AWS AI/ML Text Analyzer
        Translate, convert to speech, transcribe, and analyze sentiment using AWS services.
    """)

    with gr.Row():
        text_input = gr.Textbox(label="Enter Text in English", placeholder="Type something...", lines=4)

    with gr.Row():
        btn = gr.Button("🚀 Process Text")

    with gr.Row():
        translated_text = gr.Textbox(label="🈯 Translated Text (Hindi)", elem_classes=["output-box"])
        sentiment = gr.Textbox(label="🧠 Detected Sentiment", elem_classes=["output-box"])

    with gr.Row():
        score = gr.Textbox(label="📊 Sentiment Score", elem_classes=["output-box"])
        audio_output = gr.Audio(label="🔊 Audio (Hindi)", type="filepath")

    btn.click(fn=analyze_text,
              inputs=text_input,
              outputs=[translated_text, sentiment, score, audio_output])
    
if __name__ == "__main__":
    demo.launch()
