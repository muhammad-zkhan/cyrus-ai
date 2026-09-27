import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000
DURATION = 5

print("🎙️ 5 seconds recording...")
print("Ab bolo...")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32"
)

sd.wait()

sf.write(
    "voice_test.wav",
    audio,
    SAMPLE_RATE
)

print("✅ Recording complete!")
print("File: voice_test.wav")