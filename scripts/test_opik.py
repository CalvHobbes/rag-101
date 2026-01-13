import opik
from src.config import get_settings

# Configure manually because .env has OPIK__API_KEY but SDK expects OPIK_API_KEY
settings = get_settings()
opik.configure(
    api_key=settings.opik.api_key,
    workspace=settings.opik.workspace,
    use_local=False
)

@opik.track(name="verification-run")
def test_funct():
    print("Opik is working")

if __name__ == "__main__":
    try:
        test_funct()
    except Exception as e:
        print(f"Opik verification failed: {e}")
