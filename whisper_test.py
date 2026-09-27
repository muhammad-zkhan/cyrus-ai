from faster_whisper import WhisperModel

print("Whisper model load ho raha hai...")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("Audio transcribe ho raha hai...")

segments, info = model.transcribe(
    "voice_test.wav",
    beam_size=1,
    language=None
)

text = " ".join(
    segment.text.strip()
    for segment in segments
)

print()
print("YOU SAID:")
print(text)
print()
print("Detected language:", info.language)
print("Language probability:", info.language_probability)