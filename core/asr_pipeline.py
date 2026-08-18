import os
import types

if not hasattr(types, "UnionType"):
    try:
        types.UnionType = type("UnionType", (), {})
    except Exception:
        pass

try:
    from transformers import pipeline
except Exception as e:
    pipeline = None
    print(f"[ASRPipeline Warning] Transformers pipeline import notice: {e}")

try:
    import gradio as gr
except Exception as e:
    gr = None
    print(f"[ASRPipeline Warning] Gradio import notice: {e}")


class HuggingFaceASRPipeline:
    """
    Automatic Speech Recognition (ASR) Pipeline using Hugging Face Transformers.
    Integrates 'from transformers import pipeline' with optional Gradio web demo support.
    """
    def __init__(self, model_name="openai/whisper-tiny"):
        self.model_name = model_name
        self.asr = None
        if pipeline is not None:
            try:
                print(f"[ASRPipeline] Initializing Hugging Face ASR pipeline with model '{model_name}'...")
                self.asr = pipeline("automatic-speech-recognition", model=model_name)
            except Exception as ex:
                print(f"[ASRPipeline Error] Failed to load local ASR pipeline: {ex}")

    def transcribe(self, audio_file_path: str) -> str:
        """Transcribes audio file using Hugging Face Transformers ASR pipeline."""
        if self.asr:
            try:
                result = self.asr(audio_file_path)
                if isinstance(result, dict):
                    return result.get("text", "").strip()
                elif isinstance(result, list) and len(result) > 0:
                    return result[0].get("text", "").strip()
            except Exception as e:
                print(f"[ASRPipeline Exception] Transcription failed: {e}")
        return ""

    def launch_gradio_demo(self):
        """Launches optional Gradio web interface for Hugging Face ASR."""
        if gr is None:
            print("[ASRPipeline Error] Gradio is not available.")
            return

        def transcribe_audio(audio_path):
            return self.transcribe(audio_path)

        demo = gr.Interface(
            fn=transcribe_audio,
            inputs=gr.Audio(type="filepath"),
            outputs="text",
            title="Sahayak HuggingFace ASR Demo",
            description="Automatic Speech Recognition using HuggingFace Transformers Pipeline"
        )
        demo.launch(share=False)
