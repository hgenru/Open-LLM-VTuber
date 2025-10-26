import base64
import random
from pydub import AudioSegment
from pydub.utils import make_chunks
from ..agent.output_types import Actions
from ..agent.output_types import DisplayText


def _get_volume_by_chunks(audio: AudioSegment, chunk_length_ms: int) -> list:
    """
    Calculate the normalized volume (RMS) for each chunk of the audio.

    Parameters:
        audio (AudioSegment): The audio segment to process.
        chunk_length_ms (int): The length of each audio chunk in milliseconds.

    Returns:
        list: Normalized volumes for each chunk.
    """
    chunks = make_chunks(audio, chunk_length_ms)
    volumes = [chunk.rms for chunk in chunks]
    max_volume = max(volumes)
    if max_volume == 0:
        raise ValueError("Audio is empty or all zero.")
    return [volume / max_volume for volume in volumes]


def _apply_dynamic_pitch(audio: AudioSegment, chunk_length_ms: int, base_pitch: float = 1.0, variation: float = 0.1) -> AudioSegment:
    """
    Apply dynamic pitch shift to audio chunks (GLaDOS-style).

    Parameters:
        audio (AudioSegment): The audio to process
        chunk_length_ms (int): Length of each chunk in ms
        base_pitch (float): Base pitch multiplier (default 1.0)
        variation (float): Random variation range (default 0.1 = ±10%)

    Returns:
        AudioSegment: Audio with dynamic pitch applied
    """
    chunks = make_chunks(audio, chunk_length_ms)
    processed_chunks = []

    for chunk in chunks:
        # Random pitch shift for this chunk
        pitch_shift = base_pitch + random.uniform(-variation, variation)

        # Apply pitch shift
        new_sample_rate = int(chunk.frame_rate * pitch_shift)
        shifted = chunk._spawn(chunk.raw_data, overrides={'frame_rate': new_sample_rate})
        shifted = shifted.set_frame_rate(chunk.frame_rate)

        processed_chunks.append(shifted)

    # Combine all chunks
    result = processed_chunks[0]
    for chunk in processed_chunks[1:]:
        result += chunk

    return result


def prepare_audio_payload(
    audio_path: str | None,
    chunk_length_ms: int = 20,
    display_text: DisplayText = None,
    actions: Actions = None,
    forwarded: bool = False,
) -> dict[str, any]:
    """
    Prepares the audio payload for sending to a broadcast endpoint.
    If audio_path is None, returns a payload with audio=None for silent display.

    Parameters:
        audio_path (str | None): The path to the audio file to be processed, or None for silent display
        chunk_length_ms (int): The length of each audio chunk in milliseconds
        display_text (DisplayText, optional): Text to be displayed with the audio
        actions (Actions, optional): Actions associated with the audio

    Returns:
        dict: The audio payload to be sent
    """
    if isinstance(display_text, DisplayText):
        display_text = display_text.to_dict()

    if not audio_path:
        # Return payload for silent display
        return {
            "type": "audio",
            "audio": None,
            "volumes": [],
            "slice_length": chunk_length_ms,
            "display_text": display_text,
            "actions": actions.to_dict() if actions else None,
            "forwarded": forwarded,
        }

    try:
        audio = AudioSegment.from_file(audio_path)
        audio = _apply_dynamic_pitch(audio, chunk_length_ms=5, base_pitch=1.0, variation=0.05)
        audio = _apply_dynamic_pitch(audio, chunk_length_ms=100, base_pitch=1.0, variation=0.07)
        audio_bytes = audio.export(format="wav").read()
    except Exception as e:
        raise ValueError(
            f"Error loading or converting generated audio file to wav file '{audio_path}': {e}"
        )
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    volumes = _get_volume_by_chunks(audio, chunk_length_ms)

    payload = {
        "type": "audio",
        "audio": audio_base64,
        "volumes": volumes,
        "slice_length": chunk_length_ms,
        "display_text": display_text,
        "actions": actions.to_dict() if actions else None,
        "forwarded": forwarded,
    }

    return payload


# Example usage:
# payload, duration = prepare_audio_payload("path/to/audio.mp3", display_text="Hello", expression_list=[0,1,2])
