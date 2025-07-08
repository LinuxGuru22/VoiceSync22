import requests
import threading
import time

selected_model = None  # Ensure selected_model is declared globally

def get_user_selection(models):
    """Handles user input for model selection with timeout."""
    global selected_model
    try:
        selection = input("Enter the number of the model you want to use (auto-selects 1): ")
        if selection.isdigit():
            selection = int(selection)
            if 1 <= selection <= len(models):
                selected_model = models[selection - 1]
                return
        print(f"Invalid input. Defaulting to: {models[0]}")
    except Exception:
        print(f"Error during input. Defaulting to: {models[0]}")

    selected_model = models[0]

def get_ollama_model_http():
    """Fetch available Ollama models via HTTP request and prompt user to select one within 10 seconds."""
    global selected_model
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)  # Timeout for HTTP request
        response.raise_for_status()

        data = response.json()
        models = [model["name"] for model in data.get("models", [])]

        if not models:
            print("No models found in Ollama.")
            print("make sure your pointed to the right ollama server.")
            
            return

        print("Available Ollama Models:")
        for index, model in enumerate(models, start=1):
            print(f"{index}. {model}")

        # Start a thread for user input
        input_thread = threading.Thread(target=get_user_selection, args=(models,))
        input_thread.start()

        # Wait for input or timeout after 10 seconds
        input_thread.join(timeout=None)

        if not selected_model:
            print(f"Timed out! Defaulting to: {models[0]}")
            selected_model = models[0]

        print(f"Selected Model: {selected_model}")
        return selected_model
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Ollama models: {e}")
