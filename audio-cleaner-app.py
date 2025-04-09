import os
import streamlit as st
from pydub import AudioSegment, silence
import librosa
import soundfile as sf
import noisereduce as nr
import tempfile

# === Funciones de procesamiento ===
def convert_mp3_to_wav(input_path, output_path):
    audio = AudioSegment.from_mp3(input_path)
    audio.export(output_path, format="wav")

def normalize_audio(audio):
    return audio.apply_gain(-audio.dBFS)

def remove_silence(audio, min_silence_len=1000, silence_thresh=-40):
    chunks = silence.split_on_silence(audio, min_silence_len, silence_thresh)
    return sum(chunks)

def reduce_noise(input_wav, output_wav, noise_sample_duration=1):
    audio, sr = librosa.load(input_wav, sr=None)
    noise_sample = audio[0:sr * noise_sample_duration]
    reduced = nr.reduce_noise(y=audio, y_noise=noise_sample, sr=sr)
    sf.write(output_wav, reduced, sr)

def clean_audio(mp3_file, output_dir, min_silence_len, silence_thresh, noise_sample_duration):
    base_name = os.path.splitext(mp3_file.name)[0]
    temp_mp3_path = os.path.join(output_dir, f"{base_name}.mp3")
    temp_wav = os.path.join(output_dir, f"{base_name}_temp.wav")
    intermediate = os.path.join(output_dir, f"{base_name}_intermediate.wav")
    final_output = os.path.join(output_dir, f"{base_name}_limpio.wav")

    with open(temp_mp3_path, "wb") as f:
        f.write(mp3_file.getbuffer())

    convert_mp3_to_wav(temp_mp3_path, temp_wav)
    audio = AudioSegment.from_wav(temp_wav)
    normalized = normalize_audio(audio)
    no_silence = remove_silence(normalized, min_silence_len, silence_thresh)
    no_silence.export(intermediate, format="wav")
    reduce_noise(intermediate, final_output, noise_sample_duration)

    return temp_mp3_path, final_output

# === Interfaz Streamlit ===
st.set_page_config(page_title="Limpieza de Audios", layout="centered")
st.title("Limpieza de Audios en Lote con Ajustes Personalizados")
st.write("Sube tus archivos MP3, ajusta los parámetros y obtén versiones limpias. Puedes escuchar el antes y después.")

# === Parámetros ajustables ===
st.sidebar.header("Ajustes de limpieza")

min_silence_len = st.sidebar.slider(
    "Duración mínima del silencio (ms)", min_value=300, max_value=3000, value=1000, step=100
)

silence_thresh = st.sidebar.slider(
    "Umbral de silencio (dBFS)", min_value=-70, max_value=-10, value=-40, step=1
)

noise_sample_duration = st.sidebar.slider(
    "Duración de muestra de ruido (seg)", min_value=1, max_value=5, value=1, step=1
)

uploaded_files = st.file_uploader("Sube tus archivos MP3", type="mp3", accept_multiple_files=True)

if uploaded_files:
    with tempfile.TemporaryDirectory() as tmp_dir:
        for file in uploaded_files:
            with st.spinner(f"Procesando {file.name}..."):
                original_path, cleaned_path = clean_audio(
                    file, tmp_dir, min_silence_len, silence_thresh, noise_sample_duration
                )

            st.subheader(f"Resultado para: {file.name}")

            st.write("**Audio Original**")
            st.audio(original_path)

            st.write("**Audio Limpio**")
            st.audio(cleaned_path)

            with open(cleaned_path, "rb") as f:
                st.download_button(
                    f"Descargar {os.path.basename(cleaned_path)}",
                    f,
                    file_name=os.path.basename(cleaned_path),
                    mime="audio/wav"
                )
