import os
import streamlit as st
from pydub import AudioSegment, silence
import librosa
import soundfile as sf
import noisereduce as nr
import tempfile
import math
import zipfile
import io


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

def clean_audio(mp3_file, output_dir, min_silence_len, silence_thresh, noise_sample_duration, formato = 'mp3'):
    base_name = os.path.splitext(mp3_file.name)[0]
    temp_mp3_path = os.path.join(output_dir, f"{base_name}.mp3")
    temp_wav = os.path.join(output_dir, f"{base_name}_temp.wav")
    intermediate = os.path.join(output_dir, f"{base_name}_intermediate.wav")
    # final_output = os.path.join(output_dir, f"{base_name}_limpio.wav")

    with open(temp_mp3_path, "wb") as f:
        f.write(mp3_file.getbuffer())

    convert_mp3_to_wav(temp_mp3_path, temp_wav)
    audio = AudioSegment.from_wav(temp_wav)
    normalized = normalize_audio(audio)
    no_silence = remove_silence(normalized, min_silence_len, silence_thresh)
    no_silence.export(intermediate, format="wav")
    # reduce_noise(intermediate, final_output, noise_sample_duration)

    # if formato != "wav":
    #     convertido_path = final_output.replace(".wav", f".{formato}")
    #     AudioSegment.from_wav(final_output).export(convertido_path, format=formato)
    #     final_output = convertido_path

    # return temp_mp3_path, final_output
    return temp_mp3_path

def dividir_audio_en_segmentos(input_path, duracion_segmento_min=5, output_dir="segmentos", formato="wav"):
    audio = AudioSegment.from_file(input_path)
    duracion_segmento_ms = duracion_segmento_min * 60 * 1000
    total_duracion_ms = len(audio)
    total_segmentos = math.ceil(total_duracion_ms / duracion_segmento_ms)

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    archivos_generados = []

    for i in range(total_segmentos):
        inicio = i * duracion_segmento_ms
        fin = min((i + 1) * duracion_segmento_ms, total_duracion_ms)
        segmento = audio[inicio:fin]

        nombre_segmento = f"{base_name}_parte_{i+1}_{duracion_segmento_min}min.{formato}"
        path_segmento = os.path.join(output_dir, nombre_segmento)
        segmento.export(path_segmento, format=formato)
        archivos_generados.append(path_segmento)
    return archivos_generados

def crear_zip_segmentos(lista_segmentos):
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "w") as zipf:
        for path in lista_segmentos:
            arcname = os.path.basename(path)
            zipf.write(path, arcname)
    buffer_zip.seek(0)
    return buffer_zip


# === Interfaz Streamlit ===
st.set_page_config(page_title="Limpieza de Audios", layout="centered")
st.title("Limpieza de Audios en Lote con Ajustes Personalizados")
st.write("Sube tus archivos MP3, ajusta los parámetros, escucha el antes y después, y divide en segmentos si lo deseas.")

# === Parámetros de limpieza ===
st.sidebar.header("Ajustes de limpieza")
min_silence_len = st.sidebar.slider("Duración mínima del silencio (ms)", 300, 3000, 1000, 100)
silence_thresh = st.sidebar.slider("Umbral de silencio (dBFS)", -70, -10, -40, 1)
noise_sample_duration = st.sidebar.slider("Duración muestra de ruido (seg)", 1, 5, 1, 1)

# === División opcional ===
dividir = st.sidebar.checkbox("Dividir audio limpio en partes", value=True)
duracion_segmento = 5  # valor por defecto

if dividir:
    duracion_segmento = st.sidebar.slider(
        "Duración de cada parte (minutos)", min_value=1, max_value=10, value=5, step=1
    )

# === Selección de formato de salida ===
formato_salida = st.sidebar.selectbox(
    "Formato de salida", options=["wav", "mp3", "flac"], index=0
)

uploaded_files = st.file_uploader("Sube tus archivos MP3", type="mp3", accept_multiple_files=True)

if uploaded_files:
    with tempfile.TemporaryDirectory() as tmp_dir:
        for file in uploaded_files:
            with st.spinner(f"Procesando {file.name}..."):
                # original_path, cleaned_path = clean_audio(
                #     file, tmp_dir, min_silence_len, silence_thresh, noise_sample_duration, formato_salida
                # )
                original_path = clean_audio(
                    file, tmp_dir, min_silence_len, silence_thresh, noise_sample_duration, formato_salida
                )

            st.subheader(f"Resultado para: {file.name}")

            st.write("**Audio Original**")
            st.audio(original_path)

            # st.write("**Audio Limpio**")
            # st.audio(cleaned_path)

            # with open(cleaned_path, "rb") as f:
            #     st.download_button(
            #         f"Descargar audio limpio ({os.path.basename(cleaned_path)})",
            #         f,
            #         file_name=os.path.basename(cleaned_path),
            #         mime="audio/wav"
            #     )

            # === División en segmentos de 5 minutos ===
            if dividir:
                st.write("**Segmentos de 5 minutos:**")
                # segmentos = dividir_audio_en_segmentos(cleaned_path, duracion_segmento, tmp_dir, formato=formato_salida)
                segmentos = dividir_audio_en_segmentos(original_path, duracion_segmento, tmp_dir, formato=formato_salida)
                for i, segmento_path in enumerate(segmentos):
                    st.audio(segmento_path)
                    with open(segmento_path, "rb") as f:
                        st.download_button(
                            f"Descargar parte {i+1}",
                            f,
                            file_name=os.path.basename(segmento_path),
                            mime="audio/wav"
                        )

                # === Descargar ZIP con todos los segmentos ===
                zip_buffer = crear_zip_segmentos(segmentos)
                st.download_button(
                    label="Descargar todos los segmentos en ZIP",
                    data=zip_buffer,
                    file_name=f"{os.path.splitext(os.path.basename(original_path))[0]}_segmentos.zip",
                    mime="application/zip"
                )

